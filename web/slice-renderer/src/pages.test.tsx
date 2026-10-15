// @vitest-environment jsdom
// Public page structure in the approved design (FR9.1 to FR9.8, FR4.10, NFR8), checked on the
// parsed DOM of the rendered HTML with Testing Library queries.
import { getAllByRole, getByRole, queryByRole, within } from "@testing-library/dom";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { publicResolver } from "./cli";
import { render } from "./render";
import { ASSET, exhibit, snapshot } from "./test-fixtures";
import type { Exhibit, PublicSiteSnapshot, RenderOptions } from "./types";

const PUBLIC: RenderOptions = { mode: "public", resolveAsset: publicResolver };
const SOFTWARE = { slug: "software", name: "Software & Tools", position: 3 } as const;
const GAMES = { slug: "games", name: "Games & AI Arenas", position: 0 } as const;

/** Load a rendered page into the jsdom document (scripts never run: runScripts is off). */
function load(html: string): Document {
  document.open();
  document.write(html);
  document.close();
  return document;
}

function page(input: PublicSiteSnapshot, path: string): Document {
  const found = render(input, PUBLIC).pages.find((p) => p.path === path);
  if (!found) throw new Error(`no page ${path}`);
  return load(found.html);
}

function richExhibit(overrides: Partial<Exhibit> = {}): Exhibit {
  return exhibit({
    slug: "alpha",
    title: "Alpha",
    featured: true,
    primaryCategory: SOFTWARE,
    liveUrl: "https://alpha.test.example",
    badges: [{ kind: "inBrowser" }, { kind: "openSource", spdx: "MIT" }],
    publicRepositories: [
      { name: "alpha-repo", url: "https://github.com/example/alpha", licence: "MIT" },
    ],
    ...overrides,
  });
}

function site(exhibits: Exhibit[], featuredOrder: string[] = []): PublicSiteSnapshot {
  const counts = new Map<string, { slug: string; name: string; position: number; n: number }>();
  for (const e of exhibits) {
    const c = e.primaryCategory;
    if (c) counts.set(c.slug, { ...c, n: (counts.get(c.slug)?.n ?? 0) + 1 });
  }
  return snapshot({
    exhibits,
    featuredOrder,
    categories: [...counts.values()].map(({ n, ...c }) => ({ ...c, count: n }) as never),
  });
}

describe("home page (FR9.1, FR9.7, FR9.8)", () => {
  it("renders no carousel when nothing published is featured", () => {
    const doc = page(site([richExhibit({ featured: false })]), "/");
    expect(doc.querySelector(".hero")).toBeNull();
    expect(getByRole(doc.body, "heading", { name: "Selected Work" })).toBeTruthy();
  });

  it("renders featured exhibits in the confirmed order, first slide visible, controls hidden", () => {
    const beta = richExhibit({ slug: "beta", title: "Beta", leadImage: { ...lead(2) } });
    const doc = page(site([richExhibit(), beta], ["beta", "alpha"]), "/");
    const hero = doc.querySelector(".hero");
    expect(hero?.getAttribute("aria-roledescription")).toBe("carousel");
    const slides = [...doc.querySelectorAll(".hero__slide")];
    expect(slides.map((s) => s.getAttribute("aria-label"))).toEqual(["Beta", "Alpha"]);
    expect(slides.map((s) => s.hasAttribute("hidden"))).toEqual([false, true]);
    expect(doc.querySelector(".hero__controls")?.hasAttribute("hidden")).toBe(true);
    expect(
      within(slides[0] as HTMLElement).getByRole("link", { name: /Open the App/ }),
    ).toBeTruthy();
    expect(doc.querySelector(".hero__status")?.getAttribute("aria-live")).toBe("polite");
  });

  it("omits the controls for a single featured exhibit", () => {
    const doc = page(site([richExhibit()], ["alpha"]), "/");
    expect(doc.querySelectorAll(".hero__slide")).toHaveLength(1);
    expect(doc.querySelector(".hero__controls")).toBeNull();
  });

  it("lists the populated categories with their published counts", () => {
    const games = richExhibit({
      slug: "go",
      title: "Go",
      primaryCategory: GAMES,
      leadImage: lead(3),
    });
    const doc = page(
      site([
        richExhibit(),
        games,
        richExhibit({ slug: "gamma", primaryCategory: GAMES, leadImage: lead(4) }),
      ]),
      "/",
    );
    const tiles = [...doc.querySelectorAll(".type")].map((t) => t.textContent);
    expect(tiles).toEqual([
      "Games & AI ArenasPlay them, or watch the bots2 projects",
      "Software & ToolsClone, build, or download1 project",
    ]);
    const nav = getByRole(doc.body, "navigation", { name: "Primary" });
    expect(within(nav).queryByRole("link", { name: "Woodworking" })).toBeNull();
    expect(within(nav).getByRole("link", { name: "Home" }).getAttribute("aria-current")).toBe(
      "page",
    );
  });

  it("shows the installation notice when nothing is published", () => {
    const doc = page(snapshot({ exhibits: [] }), "/");
    expect(doc.querySelector(".notice")?.textContent).toBe("New work is being installed.");
    expect(doc.querySelector(".hero, .cards")).toBeNull();
  });
});

describe("catalog and category pages (FR9.1, FR9.8)", () => {
  const games = () =>
    richExhibit({ slug: "go", title: "Go", primaryCategory: GAMES, leadImage: lead(3) });

  it("lists every published exhibit with chips and a result count", () => {
    const doc = page(site([richExhibit(), games()]), "/work/");
    expect(getByRole(doc.body, "heading", { level: 1 }).textContent).toBe("All Projects");
    const chips = getByRole(doc.body, "navigation", { name: "Browse by category" });
    expect(within(chips).getByRole("link", { name: "All 2" }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(doc.querySelector(".result-count")?.textContent).toBe("2 published exhibits");
    expect(doc.querySelectorAll(".cards--3 .card")).toHaveLength(2);
  });

  it("lists only the category's exhibits on its own page", () => {
    const doc = page(site([richExhibit(), games()]), "/category/games");
    expect(getByRole(doc.body, "heading", { level: 1 }).textContent).toBe("Games & AI Arenas");
    expect(doc.querySelector(".page-head__lede")?.textContent).toBe(
      "Play them, or watch the bots.",
    );
    const cards = [...doc.querySelectorAll(".card h3")].map((h) => h.textContent);
    expect(cards).toEqual(["Go"]);
    const chip = within(getByRole(doc.body, "navigation", { name: "Browse by category" }));
    expect(
      chip.getByRole("link", { name: "Games & AI Arenas 1" }).getAttribute("aria-current"),
    ).toBe("page");
    expect(doc.querySelector(".result-count")?.textContent).toBe("1 published exhibit");
  });

  it("renders no page for an empty category and serves the category 404 page", () => {
    const output = render(site([richExhibit()]), PUBLIC);
    expect(output.pages.map((p) => p.path)).not.toContain("/category/games");
    const missing = output.pages.find((p) => p.path === "/category-404.html");
    expect(missing?.status).toBe(404);
    const doc = load(missing?.html ?? "");
    expect(getByRole(doc.body, "heading", { level: 1 }).textContent).toBe(
      "This category isn't on display",
    );
    expect(getByRole(doc.body, "link", { name: "See all work" }).getAttribute("href")).toBe(
      "/work/",
    );
  });

  it("serves the exhibit 404 page with a link to all work (FR9.3)", () => {
    const doc = page(site([richExhibit()]), "/404.html");
    expect(getByRole(doc.body, "heading", { level: 1 }).textContent).toBe(
      "This exhibit isn't on display",
    );
    expect(doc.querySelector(".eyebrow")?.textContent).toBe("Exhibit");
  });
});

describe("exhibit page (FR9.2, FR4.10)", () => {
  it("omits empty narrative sections and keeps the fixed section order", () => {
    const doc = page(
      site([
        richExhibit({
          sections: {
            outcomes: "It works.",
            inspiration: "Why.",
            designChallenges: "   ",
            implementation: "",
          },
        }),
      ]),
      "/work/alpha",
    );
    const headings = [...doc.querySelectorAll(".story-section h2")].map((h) => h.textContent);
    expect(headings).toEqual(["Inspiration", "Outcomes"]);
    const inPage = getByRole(doc.body, "navigation", { name: "On this page" });
    expect(getAllByRole(inPage, "link").map((a) => a.textContent)).toEqual(["Story", "Details"]);
  });

  it("omits the story, gallery and downloads blocks when they are empty", () => {
    const doc = page(site([richExhibit()]), "/work/alpha");
    expect(doc.querySelector("#story, #gallery, #downloads")).toBeNull();
    expect(doc.querySelector("#details")).not.toBeNull();
  });

  it("renders the badges exactly as C2 lists them", () => {
    const badges = [
      { kind: "bestOnDesktop" },
      { kind: "byInvitation" },
      { kind: "openSource", spdx: "Apache-2.0" },
    ] as const;
    const doc = page(
      site([
        richExhibit({
          badges: [...badges],
          publicRepositories: [
            { name: "r", url: "https://github.com/example/r", licence: "Apache-2.0" },
          ],
        }),
      ]),
      "/work/alpha",
    );
    const labels = [...doc.querySelectorAll(".exhibit-hero .badge")].map((b) => b.textContent);
    expect(labels).toEqual(["Best on desktop", "By invitation", "Open source · Apache-2.0"]);
    expect(doc.querySelector(".exhibit-hero .badge--live")?.textContent).toBe("By invitation");
    const details = doc.querySelector(".exhibit-details")?.textContent ?? "";
    expect(details).toContain("By invitation");
    expect(details).toContain("Best on desktop");
  });

  it("links source code only for public repositories (D-15, D-22)", () => {
    const doc = page(
      site([
        richExhibit({
          badges: [{ kind: "inBrowser" }, { kind: "sourcePrivate" }],
          publicRepositories: [],
        }),
      ]),
      "/work/alpha",
    );
    expect(queryByRole(doc.body, "link", { name: /View source/ })).toBeNull();
    expect(doc.querySelector('a[href^="https://github.com/example/"]')).toBeNull();
    expect(doc.querySelector(".badge:not(.badge--live)")?.textContent).toBe("Source private");
  });

  it("links the live app, public source and owner links that exist", () => {
    const doc = page(
      site([
        richExhibit({
          links: [{ kind: "documentation", label: "Docs", url: "https://docs.test.example" }],
        }),
      ]),
      "/work/alpha",
    );
    expect(getByRole(doc.body, "link", { name: /Open the app/ }).getAttribute("href")).toBe(
      "https://alpha.test.example",
    );
    expect(getByRole(doc.body, "link", { name: /View source/ }).getAttribute("href")).toBe(
      "https://github.com/example/alpha",
    );
    expect(getByRole(doc.body, "link", { name: "Docs" }).getAttribute("href")).toBe(
      "https://docs.test.example",
    );
  });

  it("renders the gallery with an enlarged view that works without script", () => {
    const image = {
      assetRef: "ast_PlaceholderAsset0009",
      altText: "Wide shot",
      caption: "Caption",
      width: 2000,
      height: 1000,
    };
    const doc = page(site([richExhibit({ images: [image] })]), "/work/alpha");
    const link = getByRole(doc.body, "link", { name: "Enlarge Wide shot" });
    expect(link.getAttribute("href")).toBe("/media/ast_PlaceholderAsset0009/w1600.jpg");
    expect(doc.querySelector("#gallery figcaption")?.textContent).toBe("Caption");
  });

  it("renders downloads with their label and type", () => {
    const doc = page(
      site([
        richExhibit({
          attachments: [{ assetRef: ASSET, label: "Cut list", fileType: "PDF", byteSize: 9 }],
        }),
      ]),
      "/work/alpha",
    );
    const link = getByRole(doc.body, "link", { name: "Cut list PDF" });
    expect(link.getAttribute("href")).toBe(`/files/${ASSET}/cut-list.pdf`);
  });

  it("escapes hostile narrative, caption and alt text", () => {
    const hostile = '<img src=x onerror="alert(1)">';
    const image = {
      assetRef: "ast_PlaceholderAsset0009",
      altText: hostile,
      caption: hostile,
      width: 500,
      height: 500,
    };
    const html =
      render(
        site([richExhibit({ sections: { outcomes: hostile }, images: [image] })]),
        PUBLIC,
      ).pages.find((p) => p.path === "/work/alpha")?.html ?? "";
    expect(html).not.toContain("<img src=x");
    expect(html).toContain("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;");
  });
});

describe("images and links (NFR8, D-19, FR9.5)", () => {
  const input = () =>
    site(
      [
        richExhibit({
          images: [
            { assetRef: "ast_PlaceholderAsset0009", altText: "Detail", width: 900, height: 600 },
          ],
        }),
      ],
      ["alpha"],
    );

  it("gives every image an alt attribute and dimensions, and published images their alt text", () => {
    for (const rendered of render(input(), PUBLIC).pages) {
      const doc = load(rendered.html);
      for (const img of doc.querySelectorAll("img")) {
        expect(img.hasAttribute("alt")).toBe(true);
        expect(Number(img.getAttribute("width"))).toBeGreaterThan(0);
        expect(Number(img.getAttribute("height"))).toBeGreaterThan(0);
      }
    }
    const doc = page(input(), "/work/alpha");
    const alts = [...doc.querySelectorAll("img")].map((img) => img.getAttribute("alt"));
    expect(alts).toEqual(["Placeholder illustration", "Detail"]);
  });

  it("links only to site paths, fragments and URLs from the snapshot", () => {
    const allowed = new Set([
      "https://github.com/example",
      "https://github.com/example/alpha",
      "https://alpha.test.example",
    ]);
    for (const rendered of render(input(), PUBLIC).pages) {
      const doc = load(rendered.html);
      for (const element of doc.querySelectorAll("[href], [src]")) {
        const url = element.getAttribute("href") ?? element.getAttribute("src") ?? "";
        expect(url.startsWith("/") || url.startsWith("#") || allowed.has(url), url).toBe(true);
      }
    }
  });

  it("makes the skip link the first focusable element, targeting main", () => {
    const doc = page(input(), "/");
    const first = doc.querySelector("a, button");
    expect(first?.textContent).toBe("Skip to content");
    expect(first?.getAttribute("href")).toBe("#main");
    expect(doc.querySelector("main")?.id).toBe("main");
  });
});

describe("static assets (FR9.5, NFR15)", () => {
  const read = (file: string) => readFileSync(join(process.cwd(), "assets", file), "utf-8");

  it("loads nothing from another origin in the stylesheet", () => {
    const css = read("site.css");
    expect(css).not.toMatch(/@import|url\(\s*["']?(https?:)?\/\//i);
    const urls = [...css.matchAll(/url\("([^"]+)"\)/g)].map((m) => m[1]);
    expect(urls).toHaveLength(5);
    for (const url of urls) expect(url).toMatch(/^[a-z0-9-]+\.[0-9a-f]{10}\.woff2$/);
  });

  it("keeps the script free of network, storage and dynamic code", () => {
    const js = read("site.js");
    expect(js).not.toMatch(
      /fetch\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|document\.cookie|eval\(|new Function|innerHTML|setTimeout|setInterval/,
    );
    const urls = js.match(/https?:\/\/[^"'\s]+/g) ?? [];
    expect(urls).toEqual(["http://www.w3.org/2000/svg"]);
  });

  it("has generated assets that match their sources", () => {
    const cwd = process.cwd();
    expect(() =>
      execFileSync(process.execPath, ["scripts/hash-assets.mjs", "--check"], {
        cwd,
        stdio: "pipe",
      }),
    ).not.toThrow();
  });
});

function lead(n: number) {
  return {
    assetRef: `ast_PlaceholderAsset000${n}`,
    altText: `Lead ${n}`,
    width: 1200,
    height: 800,
  };
}
