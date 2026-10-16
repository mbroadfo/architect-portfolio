import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, type StudioApi } from "./api";
import { App, parseRoute } from "./App";
import { fakeClient, projectView, review, summary } from "./test-fixtures";

function go(hash: string) {
  act(() => {
    window.location.hash = hash;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

function start(client: StudioApi, hash = "#projects") {
  window.history.replaceState(null, "", hash);
  render(<App client={client} />);
}

beforeEach(() => {
  window.history.replaceState(null, "", "#projects");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("routes", () => {
  it("parses hash routes and falls back to Projects", () => {
    expect(parseRoute("#edit/stars")).toEqual({ view: "edit", id: "stars" });
    expect(parseRoute("#edit")).toEqual({ view: "projects" });
    expect(parseRoute("#nope")).toEqual({ view: "projects" });
    expect(parseRoute("#activity")).toEqual({ view: "activity" });
  });
});

describe("Projects", () => {
  it("lists projects with statuses in words (FR3.2) and offers take-down for public ones", async () => {
    const client = fakeClient({
      list: vi.fn(async () => [
        summary(),
        summary({
          id: "baduk",
          title: "Baduk",
          status: "Changes since last publish",
          featuredPosition: 2,
          repositories: 0,
        }),
      ]),
    });
    start(client);
    const stars = await screen.findByTestId("project-stars");
    expect(within(stars).getByText("Draft")).toBeTruthy();
    expect(within(stars).queryByRole("button", { name: "Take down" })).toBeNull();
    const baduk = screen.getByTestId("project-baduk");
    expect(within(baduk).getByText("Changes since last publish")).toBeTruthy();
    expect(within(baduk).getByText("No repository")).toBeTruthy();
    expect(within(baduk).getByText("Yes · 2")).toBeTruthy();
    await userEvent.click(within(baduk).getByRole("button", { name: "Take down" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/Can.t withdraw copies already downloaded/)).toBeTruthy();
    await userEvent.click(within(dialog).getByRole("button", { name: "Take down Baduk" }));
    expect(client.takeDown).toHaveBeenCalledWith("baduk", "Baduk");
  });

  it("shows the empty state and creates a project from a title only", async () => {
    const client = fakeClient({ list: vi.fn(async () => []) });
    start(client);
    expect(await screen.findByText("No projects yet")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "New project" }));
    await userEvent.click(screen.getByRole("button", { name: "Create draft" }));
    expect(screen.getByRole("alert").textContent).toContain("Give the project a title");
    await userEvent.type(screen.getByRole("textbox"), "Chess Bot");
    await userEvent.click(screen.getByRole("button", { name: "Create draft" }));
    await waitFor(() => expect(window.location.hash).toBe("#edit/new"));
    expect(client.create).toHaveBeenCalledWith("Chess Bot");
  });

  it("reports a failure to list", async () => {
    start(
      fakeClient({
        list: vi.fn(async () => Promise.reject(new ApiError(500, "X", "Disk on fire"))),
      }),
    );
    expect((await screen.findByRole("alert")).textContent).toContain("Disk on fire");
  });
});

describe("Editor", () => {
  it("saves at the loaded revision and shows the saved state", async () => {
    const client = fakeClient();
    start(client, "#edit/stars");
    const title = await screen.findByDisplayValue("STARS");
    await userEvent.type(title, " 2");
    expect(screen.getByText(/Unsaved changes/)).toBeTruthy();
    const rights = screen.getByRole("group", { name: "Rights review" });
    expect(within(rights).getByText(/Only you decide/)).toBeTruthy();
    const legends = Array.from(document.querySelectorAll("legend")).map((l) => l.textContent);
    expect(legends.indexOf("Rights review")).toBe(1); // right after Basics
    expect(
      (screen.getByRole("button", { name: "Review publication" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    await userEvent.type(screen.getByLabelText("Alt text for image 1"), "!");
    await userEvent.type(screen.getByLabelText("Caption for image 1"), "Home");
    await userEvent.click(screen.getByRole("checkbox", { name: /Include the live URL/ }));
    await userEvent.click(screen.getByRole("button", { name: "Add a link" }));
    await userEvent.type(screen.getByLabelText("Link 1 label"), "Demo");
    await userEvent.click(screen.getByRole("button", { name: "Add a repository" }));
    await userEvent.click(screen.getByRole("button", { name: "Remove repository 2" }));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(client.save).toHaveBeenCalled());
    const [id, revision, fields, images] = vi.mocked(client.save).mock.calls[0]!;
    expect(id).toBe("stars");
    expect(revision).toBe(5);
    expect(fields.title).toBe("STARS 2");
    expect(fields.liveUrlIncluded).toBe(true);
    expect(fields.links).toEqual([{ kind: "demo", label: "Demo", url: "https://" }]);
    expect(fields.repositories).toEqual([{ url: "https://github.com/mbroadfo/stars" }]);
    expect(images[0]).toMatchObject({ altText: "The atlas!", caption: "Home", lead: true });
    expect(
      await screen.findByText(/Saved · revision 6 · the public copy is unchanged/),
    ).toBeTruthy();
  });

  it("refuses a stale save with a reload action (FR3.4)", async () => {
    const client = fakeClient({
      save: vi.fn(async () =>
        Promise.reject(new ApiError(409, "STALE_REVISION", "this project was saved elsewhere")),
      ),
    });
    start(client, "#edit/stars");
    await userEvent.type(await screen.findByDisplayValue("STARS"), "!");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect((await screen.findByRole("alert")).textContent).toContain("saved elsewhere");
    await userEvent.click(screen.getByRole("button", { name: "Reload the saved version" }));
    await waitFor(() => expect(client.get).toHaveBeenCalledTimes(2));
    expect(await screen.findByDisplayValue("STARS")).toBeTruthy();
  });

  it("asks before leaving with unsaved changes (FR4.6)", async () => {
    start(fakeClient(), "#edit/stars");
    await userEvent.type(await screen.findByDisplayValue("STARS"), "!");
    go("#activity");
    const dialog = await screen.findByRole("dialog", { name: "Leave without saving?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Stay" }));
    expect(screen.getByDisplayValue("STARS!")).toBeTruthy();
    go("#featured");
    await userEvent.click(await screen.findByRole("button", { name: "Discard unsaved changes" }));
    expect(await screen.findByRole("heading", { name: "Featured order" })).toBeTruthy();
  });

  it("shows publish blockers and uploads images when saved", async () => {
    const client = fakeClient({
      get: vi.fn(async () =>
        projectView({
          images: [],
          blockers: [{ message: "Choose a lead image", field: "images" }],
        }),
      ),
      upload: vi.fn(async () =>
        Promise.reject(new ApiError(422, "IMAGE_REJECTED", "only JPEG, PNG and WebP")),
      ),
    });
    start(client, "#edit/stars");
    expect(await screen.findByText("Choose a lead image")).toBeTruthy();
    expect(screen.getByText("No images yet.")).toBeTruthy();
    const input = document.querySelector<HTMLInputElement>('input[type="file"]')!;
    await userEvent.upload(input, new File(["x"], "a.jpg", { type: "image/jpeg" }));
    expect((await screen.findByRole("alert")).textContent).toContain("only JPEG, PNG and WebP");
  });

  it("uploads, chooses the lead and removes images", async () => {
    const two = projectView({
      revision: 6,
      images: [
        ...projectView().images,
        {
          assetRef: "ast_bbbbbbbbbbbbbbbbbbbbbbbb",
          altText: "",
          caption: "",
          width: 500,
          height: 500,
          lead: false,
        },
      ],
    });
    const client = fakeClient({ upload: vi.fn(async () => two) });
    start(client, "#edit/stars");
    await screen.findByDisplayValue("STARS");
    const input = document.querySelector<HTMLInputElement>('input[type="file"]')!;
    await userEvent.upload(input, new File(["x"], "b.png", { type: "image/png" }));
    expect(await screen.findByText(/Uploaded. Add alt text/)).toBeTruthy();
    const radios = screen.getAllByRole("radio");
    await userEvent.click(radios[1]!);
    expect((radios[1] as HTMLInputElement).checked).toBe(true);
    await userEvent.click(screen.getByRole("button", { name: "Remove image 1" }));
    expect(screen.queryByLabelText("Alt text for image 2")).toBeNull();
  });

  it("reports a project that cannot be loaded", async () => {
    start(
      fakeClient({
        get: vi.fn(async () => Promise.reject(new ApiError(404, "NOT_FOUND", "no such project"))),
      }),
      "#edit/x",
    );
    expect((await screen.findByRole("alert")).textContent).toContain("no such project");
  });
});

describe("Publish", () => {
  it("lists everything that becomes public and confirms the reviewed revision (FR7.2)", async () => {
    const client = fakeClient();
    start(client, "#edit/stars");
    await userEvent.click(await screen.findByRole("button", { name: "Review publication" }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText(/revision 5/)).toBeTruthy();
    expect(within(dialog).getByText(/Live URL not published — not authorized/)).toBeTruthy();
    expect(within(dialog).getByText(/could not be confirmed public/)).toBeTruthy();
    expect(within(dialog).getByText(/Source available · Open source · MIT/)).toBeTruthy();
    expect(within(dialog).getByText("Inspiration")).toBeTruthy();
    const rights = within(dialog).getByRole("region", { name: "Rights review" });
    expect(within(rights).getByText(/Not marked as needing one/)).toBeTruthy();
    await userEvent.click(within(dialog).getByRole("button", { name: "Publish this revision" }));
    expect(client.publish).toHaveBeenCalledWith("stars", 5, "0123456789abcdef0123456789abcdef");
    expect(
      (await screen.findAllByText(/published at revision 5. Build the public site/)).length,
    ).toBeGreaterThan(0);
  });

  it("is blocked with the reasons (FR7.3)", async () => {
    const client = fakeClient({
      get: vi.fn(async () => projectView({ status: "Published" })),
      review: vi.fn(async () =>
        review({
          isUpdate: true,
          reviewId: null,
          liveUrl: { url: "https://stars.example.org", reason: "included and authorized" },
          images: [
            { assetRef: "ast_aaaaaaaaaaaaaaaaaaaaaaaa", altText: "", caption: "c", lead: false },
          ],
          blockers: [{ message: "Add alt text to image 1", field: "alt" }],
        }),
      ),
    });
    start(client, "#edit/stars");
    await userEvent.click(await screen.findByRole("button", { name: "Review update" }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("Add alt text to image 1")).toBeTruthy();
    expect(within(dialog).getByText("No alt text")).toBeTruthy();
    expect(within(dialog).getByText("https://stars.example.org")).toBeTruthy();
    const confirm = within(dialog).getByRole("button", { name: "Update the public exhibit" });
    expect((confirm as HTMLButtonElement).disabled).toBe(true);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows a refused confirmation", async () => {
    const client = fakeClient({
      publish: vi.fn(async () =>
        Promise.reject(new ApiError(409, "STALE_REVISION", "this review has expired")),
      ),
    });
    start(client, "#edit/stars");
    await userEvent.click(await screen.findByRole("button", { name: "Review publication" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(
      await within(dialog).findByRole("button", { name: "Publish this revision" }),
    );
    expect((await within(dialog).findByRole("alert")).textContent).toContain("expired");
  });

  it("takes a published exhibit down from the editor", async () => {
    const client = fakeClient({ get: vi.fn(async () => projectView({ status: "Published" })) });
    start(client, "#edit/stars");
    await userEvent.click(await screen.findByRole("button", { name: "Take down" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/featured carousel/)).toBeTruthy();
    expect(within(dialog).getByText(/Astronomy & Exploration/)).toBeTruthy();
    await userEvent.click(within(dialog).getByRole("button", { name: "Take down STARS" }));
    expect(await screen.findByText(/Taken down. Build the site/)).toBeTruthy();
  });
});

describe("Preview", () => {
  it("frames the preview page in a sandbox once it renders", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<html></html>", { status: 200 })),
    );
    start(fakeClient(), "#preview/stars");
    const frame = (await screen.findByTitle("Exhibit page preview")) as HTMLIFrameElement;
    expect(frame.getAttribute("sandbox")).toBe("allow-same-origin");
    expect(frame.getAttribute("src")).toBe("/preview/stars/exhibit");
    expect(screen.getAllByText("Preview — not public").length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole("button", { name: "Home page with its card" }));
    expect(await screen.findByTitle("Home page preview")).toBeTruthy();
  });

  it("explains why a preview cannot be shown", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ message: "to preview, first: Choose a lead image" }), {
            status: 422,
          }),
      ),
    );
    start(fakeClient(), "#preview/stars");
    expect((await screen.findByRole("alert")).textContent).toContain("Choose a lead image");
    expect(screen.queryByTitle("Exhibit page preview")).toBeNull();
  });
});

describe("Featured order, activity and site", () => {
  it("reorders through the explicit confirmation (FR9.7)", async () => {
    const client = fakeClient();
    start(client, "#featured");
    await userEvent.click(await screen.findByRole("button", { name: "Move Baduk up" }));
    expect(screen.getByText(/Featured but not yet published: Chess/)).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Update featured order…" }));
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Update featured order" }),
    );
    expect(client.updateFeatured).toHaveBeenCalledWith(["baduk", "stars"]);
  });

  it("shows the Git history as the activity log (FR7.7)", async () => {
    start(fakeClient(), "#activity");
    expect(await screen.findByText("Publish STARS (revision 5)")).toBeTruthy();
    expect(screen.getByText("2026-10-14 10:00")).toBeTruthy();
  });

  it("builds the site and links to the local site server", async () => {
    const client = fakeClient();
    start(client, "#site");
    expect(await screen.findByText("C:/content/build/site")).toBeTruthy();
    expect(screen.getByRole("link", { name: "View the generated site" }).getAttribute("href")).toBe(
      "http://127.0.0.1:8766/",
    );
    await userEvent.click(screen.getByRole("button", { name: "Build the public site" }));
    expect(await screen.findByText(/15 file\(s\) scanned/)).toBeTruthy();
  });

  it("packages the last build for Pages staging without uploading", async () => {
    const client = fakeClient();
    start(client, "#site");
    await userEvent.click(
      await screen.findByRole("button", { name: "Package for Pages (staging)" }),
    );
    const panel = await screen.findByRole("region", { name: "Pages package" });
    expect(within(panel).getByText(/22 files, 1234567 bytes/)).toBeTruthy();
    expect(within(panel).getByText(/stars \(revision 6\)/)).toBeTruthy();
    expect(within(panel).getByText(/Nothing was uploaded/)).toBeTruthy();
    expect(within(panel).getByText(/Registered in the content repository/)).toBeTruthy();
  });

  it("shows a refused package", async () => {
    start(
      fakeClient({
        packagePages: vi.fn(async () =>
          Promise.reject(new ApiError(422, "PAGES_REFUSED", "run 'build' first")),
        ),
      }),
      "#site",
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Package for Pages (staging)" }),
    );
    expect((await screen.findByRole("alert")).textContent).toContain("run 'build' first");
  });

  it("shows a failed build (the previous site is kept)", async () => {
    start(
      fakeClient({
        build: vi.fn(async () =>
          Promise.reject(new ApiError(500, "BUILD_FAILED", "the public-output scan failed")),
        ),
      }),
      "#site",
    );
    await userEvent.click(await screen.findByRole("button", { name: "Build the public site" }));
    expect((await screen.findByRole("alert")).textContent).toContain("scan failed");
  });
});
