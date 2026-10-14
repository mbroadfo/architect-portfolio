// Preview with the same renderer Publish uses (BR4.1), in preview mode: every page carries the
// permanent "Preview — not public" marking and noindex. Images resolve to the data addresses
// the API returned with the candidate, so the sandboxed frame needs no network access.
import { render } from "@slice-renderer/render";
import type { AssetResolver } from "@slice-renderer/types";
import type { PreviewCandidate } from "./api";

export function previewResolver(candidate: PreviewCandidate): AssetResolver {
  return (ref) =>
    ref.kind === "image"
      ? (candidate.imageAddresses[`${ref.assetRef}/${ref.variant}.${ref.format}`] ?? "")
      : "#";
}

/** Render the candidate's exhibit page in preview mode; throws RenderInputError if invalid. */
export function renderPreview(candidate: PreviewCandidate, slug: string): string {
  const output = render(candidate.snapshot, {
    mode: "preview",
    previewSlug: slug,
    resolveAsset: previewResolver(candidate),
  });
  return output.pages.find((page) => page.path === `/work/${slug}`)?.html ?? "";
}
