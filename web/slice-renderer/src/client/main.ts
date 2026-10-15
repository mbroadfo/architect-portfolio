// Entry point of the one public script (assets/site.js, built by scripts/hash-assets.mjs).
// Loaded with `defer` from a hashed same-origin file: no inline script, no eval, no network,
// no storage, no tracking (FR9.5, NFR9, NFR15). Every page works without it.
import { enhanceCarousel } from "./carousel";
import { enhanceDrawer } from "./drawer";
import { enhanceLightbox } from "./lightbox";

export function enhance(doc: Document): void {
  doc.querySelectorAll<HTMLElement>(".hero").forEach((hero) => {
    enhanceCarousel(hero);
  });
  enhanceDrawer(doc);
  enhanceLightbox(doc);
}

if (typeof document !== "undefined") enhance(document);
