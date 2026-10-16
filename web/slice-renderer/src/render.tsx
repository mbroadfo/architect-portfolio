// render(snapshot, options): the C11 renderer surface for the walking slice.
// Pure and deterministic: no clock, randomness, network, storage or environment is read.
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  CatalogPage,
  CategoryPage,
  ExhibitPage,
  HomePage,
  NotFoundPage,
  type PageContext,
} from "./pages";
import { STATIC_ASSET_PATHS } from "./static-assets";
import {
  RenderInputError,
  type PublicSiteSnapshot,
  type RenderedPage,
  type RenderOptions,
  type RenderOutput,
} from "./types";
import { validateSnapshot } from "./validate";
import { downloadName, IMAGE_FORMATS, imageVariants } from "./variants";

const DOCTYPE = "<!DOCTYPE html>";

function page(path: string, status: 200 | 404, element: ReactElement): RenderedPage {
  return { path, status, html: DOCTYPE + renderToStaticMarkup(element) };
}

function checkOptions(snapshot: PublicSiteSnapshot, options: RenderOptions): void {
  if (options.mode !== "public" && options.mode !== "preview") {
    throw new RenderInputError(`invalid options: unknown mode '${String(options.mode)}'`);
  }
  if (typeof options.resolveAsset !== "function") {
    throw new RenderInputError("invalid options: resolveAsset must be a function");
  }
  if (options.mode === "preview") {
    const slug = options.previewSlug;
    if (!slug || !snapshot.exhibits.some((e) => e.slug === slug)) {
      throw new RenderInputError(
        "invalid options: previewSlug must name an exhibit in preview mode",
      );
    }
  }
}

function requiredImages(snapshot: PublicSiteSnapshot): RenderOutput["requiredImages"] {
  const seen = new Set<string>();
  const result: RenderOutput["requiredImages"] = [];
  for (const exhibit of snapshot.exhibits) {
    for (const image of [exhibit.leadImage, ...exhibit.images]) {
      for (const { variant } of imageVariants(image)) {
        for (const format of IMAGE_FORMATS) {
          const key = `${image.assetRef}/${variant}.${format}`;
          if (!seen.has(key)) {
            seen.add(key);
            result.push({ assetRef: image.assetRef, variant, format });
          }
        }
      }
    }
  }
  return result;
}

function requiredDownloads(snapshot: PublicSiteSnapshot): RenderOutput["requiredDownloads"] {
  return snapshot.exhibits.flatMap((exhibit) =>
    exhibit.attachments.map((a) => ({ assetRef: a.assetRef, downloadName: downloadName(a) })),
  );
}

/** Validate the snapshot against C2 and the semantic rules, then render every C9 page. */
export function render(snapshot: PublicSiteSnapshot, options: RenderOptions): RenderOutput {
  const valid = validateSnapshot(snapshot);
  checkOptions(valid, options);
  const ctx: PageContext = {
    snapshot: valid,
    resolveAsset: options.resolveAsset,
    isPreview: options.mode === "preview",
  };
  const pages: RenderedPage[] = [
    page("/", 200, <HomePage ctx={ctx} />),
    page("/work/", 200, <CatalogPage ctx={ctx} />),
    ...valid.exhibits.map((exhibit) =>
      page(`/work/${exhibit.slug}`, 200, <ExhibitPage ctx={ctx} exhibit={exhibit} />),
    ),
    ...valid.categories.map((category) =>
      page(
        `/category/${category.slug}`,
        200,
        <CategoryPage ctx={ctx} slug={category.slug} name={category.name} />,
      ),
    ),
    page("/404.html", 404, <NotFoundPage ctx={ctx} kind="exhibit" />),
    page("/category-404.html", 404, <NotFoundPage ctx={ctx} kind="category" />),
  ];
  return {
    contractVersion: "1.0",
    pages,
    requiredImages: requiredImages(valid),
    requiredDownloads: requiredDownloads(valid),
    staticAssets: [...STATIC_ASSET_PATHS],
  };
}
