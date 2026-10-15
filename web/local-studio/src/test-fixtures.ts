// Test doubles for the Studio page: a fake API client with ready-made projects.
import { vi } from "vitest";
import type { ProjectSummary, ProjectView, Review, StudioApi } from "./api";

export function projectView(overrides: Partial<ProjectView> = {}): ProjectView {
  return {
    id: "stars",
    title: "STARS",
    slug: "stars",
    summary: "Fly through the real galaxy.",
    sections: {
      inspiration: "Instruments.",
      designChallenges: "",
      architecturalDecisions: "",
      implementation: "",
      outcomes: "",
      lessonsLearned: "",
    },
    primaryCategory: "astronomy",
    featured: true,
    links: [],
    liveUrl: "https://stars.example.org",
    liveUrlIncluded: false,
    liveUrlAuthorized: false,
    access: "open",
    phone: "suitable",
    repositories: [{ url: "https://github.com/mbroadfo/stars" }],
    rightsReviewRequired: false,
    rightsReviewComplete: false,
    revision: 5,
    createdAt: "2026-10-14T00:00:00Z",
    updatedAt: "2026-10-14T00:00:00Z",
    images: [
      {
        assetRef: "ast_aaaaaaaaaaaaaaaaaaaaaaaa",
        altText: "The atlas",
        caption: "",
        width: 1400,
        height: 900,
        lead: true,
      },
    ],
    status: "Draft",
    publishedRevision: null,
    blockers: [],
    ...overrides,
  };
}

export function summary(overrides: Partial<ProjectSummary> = {}): ProjectSummary {
  return {
    id: "stars",
    title: "STARS",
    slug: "stars",
    status: "Draft",
    category: "Astronomy & Exploration",
    featured: true,
    featuredPosition: null,
    revision: 5,
    updatedAt: "2026-10-14T00:00:00Z",
    leadImage: "ast_aaaaaaaaaaaaaaaaaaaaaaaa",
    repositories: 1,
    ...overrides,
  };
}

export function review(overrides: Partial<Review> = {}): Review {
  return {
    projectId: "stars",
    title: "STARS",
    revision: 5,
    status: "Draft",
    isUpdate: false,
    address: "/work/stars",
    text: [
      { label: "Title", value: "STARS" },
      { label: "inspiration", value: "Instruments." },
    ],
    images: [
      { assetRef: "ast_aaaaaaaaaaaaaaaaaaaaaaaa", altText: "The atlas", caption: "", lead: true },
    ],
    links: [{ kind: "demo", label: "Demo", url: "https://demo.example.org" }],
    liveUrl: { url: null, reason: "not authorized (FR10.7)" },
    repositories: [
      {
        url: "https://github.com/mbroadfo/stars",
        confirmedPublic: true,
        licence: null,
        note: "public",
        checkedAt: "2026-10-14T00:00:00Z",
      },
      {
        url: null,
        confirmedPublic: false,
        licence: null,
        note: "not found or private",
        checkedAt: "",
      },
    ],
    badges: [{ kind: "sourceAvailable" }, { kind: "openSource", spdx: "MIT" }],
    publicRepositories: [{ name: "stars", url: "https://github.com/mbroadfo/stars" }],
    category: "Astronomy & Exploration",
    featured: true,
    rightsReview: "not required",
    blockers: [],
    reviewId: "0123456789abcdef0123456789abcdef",
    ...overrides,
  };
}

export function fakeClient(overrides: Partial<StudioApi> = {}): StudioApi {
  return {
    list: vi.fn(async () => [summary()]),
    create: vi.fn(async (title: string) => projectView({ id: "new", title, revision: 1 })),
    get: vi.fn(async () => projectView()),
    save: vi.fn(async (_id, revision, fields) =>
      projectView({ ...fields, revision: revision + 1 }),
    ),
    upload: vi.fn(async (_id, revision) => projectView({ revision: revision + 1 })),
    review: vi.fn(async () => review()),
    publish: vi.fn(async () => ({
      projectId: "stars",
      sourceRevision: 5,
      publishedAt: "2026-10-14T00:00:00Z",
      status: "Published" as const,
    })),
    takeDown: vi.fn(async () => projectView({ status: "Taken down" })),
    featured: vi.fn(async () => ({
      order: [
        { id: "stars", title: "STARS" },
        { id: "baduk", title: "Baduk" },
      ],
      notYetPublished: [{ id: "chess", title: "Chess", status: "Draft" as const }],
      max: 5,
    })),
    updateFeatured: vi.fn(async (order: string[]) => ({
      order: order.map((id) => ({ id, title: id })),
      notYetPublished: [],
      max: 5,
    })),
    activity: vi.fn(async () => [
      { time: "2026-10-14T10:00:00+00:00", action: "Publish STARS (revision 5)" },
    ]),
    site: vi.fn(async () => ({ output: "C:/content/build/site", url: "http://127.0.0.1:8766/" })),
    build: vi.fn(async () => ({
      output: "C:/content/build/site",
      pages: 6,
      exhibits: 1,
      files: 15,
      scan: "scan_output: OK - 15 file(s) scanned",
      url: "http://127.0.0.1:8766/",
    })),
    packagePages: vi.fn(async () => ({
      artifact: "C:/content/build/pages-20261015T010203Z",
      mode: "staging" as const,
      files: 22,
      bytes: 1234567,
      buildId: "build-20261015010000-1",
      exhibits: [{ projectId: "stars", slug: "stars", sourceRevision: 6 }],
      scan: "scan_output: OK - 21 file(s) scanned",
      dryRun: "python -m portfolio_studio deploy-pages --artifact C:/content/build/pages-x",
    })),
    ...overrides,
  };
}
