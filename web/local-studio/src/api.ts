// Client for the local Studio server (same origin). Every request that changes data sends the
// Studio's custom header; the server refuses changes without it or from another origin.

export type Status = "Draft" | "Published" | "Changes since last publish" | "Taken down";
export type CategorySlug = "games" | "astronomy" | "woodworking" | "software";
export type Access = "open" | "sign-in" | "invitation";
export type Phone = "suitable" | "desktop" | "unknown";
export type LinkKind = "demo" | "documentation" | "other";

export const SECTIONS: readonly (readonly [keyof Sections, string])[] = [
  ["inspiration", "Inspiration"],
  ["designChallenges", "Design challenges"],
  ["architecturalDecisions", "Architectural decisions"],
  ["implementation", "Implementation"],
  ["outcomes", "Outcomes"],
  ["lessonsLearned", "Lessons learned"],
];

export const CATEGORIES: readonly (readonly [CategorySlug, string])[] = [
  ["games", "Games & AI Arenas"],
  ["astronomy", "Astronomy & Exploration"],
  ["woodworking", "Woodworking"],
  ["software", "Software & Tools"],
];

export interface Sections {
  inspiration: string;
  designChallenges: string;
  architecturalDecisions: string;
  implementation: string;
  outcomes: string;
  lessonsLearned: string;
}

export interface Link {
  kind: LinkKind;
  label: string;
  url: string;
}

export interface ImageView {
  assetRef: string;
  altText: string;
  caption: string;
  width: number;
  height: number;
  lead: boolean;
}

export interface Blocker {
  message: string;
  field: string;
}

/** The editable draft fields (what a save sends, minus revision and images). */
export interface DraftFields {
  title: string;
  slug: string;
  summary: string;
  sections: Sections;
  primaryCategory: CategorySlug | null;
  featured: boolean;
  links: Link[];
  liveUrl: string;
  liveUrlIncluded: boolean;
  liveUrlAuthorized: boolean;
  access: Access;
  phone: Phone;
  repositories: { url: string }[];
  rightsReviewRequired: boolean;
  rightsReviewComplete: boolean;
}

export interface ProjectView extends DraftFields {
  id: string;
  revision: number;
  createdAt: string;
  updatedAt: string;
  images: ImageView[];
  status: Status;
  publishedRevision: number | null;
  blockers: Blocker[];
}

export interface ProjectSummary {
  id: string;
  title: string;
  slug: string;
  status: Status;
  category: string | null;
  featured: boolean;
  featuredPosition: number | null;
  revision: number;
  updatedAt: string;
  leadImage: string | null;
  repositories: number;
}

export interface Badge {
  kind: string;
  spdx?: string;
}

export interface Review {
  projectId: string;
  title: string;
  revision: number;
  status: Status;
  isUpdate: boolean;
  address: string;
  text: { label: string; value: string }[];
  images: { assetRef: string; altText: string; caption: string; lead: boolean }[];
  links: Link[];
  liveUrl: { url: string | null; reason: string };
  repositories: {
    url: string | null;
    confirmedPublic: boolean;
    licence: string | null;
    note: string;
    checkedAt: string;
  }[];
  badges: Badge[];
  publicRepositories: { name: string; url: string; licence?: string }[];
  category: string | null;
  featured: boolean;
  rightsReview: string;
  blockers: Blocker[];
  reviewId: string | null;
}

export interface PublishResult {
  projectId: string;
  sourceRevision: number;
  publishedAt: string;
  status: Status;
}

export interface Featured {
  order: { id: string; title: string }[];
  notYetPublished: { id: string; title: string; status: Status }[];
  max: number;
}

export interface BuildResult {
  output: string;
  pages: number;
  exhibits: number;
  files: number;
  scan: string;
  url: string | null;
}

export interface PackageResult {
  artifact: string;
  mode: "staging" | "production";
  files: number;
  bytes: number;
  buildId: string;
  exhibits: { projectId: string; slug: string; sourceRevision: number }[];
  scan: string;
  dryRun: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function failure(response: Response): Promise<ApiError> {
  let body: { code?: unknown; message?: unknown } = {};
  try {
    body = (await response.json()) as typeof body;
  } catch {
    body = {};
  }
  const code = typeof body.code === "string" ? body.code : "INTERNAL";
  const message = typeof body.message === "string" ? body.message : response.statusText;
  return new ApiError(response.status, code, message);
}

const CHANGE_HEADERS = { "X-Studio-Request": "1" };

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = method === "GET" ? {} : { ...CHANGE_HEADERS };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {
    method,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw await failure(response);
  return (await response.json()) as T;
}

const project = (id: string) => `/api/projects/${encodeURIComponent(id)}`;

export const api = {
  list: async () =>
    (await request<{ projects: ProjectSummary[] }>("GET", "/api/projects")).projects,
  create: (title: string) => request<ProjectView>("POST", "/api/projects", { title }),
  get: (id: string) => request<ProjectView>("GET", project(id)),
  save: (
    id: string,
    revision: number,
    fields: DraftFields,
    images: { assetRef: string; altText: string; caption: string; lead: boolean }[],
  ) => request<ProjectView>("PUT", project(id), { ...fields, revision, images }),
  upload: async (id: string, revision: number, file: File): Promise<ProjectView> => {
    const form = new FormData();
    form.append("revision", String(revision));
    form.append("file", file);
    const response = await fetch(`${project(id)}/images`, {
      method: "POST",
      headers: CHANGE_HEADERS,
      credentials: "same-origin",
      body: form,
    });
    if (!response.ok) throw await failure(response);
    return (await response.json()) as ProjectView;
  },
  review: (id: string) => request<Review>("POST", `${project(id)}/review`),
  publish: (id: string, revision: number, reviewId: string) =>
    request<PublishResult>("POST", `${project(id)}/publish`, { revision, reviewId }),
  takeDown: (id: string, confirmTitle: string) =>
    request<ProjectView>("POST", `${project(id)}/take-down`, { confirmTitle }),
  featured: () => request<Featured>("GET", "/api/featured"),
  updateFeatured: (order: string[]) => request<Featured>("PUT", "/api/featured", { order }),
  activity: async () =>
    (await request<{ entries: { time: string; action: string }[] }>("GET", "/api/activity"))
      .entries,
  site: () => request<{ output: string; url: string | null }>("GET", "/api/site"),
  build: () => request<BuildResult>("POST", "/api/site/build"),
  packagePages: () => request<PackageResult>("POST", "/api/site/package"),
};

export type StudioApi = typeof api;

/** The thumbnail address of an image derivative served by the Studio. */
export function thumbnail(assetRef: string): string {
  return `/media/${encodeURIComponent(assetRef)}/w480.jpg`;
}

/** A readable sentence for an error from the Studio server. */
export function describe(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409 && error.code === "STALE_REVISION") {
      return `${error.message}`;
    }
    return error.message || `Something went wrong (${error.status}).`;
  }
  return error instanceof Error ? error.message : "Something went wrong.";
}

export const BADGE_LABELS: Record<string, string> = {
  inBrowser: "In browser",
  signInRequired: "Sign-in required",
  byInvitation: "By invitation",
  bestOnDesktop: "Best on desktop",
  sourceAvailable: "Source available",
  sourcePrivate: "Source private",
};

export function badgeLabel(badge: Badge): string {
  if (badge.kind === "openSource") return `Open source · ${badge.spdx ?? ""}`;
  return BADGE_LABELS[badge.kind] ?? badge.kind;
}
