// C2 validation: the JSON Schema (Ajv, draft 2020-12) plus the semantic rules the renderer
// can decide from the snapshot alone (C2 S1 to S7). A snapshot that fails is refused whole.
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import schema from "./c2-schema.json";
import { RenderInputError, type Exhibit, type PublicSiteSnapshot } from "./types";

// Strict mode, with union types allowed for C2's `contactEmail: [string, null]`.
const ajv = new Ajv2020({ allErrors: true, strict: true, allowUnionTypes: true });
addFormats(ajv);
const validateSchema = ajv.compile<PublicSiteSnapshot>(schema);

const LIVE_BADGES = new Set(["inBrowser", "signInRequired", "byInvitation"]);

function fail(message: string): never {
  throw new RenderInputError(`invalid snapshot: ${message}`);
}

function checkFeatured(snapshot: PublicSiteSnapshot): void {
  const featured = new Set(snapshot.exhibits.filter((e) => e.featured).map((e) => e.slug));
  const seen = new Set<string>();
  for (const slug of snapshot.featuredOrder) {
    if (!featured.has(slug)) fail(`S1: featuredOrder slug '${slug}' is not a featured exhibit`);
    if (seen.has(slug)) fail(`S1: featuredOrder slug '${slug}' appears twice`);
    seen.add(slug);
  }
}

function checkCategories(snapshot: PublicSiteSnapshot): void {
  const counts = new Map<string, number>();
  for (const exhibit of snapshot.exhibits) {
    const slug = exhibit.primaryCategory?.slug;
    if (slug) counts.set(slug, (counts.get(slug) ?? 0) + 1);
  }
  const listed = new Map<string, number>(snapshot.categories.map((c) => [c.slug, c.count]));
  const matches =
    listed.size === counts.size && [...counts].every(([slug, n]) => listed.get(slug) === n);
  if (!matches || listed.size !== snapshot.categories.length) {
    fail("S2: categories do not match the exhibits' primary categories");
  }
}

function checkBadges(exhibit: Exhibit): void {
  const kinds = exhibit.badges.map((b) => b.kind);
  for (const badge of exhibit.badges) {
    if (badge.spdx !== undefined && badge.kind !== "openSource")
      fail("S4: spdx without openSource");
  }
  const live = kinds.filter((k) => LIVE_BADGES.has(k));
  if (live.length > 1 || (live.length === 1 && exhibit.liveUrl === undefined)) {
    fail(`S5: exhibit '${exhibit.slug}' has an invalid access badge`);
  }
  const repositories = exhibit.publicRepositories;
  for (const badge of exhibit.badges) {
    const consistent =
      (badge.kind === "openSource" && repositories.some((r) => r.licence === badge.spdx)) ||
      (badge.kind === "sourceAvailable" && repositories.length > 0) ||
      (badge.kind === "sourcePrivate" && repositories.length === 0) ||
      !["openSource", "sourceAvailable", "sourcePrivate"].includes(badge.kind);
    if (!consistent) fail(`S6: exhibit '${exhibit.slug}' badge '${badge.kind}' is inconsistent`);
  }
}

function checkAssets(exhibit: Exhibit): void {
  const imageRefs = [exhibit.leadImage, ...exhibit.images].map((i) => i.assetRef);
  const fileRefs = exhibit.attachments.map((a) => a.assetRef);
  if (new Set(imageRefs).size !== imageRefs.length || new Set(fileRefs).size !== fileRefs.length) {
    fail(`S7: exhibit '${exhibit.slug}' repeats an asset reference`);
  }
}

/** Validate against C2 and the snapshot-decidable semantic rules; throw RenderInputError. */
export function validateSnapshot(input: unknown): PublicSiteSnapshot {
  if (!validateSchema(input)) {
    const details = (validateSchema.errors ?? [])
      .map((e) => `${e.instancePath || "/"} ${e.message ?? "is invalid"}`)
      .join("; ");
    fail(details);
  }
  const snapshot = input;
  const slugs = snapshot.exhibits.map((e) => e.slug);
  if (new Set(slugs).size !== slugs.length) fail("S3: exhibit slugs are not unique");
  checkFeatured(snapshot);
  checkCategories(snapshot);
  for (const exhibit of snapshot.exhibits) {
    checkBadges(exhibit);
    checkAssets(exhibit);
  }
  return snapshot;
}
