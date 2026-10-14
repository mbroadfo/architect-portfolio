// Test-only builders: placeholder content only, no real project data (FR10.7).
import type { Exhibit, PublicSiteSnapshot } from "./types";

export const ASSET = "ast_PlaceholderAsset0001";

export function exhibit(overrides: Partial<Exhibit> = {}): Exhibit {
  return {
    slug: "placeholder-project",
    title: "Placeholder project",
    summary: "Placeholder summary text.",
    sections: {},
    leadImage: { assetRef: ASSET, altText: "Placeholder illustration", width: 400, height: 300 },
    images: [],
    attachments: [],
    links: [],
    badges: [],
    publicRepositories: [],
    featured: false,
    publishedAt: "2026-10-11T12:00:00Z",
    ...overrides,
  };
}

export function snapshot(overrides: Partial<PublicSiteSnapshot> = {}): PublicSiteSnapshot {
  return {
    schemaVersion: "1.0",
    generation: 1,
    site: {
      ownerName: "Placeholder Owner",
      githubProfileUrl: "https://github.com/example",
      contactEmail: null,
    },
    exhibits: [exhibit()],
    featuredOrder: [],
    categories: [],
    ...overrides,
  };
}
