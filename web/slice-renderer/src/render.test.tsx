// Renderer tests (Step 16; AC0.5, AC0.6, BR4.1, BR4.2; C11 contract tests).
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { publicResolver } from "./cli";
import { render } from "./render";
import { STATIC_ASSETS } from "./static-assets";
import { ASSET, exhibit, snapshot } from "./test-fixtures";
import { RenderInputError, type RenderOptions } from "./types";

const PUBLIC: RenderOptions = { mode: "public", resolveAsset: publicResolver };
const PREVIEW: RenderOptions = {
  mode: "preview",
  resolveAsset: publicResolver,
  previewSlug: "placeholder-project",
};

function html(options: RenderOptions, path = "/work/placeholder-project", input = snapshot()) {
  const page = render(input, options).pages.find((p) => p.path === path);
  if (!page) throw new Error(`no page ${path}`);
  return page.html;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("escaping (AC0.6, BR4.2)", () => {
  it("renders hostile title and summary as text, never markup", () => {
    const hostile = snapshot({
      exhibits: [
        exhibit({
          title: '<script>alert("x")</script> & "quotes"',
          summary: "<img src=x onerror=alert(1)> summary",
        }),
      ],
    });
    const page = html(PUBLIC, "/work/placeholder-project", hostile);
    expect(page).toContain(
      "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; &quot;quotes&quot;",
    );
    expect(page).toContain("&lt;img src=x onerror=alert(1)&gt; summary");
    expect(page).not.toMatch(/<script/i);
    expect(page).not.toMatch(/<img src=x/i);
  });

  it("produces no inline scripts, styles or separator comments on any page", () => {
    for (const page of render(snapshot(), PUBLIC).pages) {
      expect(page.html).not.toMatch(/<script|<style|style=|<!--/i);
    }
  });
});

describe("invalid input (C11 RenderInputError)", () => {
  it.each([
    ["an extra field", { ...snapshot(), privateNotes: "x" }],
    ["a missing field", { ...snapshot(), site: undefined }],
    ["a bad slug", snapshot({ exhibits: [exhibit({ slug: "Bad Slug" })] })],
    [
      "a repository host link",
      snapshot({
        exhibits: [
          exhibit({ links: [{ kind: "demo", label: "x", url: "https://github.com/a/b" }] }),
        ],
      }),
    ],
    ["an over-long title", snapshot({ exhibits: [exhibit({ title: "x".repeat(121) })] })],
  ])("throws RenderInputError for %s", (_name, input) => {
    expect(() => render(input as never, PUBLIC)).toThrow(RenderInputError);
  });

  it("throws before rendering when options are invalid", () => {
    expect(() => render(snapshot(), { ...PUBLIC, mode: "draft" as never })).toThrow(/unknown mode/);
    expect(() => render(snapshot(), { mode: "public", resolveAsset: null as never })).toThrow(
      /resolveAsset/,
    );
    expect(() => render(snapshot(), { ...PREVIEW, previewSlug: undefined })).toThrow(/previewSlug/);
    expect(() => render(snapshot(), { ...PREVIEW, previewSlug: "missing" })).toThrow(/previewSlug/);
  });
});

describe("preview marking (AC0.5, BR4.1)", () => {
  it("marks every preview page 'Preview — not public' with noindex", () => {
    for (const page of render(snapshot(), PREVIEW).pages) {
      expect(page.html).toContain('<p class="preview-banner">Preview — not public</p>');
      expect(page.html).toContain('<meta name="robots" content="noindex"/>');
    }
  });

  it("never marks public pages", () => {
    for (const page of render(snapshot(), PUBLIC).pages) {
      expect(page.html).not.toContain("Preview — not public");
      expect(page.html).not.toContain("noindex");
    }
  });
});

describe("determinism and purity (C11)", () => {
  it("gives byte-identical output for the same input", () => {
    expect(JSON.stringify(render(snapshot(), PUBLIC))).toBe(
      JSON.stringify(render(snapshot(), PUBLIC)),
    );
  });

  it("reads no clock, randomness, network or timers while rendering", () => {
    const boom = () => {
      throw new Error("impure call");
    };
    vi.spyOn(Date, "now").mockImplementation(boom);
    vi.spyOn(Math, "random").mockImplementation(boom);
    vi.stubGlobal("fetch", boom);
    vi.stubGlobal("setTimeout", boom);
    expect(render(snapshot(), PUBLIC).pages.length).toBeGreaterThan(0);
  });
});

describe("pages and required assets (C9, C8)", () => {
  it("renders the C9 pages for one exhibit", () => {
    const output = render(snapshot(), PUBLIC);
    expect(output.contractVersion).toBe("1.0");
    expect(output.pages.map((p) => [p.path, p.status])).toEqual([
      ["/", 200],
      ["/work/", 200],
      ["/work/placeholder-project", 200],
      ["/404.html", 404],
      ["/category-404.html", 404],
    ]);
    expect(output.staticAssets).toEqual([STATIC_ASSETS.site.path]);
  });

  it("shows the installation notice when nothing is published", () => {
    const home = render(snapshot({ exhibits: [] }), PUBLIC).pages[0];
    expect(home?.html).toContain("New work is being installed.");
  });

  it.each([
    [400, ["w480"]],
    [1000, ["w480", "w960"]],
    [2000, ["w480", "w960", "w1600"]],
  ])("requires the C8 variants for width %i", (width, variants) => {
    const input = snapshot({
      exhibits: [exhibit({ leadImage: { assetRef: ASSET, altText: "a", width, height: 10 } })],
    });
    const required = render(input, PUBLIC).requiredImages;
    expect(required).toHaveLength(variants.length * 2);
    expect(new Set(required.map((r) => r.variant))).toEqual(new Set(variants));
  });

  it("encodes a narrow image's w480 variant at its own width", () => {
    expect(html(PUBLIC)).toContain(`srcSet="/media/${ASSET}/w480.webp 400w"`);
  });

  it("renders featured exhibits, categories, links, repositories and downloads", () => {
    const rich = snapshot({
      exhibits: [
        exhibit({
          featured: true,
          primaryCategory: { slug: "software", name: "Software", position: 0 },
          images: [
            { assetRef: "ast_PlaceholderAsset0002", altText: "b", width: 1000, height: 500 },
          ],
          links: [{ kind: "demo", label: "Demo", url: "https://demo.test.example" }],
          liveUrl: "https://demo.test.example",
          badges: [{ kind: "inBrowser" }, { kind: "openSource", spdx: "MIT" }],
          publicRepositories: [
            { name: "repo", url: "https://github.com/example/repo", licence: "MIT" },
          ],
          attachments: [
            { assetRef: ASSET, label: "Plans & Drawings", fileType: "PDF", byteSize: 10 },
          ],
        }),
      ],
      featuredOrder: ["placeholder-project"],
      categories: [{ slug: "software", name: "Software", position: 0, count: 1 }],
    });
    const output = render(rich, PUBLIC);
    expect(output.pages.map((p) => p.path)).toContain("/category/software");
    expect(output.requiredDownloads).toEqual([
      { assetRef: ASSET, downloadName: "plans-drawings.pdf" },
    ]);
    const home = output.pages[0]?.html ?? "";
    expect(home).toContain("Featured");
    expect(home).toContain('href="/category/software"');
    const page = output.pages.find((p) => p.path === "/work/placeholder-project")?.html ?? "";
    expect(page).toContain(`href="/files/${ASSET}/plans-drawings.pdf"`);
    expect(page).toContain('href="https://github.com/example/repo"');
    expect(page).toContain('href="https://demo.test.example"');
  });

  it("references the static asset whose hash matches its content", () => {
    const css = readFileSync(new URL("../assets/site.css", import.meta.url));
    const hash = createHash("sha256").update(css).digest("hex").slice(0, 10);
    expect(STATIC_ASSETS.site.path).toBe(`/assets/site.${hash}.css`);
  });
});
