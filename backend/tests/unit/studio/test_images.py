"""FR4.2 image validation and sanitization: by content, size and pixel limits, no metadata."""

from __future__ import annotations

import io
import struct
import zlib

import pytest
from PIL import Image
from portfolio_studio.errors import ImageRejectedError, UploadTooLargeError
from portfolio_studio.images import (
    MAX_UPLOAD_BYTES,
    process_image,
    read_limited,
    sniff,
    variant_widths,
)

from .conftest import make_image


def png_header_only(width: int, height: int) -> bytes:
    """A PNG whose header claims ``width`` x ``height`` with almost no pixel data (a bomb)."""
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk = b"IHDR" + ihdr
    body = struct.pack(">I", len(ihdr)) + chunk + struct.pack(">I", zlib.crc32(chunk))
    idat = b"IDAT" + zlib.compress(b"\x00" * 64)
    body += struct.pack(">I", len(idat) - 4) + idat + struct.pack(">I", zlib.crc32(idat))
    end = b"IEND"
    body += struct.pack(">I", 0) + end + struct.pack(">I", zlib.crc32(end))
    return b"\x89PNG\r\n\x1a\n" + body


def test_wrong_signature_is_rejected_whatever_the_name() -> None:
    """FR4.2: an HTML or text file renamed .jpg is refused by its content."""
    with pytest.raises(ImageRejectedError):
        process_image(b"<html><script>alert(1)</script></html>")
    with pytest.raises(ImageRejectedError):
        sniff(b"GIF89a....")


def test_oversize_upload_is_rejected_before_decoding() -> None:
    """FR4.2: more than 10 MB is refused while reading."""
    with pytest.raises(UploadTooLargeError):
        read_limited(io.BytesIO(b"\xff\xd8\xff" + b"0" * MAX_UPLOAD_BYTES))
    with pytest.raises(UploadTooLargeError):
        process_image(b"\xff\xd8\xff" + b"0" * MAX_UPLOAD_BYTES)
    assert read_limited(io.BytesIO(b"abc")) == b"abc"


def test_pixel_bomb_is_rejected_before_full_decode() -> None:
    """FR4.2: the pixel count is checked from the header before decoding."""
    with pytest.raises(ImageRejectedError, match="pixels"):
        process_image(png_header_only(11_000, 11_000))
    with pytest.raises(ImageRejectedError, match="pixels on each side"):
        process_image(png_header_only(20_000, 10))


def test_truncated_image_is_rejected() -> None:
    data = make_image()
    with pytest.raises(ImageRejectedError):
        process_image(data[: len(data) // 3])


def test_exif_and_gps_are_stripped_from_every_derivative() -> None:
    """FR4.2, ADR-006: derivatives carry no EXIF, GPS, camera or ICC metadata."""
    original = make_image((2000, 1000), gps=True)
    assert b"SecretCam" in original and b"Exif" in original
    processed = process_image(original)
    assert processed.width == 2000 and processed.height == 1000
    keys = sorted(d.key for d in processed.derivatives)
    assert keys == [
        "w1600.jpg",
        "w1600.webp",
        "w480.jpg",
        "w480.webp",
        "w960.jpg",
        "w960.webp",
    ]
    for derivative in processed.derivatives:
        assert b"Exif" not in derivative.data
        assert b"SecretCam" not in derivative.data
        image = Image.open(io.BytesIO(derivative.data))
        assert not image.getexif()
        assert "icc_profile" not in image.info and "exif" not in image.info
        assert image.width == int(derivative.key.split(".")[0][1:])


def test_png_with_transparency_and_webp_are_accepted() -> None:
    buffer = io.BytesIO()
    Image.new("RGBA", (300, 200), (255, 0, 0, 0)).save(buffer, "PNG")
    small = process_image(buffer.getvalue())
    assert small.original_extension == "png"
    # Below 480 pixels wide, only w480 is made, at the original width (never upscaled).
    assert sorted(d.key for d in small.derivatives) == ["w480.jpg", "w480.webp"]
    assert Image.open(io.BytesIO(small.derivatives[0].data)).width == 300
    assert process_image(make_image((600, 400), "WEBP")).original_extension == "webp"


def test_animated_images_are_rejected() -> None:
    frames = [Image.new("RGB", (64, 64), c) for c in ((0, 0, 0), (255, 255, 255))]
    buffer = io.BytesIO()
    frames[0].save(buffer, "WEBP", save_all=True, append_images=frames[1:])
    with pytest.raises(ImageRejectedError, match="animated"):
        process_image(buffer.getvalue())


def test_exif_orientation_is_applied() -> None:
    image = Image.new("RGB", (400, 200))
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif.tobytes())
    processed = process_image(buffer.getvalue())
    assert (processed.width, processed.height) == (200, 400)


def test_variant_widths_follow_c8() -> None:
    assert variant_widths(300) == [("w480", 300)]
    assert variant_widths(960) == [("w480", 480), ("w960", 960)]
    assert [n for n, _ in variant_widths(5000)] == ["w480", "w960", "w1600"]


def test_multi_picture_jpeg_keeps_only_the_primary_image() -> None:
    """LS-6: an MPO (phone camera JPEG) is accepted; its secondary picture and metadata are
    dropped, and only the primary image's pixels are re-encoded."""
    primary = Image.new("RGB", (1000, 700), (200, 30, 30))
    secondary = Image.new("RGB", (320, 240), (30, 200, 30))
    exif = Image.Exif()
    exif[0x0110] = "SecretCam 9000"
    exif[0x8825] = {1: "N", 2: (47.0, 36.0, 12.0)}
    buffer = io.BytesIO()
    primary.save(buffer, "MPO", save_all=True, append_images=[secondary], exif=exif.tobytes())
    data = buffer.getvalue()
    opened = Image.open(io.BytesIO(data))
    assert opened.format == "MPO" and getattr(opened, "n_frames", 1) == 2
    processed = process_image(data)
    assert (processed.width, processed.height) == (1000, 700)
    for derivative in processed.derivatives:
        assert derivative.data.count(b"\xff\xd8") == (1 if derivative.key.endswith(".jpg") else 0)
        assert b"MPF" not in derivative.data and b"Exif" not in derivative.data
        assert b"SecretCam" not in derivative.data
        image = Image.open(io.BytesIO(derivative.data))
        assert getattr(image, "n_frames", 1) == 1
        red, green, _ = image.convert("RGB").getpixel((10, 10))  # type: ignore[misc]
        assert red > 150 and green < 80  # the primary picture, not the secondary
