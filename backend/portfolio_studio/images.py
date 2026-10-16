"""Image uploads: validate by content, limit pixels, re-encode without metadata (FR4.2, ADR-006).

1. The size limit (10 MB) is enforced while reading, before any decoding.
2. The file signature decides the type (JPEG, PNG or WebP); the name and declared type are
   ignored. A multi-picture JPEG (MPO) is accepted, and only its primary image is used.
   HEIC is deferred.
3. The header is parsed lazily and the pixel count checked before the full decode; Pillow's
   own decompression-bomb limit is turned into an error as a second line of defence.
4. The decoded pixels are oriented, flattened to RGB and re-encoded into the C8 variants
   (w480, w960, w1600; never upscaled) as WebP and JPEG. The new images carry no EXIF, GPS,
   ICC profile, XMP, comments or thumbnails: only pixels are copied.
5. The original bytes are kept privately; they are never published.
"""

from __future__ import annotations

import hashlib
import io
import secrets
import string
import warnings
from collections.abc import Iterator
from dataclasses import dataclass
from typing import IO

from PIL import Image, ImageOps, UnidentifiedImageError

from portfolio_studio.errors import ImageRejectedError, UploadTooLargeError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_SIDE = 12_000
VARIANT_WIDTHS: tuple[tuple[str, int], ...] = (("w480", 480), ("w960", 960), ("w1600", 1600))
FORMATS: tuple[str, ...] = ("webp", "jpg")
WEBP_QUALITY = 82
JPEG_QUALITY = 85
BACKGROUND = (14, 13, 11)  # the site's --bg, used to flatten transparency
# The Pillow formats each signature may decode as. MPO (multi-picture JPEG, as phones write
# it) is a JPEG signature too: only its primary image is used (security review LS-6).
FORMATS_BY_SIGNATURE: dict[str, frozenset[str]] = {
    "jpg": frozenset({"JPEG", "MPO"}),
    "png": frozenset({"PNG"}),
    "webp": frozenset({"WEBP"}),
}
ALPHABET = string.ascii_letters + string.digits


def new_asset_ref() -> str:
    return "ast_" + "".join(secrets.choice(ALPHABET) for _ in range(24))


def read_limited(stream: IO[bytes], limit: int = MAX_UPLOAD_BYTES) -> bytes:
    """Read at most ``limit`` bytes; refuse a larger stream without reading it all."""
    data = stream.read(limit + 1)
    if len(data) > limit:
        raise UploadTooLargeError(f"images are limited to {limit // (1024 * 1024)} MB")
    return data


def sniff(data: bytes) -> str:
    """The image type from the file signature: 'jpg', 'png' or 'webp'."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    raise ImageRejectedError("only JPEG, PNG and WebP images are accepted (checked by content)")


def variant_widths(width: int) -> list[tuple[str, int]]:
    """C8: every width in {480, 960, 1600} at most W; below 480, only w480 encoded at W."""
    widths = [(name, limit) for name, limit in VARIANT_WIDTHS if limit <= width]
    return widths or [("w480", width)]


@dataclass(frozen=True)
class Derivative:
    key: str  # "<variant>.<format>"
    data: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass(frozen=True)
class ProcessedImage:
    """The result of a validated upload."""

    original_extension: str
    width: int
    height: int
    derivatives: tuple[Derivative, ...]


def _open_checked(data: bytes, kind: str) -> Image.Image:
    """Parse the header only, check the format and pixel count, then decode."""
    try:
        image = Image.open(io.BytesIO(data))
    except Image.DecompressionBombError as error:
        raise ImageRejectedError("the image has too many pixels") from error
    except (UnidentifiedImageError, OSError) as error:
        raise ImageRejectedError("the file is not a readable image") from error
    if image.format not in FORMATS_BY_SIGNATURE[kind]:
        raise ImageRejectedError("the image content does not match its signature")
    width, height = image.size
    if width < 1 or height < 1 or width > MAX_SIDE or height > MAX_SIDE:
        raise ImageRejectedError(f"images are limited to {MAX_SIDE} pixels on each side")
    if width * height > MAX_PIXELS:
        raise ImageRejectedError(f"images are limited to {MAX_PIXELS // 1_000_000} megapixels")
    if image.format == "MPO":
        image.seek(0)  # the primary image; the secondary pictures are never decoded or kept
    elif getattr(image, "n_frames", 1) > 1:
        raise ImageRejectedError("animated images are not accepted")
    try:
        image.load()
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise ImageRejectedError("the image could not be decoded") from error
    return image


def _pixels_only(image: Image.Image) -> Image.Image:
    """Orient, flatten to RGB and copy only the pixels into a new image (no metadata)."""
    oriented = ImageOps.exif_transpose(image)
    if oriented.mode in ("RGBA", "LA") or (
        oriented.mode == "P" and "transparency" in oriented.info
    ):
        rgba = oriented.convert("RGBA")
        flattened = Image.new("RGB", rgba.size, BACKGROUND)
        flattened.paste(rgba, mask=rgba.getchannel("A"))
        oriented = flattened
    rgb = oriented.convert("RGB")
    clean = Image.new("RGB", rgb.size)
    clean.paste(rgb)
    clean.info.clear()
    return clean


def _encode(image: Image.Image, image_format: str) -> bytes:
    buffer = io.BytesIO()
    if image_format == "webp":
        image.save(buffer, "WEBP", quality=WEBP_QUALITY, method=4, exif=b"", icc_profile=None)
    else:
        image.save(
            buffer,
            "JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
            progressive=True,
            exif=b"",
            icc_profile=None,
        )
    return buffer.getvalue()


def _variants(clean: Image.Image) -> Iterator[Derivative]:
    width, height = clean.size
    for name, target in variant_widths(width):
        if target == width:
            resized = clean
        else:
            resized = clean.resize(
                (target, max(1, round(height * target / width))), Image.Resampling.LANCZOS
            )
            resized.info.clear()
        for image_format in FORMATS:
            yield Derivative(key=f"{name}.{image_format}", data=_encode(resized, image_format))


def process_image(data: bytes) -> ProcessedImage:
    """Validate an upload and produce its sanitized derivatives."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadTooLargeError(f"images are limited to {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    kind = sniff(data)
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        previous = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        try:
            image = _open_checked(data, kind)
            clean = _pixels_only(image)
        except Image.DecompressionBombWarning as error:
            raise ImageRejectedError("the image has too many pixels") from error
        finally:
            Image.MAX_IMAGE_PIXELS = previous
    derivatives = tuple(_variants(clean))
    return ProcessedImage(
        original_extension=kind,
        width=clean.size[0],
        height=clean.size[1],
        derivatives=derivatives,
    )
