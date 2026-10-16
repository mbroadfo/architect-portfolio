// Studio page tests (Step 21; NFR15.2, AC0.3, AC0.5, AC0.6). The API and the identity
// provider are a fake fetch that records every request; nothing touches a network.
import { exhibit, snapshot } from "@slice-renderer/test-fixtures";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { ProjectView } from "./api";

const TOKEN = "header.payload.signature";

interface Recorded {
  method: string;
  url: string;
  headers: Record<string, string>;
  body: unknown;
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

class FakeBackend {
  requests: Recorded[] = [];
  projects = new Map<string, ProjectView>();
  overrides: ((request: Recorded) => Response | undefined)[] = [];

  project(overrides: Partial<ProjectView> = {}): ProjectView {
    const view: ProjectView = {
      projectId: `p${this.projects.size + 1}`,
      title: "Placeholder project",
      summary: "",
      slug: "placeholder-project",
      revision: 1,
      status: "Draft",
      updatedAt: "2026-10-11T12:00:00Z",
      publishedRevision: null,
      ...overrides,
    };
    this.projects.set(view.projectId, view);
    return view;
  }

  handle = async (input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> => {
    const url = String(input);
    const headers = (init.headers ?? {}) as Record<string, string>;
    const body = typeof init.body === "string" ? JSON.parse(init.body) : undefined;
    const request: Recorded = { method: init.method ?? "GET", url, headers, body };
    this.requests.push(request);
    for (const override of this.overrides) {
      const response = override(request);
      if (response) return response;
    }
    return this.route(request);
  };

  private route({ method, url, body }: Recorded): Response {
    if (url.includes("/token?sub=")) return json(200, { access_token: TOKEN });
    const path = new URL(url).pathname;
    const match = /^\/slice\/projects\/([^/]+)(\/preview|\/publish)?$/.exec(path);
    if (path === "/slice/projects" && method === "GET") {
      return json(200, { projects: [...this.projects.values()] });
    }
    if (path === "/slice/projects" && method === "POST") {
      const title = (body as { title: string }).title;
      const slug = title
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
      return json(201, this.project({ title, slug }));
    }
    const current = match ? this.projects.get(match[1] ?? "") : undefined;
    if (!current || !match)
      return json(404, { code: "NOT_FOUND", message: "not found", requestId: "r" });
    if (match[2] === "/preview") {
      const candidate = snapshot({
        exhibits: [exhibit({ slug: current.slug, title: current.title, summary: current.summary })],
      });
      return json(200, { revision: current.revision, snapshot: candidate, imageAddresses: {} });
    }
    if (match[2] === "/publish") {
      const revision = (body as { revision: number }).revision;
      this.projects.set(current.projectId, {
        ...current,
        status: "Published",
        publishedRevision: revision,
      });
      return json(200, {
        versionId: "v1",
        sourceRevision: revision,
        publishedAt: "x",
        status: "Published",
      });
    }
    if (method === "PATCH") {
      const updated = { ...current, ...(body as object), revision: current.revision + 1 };
      this.projects.set(current.projectId, updated);
      return json(200, updated);
    }
    return json(200, current);
  }
}

let backend: FakeBackend;

beforeEach(() => {
  backend = new FakeBackend();
  vi.stubGlobal("fetch", vi.fn(backend.handle));
  localStorage.clear();
  sessionStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function signIn() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByTestId("signin-button"));
  await screen.findByTestId("project-list");
  return user;
}

async function openEditor(title = "Slice demo") {
  const user = await signIn();
  await user.type(screen.getByTestId("new-project-title-input"), title);
  await user.click(screen.getByTestId("new-project-create-button"));
  await screen.findByTestId("editor");
  return user;
}

describe("Studio page", () => {
  it("marks its local-only sign-in with the fake-provider marker (R-06)", () => {
    render(<App />);
    expect(screen.getByTestId("signed-out").getAttribute("data-local-only")).toBe(
      "AIDLC_LOCAL_ONLY_FAKE_IDP",
    );
  });

  it("keeps the token in memory only and sends it as a bearer header (NFR15.2)", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    await openEditor();
    expect(setItem).not.toHaveBeenCalled();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    const apiCalls = backend.requests.filter((r) => r.url.includes("/slice/"));
    expect(apiCalls.length).toBeGreaterThan(0);
    for (const call of apiCalls) expect(call.headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });

  it("creates a project and saves it with its base revision", async () => {
    const user = await openEditor("New thing");
    expect(screen.getByTestId("editor-status").textContent).toBe("Draft");
    await user.type(screen.getByTestId("editor-summary-input"), "A summary");
    await user.click(screen.getByTestId("editor-save-button"));
    await waitFor(() =>
      expect(screen.getByTestId("editor-revision").textContent).toBe("Revision 2"),
    );
    const patch = backend.requests.find((r) => r.method === "PATCH");
    expect(patch?.headers["If-Match"]).toBe('"1"');
    expect(patch?.body).toEqual({ title: "New thing", summary: "A summary" });
  });

  it("shows the 409 message and reloads the project (AC0.3)", async () => {
    const user = await openEditor();
    backend.overrides.push((r) =>
      r.method === "PATCH"
        ? json(409, { code: "STALE_REVISION", message: "stale", requestId: "r" })
        : undefined,
    );
    await user.click(screen.getByTestId("editor-save-button"));
    expect((await screen.findByTestId("notice-text")).textContent).toBe(
      "Reload: this project changed.",
    );
    await user.click(screen.getByTestId("notice-reload-button"));
    await waitFor(() => expect(screen.queryByTestId("notice")).toBeNull());
    expect(backend.requests.at(-1)?.method).toBe("GET");
  });

  it("previews in a sandboxed frame without scripts, marked not public (AC0.5)", async () => {
    const user = await openEditor("Hostile <script>x</script>");
    await user.click(screen.getByTestId("editor-preview-button"));
    const frame = await screen.findByTestId("preview-frame");
    expect(frame.getAttribute("sandbox")).toBe("");
    expect(frame.getAttribute("sandbox")).not.toContain("allow-scripts");
    const html = frame.getAttribute("srcdoc") ?? "";
    expect(html).toContain("Preview — not public");
    expect(html).toContain("Hostile &lt;script&gt;x&lt;/script&gt;");
    expect(html).not.toContain("<script>x");
  });

  it("publishes exactly the reviewed revision after confirmation (AC0.6)", async () => {
    const user = await openEditor();
    await user.type(screen.getByTestId("editor-summary-input"), "Reviewed text");
    await user.click(screen.getByTestId("editor-save-button"));
    await waitFor(() =>
      expect(screen.getByTestId("editor-revision").textContent).toBe("Revision 2"),
    );
    await user.click(screen.getByTestId("editor-preview-button"));
    await user.click(await screen.findByTestId("publish-button"));
    expect(screen.getByTestId("publish-confirmation-text").textContent).toBe(
      "Publish revision 2 to the public site?",
    );
    await user.click(screen.getByTestId("publish-confirm-button"));
    await waitFor(() => expect(screen.getByTestId("editor-status").textContent).toBe("Published"));
    const publish = backend.requests.find((r) => r.url.endsWith("/publish"));
    expect(publish?.body).toEqual({ revision: 2 });
    expect(screen.getByTestId("notice-text").textContent).toBe("Published revision 2.");
  });

  it("can cancel the publish confirmation", async () => {
    const user = await openEditor();
    await user.click(screen.getByTestId("editor-preview-button"));
    await user.click(await screen.findByTestId("publish-button"));
    await user.click(screen.getByTestId("publish-cancel-button"));
    expect(screen.queryByTestId("publish-confirmation")).toBeNull();
    expect(backend.requests.some((r) => r.url.endsWith("/publish"))).toBe(false);
  });

  it("asks to sign in again on 401 and forgets the token", async () => {
    const user = await signIn();
    backend.overrides.push((r) =>
      r.method === "POST" && r.url.endsWith("/slice/projects")
        ? json(401, { code: "UNAUTHENTICATED", message: "expired", requestId: "r" })
        : undefined,
    );
    await user.type(screen.getByTestId("new-project-title-input"), "x");
    await user.click(screen.getByTestId("new-project-create-button"));
    expect((await screen.findByTestId("notice-text")).textContent).toBe("Sign in again.");
    expect(screen.getByTestId("signed-out")).toBeTruthy();
    backend.overrides.length = 0;
    await user.click(screen.getByTestId("notice-signin-button"));
    await screen.findByTestId("project-list");
  });

  it.each([
    [
      422,
      { code: "VALIDATION_FAILED", message: "title: must not be empty" },
      "title: must not be empty",
    ],
    [409, { code: "SLUG_TAKEN", message: "taken" }, "That slug is already in use."],
    [500, { code: "INTERNAL", message: "boom" }, "Something went wrong (500): boom"],
  ])("shows the reason for a %i", async (status, body, expected) => {
    const user = await openEditor();
    backend.overrides.push((r) =>
      r.method === "PATCH" ? json(status, { ...body, requestId: "r" }) : undefined,
    );
    await user.click(screen.getByTestId("editor-save-button"));
    expect((await screen.findByTestId("notice-text")).textContent).toBe(expected);
  });

  it("reports a failed sign-in and a network failure", async () => {
    backend.overrides.push((r) => (r.url.includes("/token") ? json(400, {}) : undefined));
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByTestId("signin-button"));
    expect((await screen.findByTestId("notice-text")).textContent).toBe(
      "Something went wrong (400): Sign-in failed",
    );
    backend.overrides.length = 0;
    backend.overrides.push((r) => {
      if (r.url.includes("/slice/")) throw new TypeError("Failed to fetch");
      return undefined;
    });
    await user.click(screen.getByTestId("signin-button"));
    expect((await screen.findByTestId("notice-text")).textContent).toBe("Failed to fetch");
  });

  it("lists projects, opens one, goes back and signs out", async () => {
    backend.project({ title: "Existing", status: "Published", publishedRevision: 1 });
    const user = await signIn();
    expect(screen.getByTestId("project-list-status").textContent).toBe("Published");
    await user.click(screen.getByTestId("project-list-open-button"));
    expect((screen.getByTestId("editor-title-input") as HTMLInputElement).value).toBe("Existing");
    await user.click(screen.getByTestId("editor-back-button"));
    await screen.findByTestId("project-list");
    await user.click(screen.getByTestId("signout-button"));
    expect(screen.getByTestId("signed-out")).toBeTruthy();
  });
});
