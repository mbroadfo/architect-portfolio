// Studio API client (C1 error shape). The access token is passed in by the caller and lives in
// React state only; this module never stores it (NFR15.2). It is sent as a bearer header.
import type { PublicSiteSnapshot } from "@slice-renderer/types";
import { API_BASE, OWNER_SUBJECT, TOKEN_URL } from "./config";

export type SliceStatus = "Draft" | "Published" | "Changes since last publish";

export interface ProjectView {
  projectId: string;
  title: string;
  summary: string;
  slug: string;
  revision: number;
  status: SliceStatus;
  updatedAt: string;
  publishedRevision: number | null;
}

export interface PreviewCandidate {
  revision: number;
  snapshot: PublicSiteSnapshot;
  imageAddresses: Record<string, string>;
}

export interface PublishResult {
  versionId: string;
  sourceRevision: number;
  publishedAt: string;
  status: SliceStatus;
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

/** Sign in through the LOCAL-ONLY fake identity provider (the local stand-in for Auth0). */
export async function fetchToken(): Promise<string> {
  const response = await fetch(`${TOKEN_URL}?sub=${encodeURIComponent(OWNER_SUBJECT)}`);
  if (!response.ok) throw new ApiError(response.status, "SIGN_IN_FAILED", "Sign-in failed");
  const body = (await response.json()) as { access_token?: unknown };
  if (typeof body.access_token !== "string") {
    throw new ApiError(500, "SIGN_IN_FAILED", "Sign-in returned no token");
  }
  return body.access_token;
}

export interface StudioClient {
  list(): Promise<ProjectView[]>;
  create(title: string): Promise<ProjectView>;
  get(projectId: string): Promise<ProjectView>;
  save(
    projectId: string,
    revision: number,
    changes: { title: string; summary: string },
  ): Promise<ProjectView>;
  preview(projectId: string): Promise<PreviewCandidate>;
  publish(projectId: string, revision: number): Promise<PublishResult>;
}

export function createClient(token: string): StudioClient {
  async function request<T>(
    method: string,
    path: string,
    body?: unknown,
    extra?: Record<string, string>,
  ): Promise<T> {
    const headers: Record<string, string> = { Authorization: `Bearer ${token}`, ...extra };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) throw await failure(response);
    return (await response.json()) as T;
  }

  const project = (id: string) => `/slice/projects/${encodeURIComponent(id)}`;
  return {
    list: async () =>
      (await request<{ projects: ProjectView[] }>("GET", "/slice/projects")).projects,
    create: (title) => request<ProjectView>("POST", "/slice/projects", { title }),
    get: (id) => request<ProjectView>("GET", project(id)),
    save: (id, revision, changes) =>
      request<ProjectView>("PATCH", project(id), changes, { "If-Match": `"${revision}"` }),
    preview: (id) => request<PreviewCandidate>("GET", `${project(id)}/preview`),
    publish: (id, revision) =>
      request<PublishResult>("POST", `${project(id)}/publish`, { revision }),
  };
}
