// C8 variant rule and C9 download names: the single definitions the renderer uses.
import type { Attachment, Image, ImageFormat, Variant } from "./types";

const VARIANT_WIDTHS: readonly (readonly [Variant, number])[] = [
  ["w480", 480],
  ["w960", 960],
  ["w1600", 1600],
];
export const IMAGE_FORMATS: readonly ImageFormat[] = ["webp", "jpg"];

const EXTENSIONS: Record<Attachment["fileType"], string> = {
  PDF: "pdf",
  SKP: "skp",
  FCStd: "fcstd",
  DXF: "dxf",
  STL: "stl",
  ZIP: "zip",
  VSDX: "vsdx",
};

export interface ImageVariant {
  variant: Variant;
  /** Pixel width of the encoded variant (never upscaled). */
  width: number;
}

/** Every width in {480, 960, 1600} at most W; below 480, only w480 encoded at W. */
export function imageVariants(image: Pick<Image, "width">): ImageVariant[] {
  const variants = VARIANT_WIDTHS.filter(([, limit]) => limit <= image.width).map(
    ([variant, limit]) => ({ variant, width: limit }),
  );
  return variants.length > 0 ? variants : [{ variant: "w480", width: image.width }];
}

/** Strip leading and trailing hyphens in linear time (an anchored `-+$` regex is polynomial). */
function trimHyphens(text: string): string {
  let start = 0;
  let end = text.length;
  while (start < end && text[start] === "-") start += 1;
  while (end > start && text[end - 1] === "-") end -= 1;
  return text.slice(start, end);
}

/** downloadName = slug(label) + "." + ext (C9). */
export function downloadName(attachment: Pick<Attachment, "label" | "fileType">): string {
  const words = attachment.label.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const slug = trimHyphens(trimHyphens(words).slice(0, 60));
  return `${slug || "download"}.${EXTENSIONS[attachment.fileType]}`;
}
