// @vitest-environment jsdom
// Progressive enhancement script (FR9.7, FR9.2, NFR8): carousel, drawer and enlarged view,
// exercised on the renderer's own markup.
import { getByRole } from "@testing-library/dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { publicResolver } from "../cli";
import { render } from "../render";
import { exhibit, snapshot } from "../test-fixtures";
import type { Exhibit } from "../types";
import { enhanceCarousel } from "./carousel";
import { enhanceDrawer } from "./drawer";
import { enhanceLightbox } from "./lightbox";
import { enhance } from "./main";

function featured(slug: string, title: string): Exhibit {
  return exhibit({
    slug,
    title,
    featured: true,
    leadImage: {
      assetRef: `ast_Placeholder${slug}Asset0`,
      altText: title,
      width: 500,
      height: 300,
    },
    images: [
      {
        assetRef: `ast_Placeholder${slug}Image1`,
        altText: `${title} one`,
        caption: "One",
        width: 2000,
        height: 900,
      },
      {
        assetRef: `ast_Placeholder${slug}Image2`,
        altText: `${title} two`,
        width: 700,
        height: 900,
      },
    ],
  });
}

function load(path: string, slugs = ["alpha", "bravo", "charlie"]): void {
  const input = snapshot({
    exhibits: slugs.map((slug) => featured(slug, slug.toUpperCase())),
    featuredOrder: slugs,
  });
  const html = render(input, { mode: "public", resolveAsset: publicResolver }).pages.find(
    (p) => p.path === path,
  )?.html;
  document.open();
  document.write(html ?? "");
  document.close();
}

const hero = () => document.querySelector<HTMLElement>(".hero") as HTMLElement;
const visibleSlide = () =>
  [...document.querySelectorAll(".hero__slide")].filter((s) => !s.hasAttribute("hidden"));

function key(target: Element, name: string): void {
  target.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true }));
}

beforeEach(() => {
  vi.stubGlobal("matchMedia", (query: string) => ({ matches: false, media: query }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("featured carousel (FR9.7)", () => {
  it("reveals the controls, dots and position indicator", () => {
    load("/");
    expect(enhanceCarousel(hero())).not.toBeNull();
    expect(document.querySelector(".hero__controls")?.hasAttribute("hidden")).toBe(false);
    expect(document.querySelectorAll(".hero__dots button")).toHaveLength(3);
    expect(document.querySelector(".hero__count")?.textContent).toBe("01/03");
  });

  it("steps with the buttons, wraps around and announces politely", () => {
    load("/");
    enhanceCarousel(hero());
    getByRole(document.body, "button", { name: "Next featured project" }).click();
    expect(visibleSlide().map((s) => s.getAttribute("aria-label"))).toEqual(["BRAVO"]);
    expect(document.querySelector(".hero__status")?.textContent).toBe(
      "BRAVO, featured project 2 of 3",
    );
    getByRole(document.body, "button", { name: "Previous featured project" }).click();
    getByRole(document.body, "button", { name: "Previous featured project" }).click();
    expect(visibleSlide()[0]?.getAttribute("aria-label")).toBe("CHARLIE");
    expect(document.querySelector(".hero__index")?.textContent).toBe("03");
    const dots = [...document.querySelectorAll(".hero__dots button")];
    expect(dots.map((d) => d.getAttribute("aria-current"))).toEqual(["false", "false", "true"]);
    (dots[0] as HTMLButtonElement).click();
    expect(visibleSlide()[0]?.getAttribute("aria-label")).toBe("ALPHA");
  });

  it("follows arrow keys inside the carousel but not on a link", () => {
    load("/");
    enhanceCarousel(hero());
    const next = document.querySelector(".hero__next") as HTMLElement;
    key(next, "ArrowRight");
    expect(visibleSlide()[0]?.getAttribute("aria-label")).toBe("BRAVO");
    key(next, "ArrowLeft");
    expect(visibleSlide()[0]?.getAttribute("aria-label")).toBe("ALPHA");
    key(document.querySelector(".hero__view") as HTMLElement, "ArrowRight");
    key(next, "Enter");
    expect(visibleSlide()[0]?.getAttribute("aria-label")).toBe("ALPHA");
  });

  it("never advances on its own", () => {
    vi.useFakeTimers();
    load("/");
    enhanceCarousel(hero());
    vi.advanceTimersByTime(60_000);
    expect(visibleSlide()[0]?.getAttribute("aria-label")).toBe("ALPHA");
    vi.useRealTimers();
  });

  it("crossfades only without reduced motion", () => {
    load("/");
    enhanceCarousel(hero())?.(1);
    expect(visibleSlide()[0]?.classList.contains("is-entering")).toBe(true);
    vi.stubGlobal("matchMedia", (query: string) => ({ matches: true, media: query }));
    load("/");
    enhanceCarousel(hero())?.(1);
    expect(visibleSlide()[0]?.classList.contains("is-entering")).toBe(false);
  });

  it("does nothing for a single featured exhibit", () => {
    load("/", ["alpha"]);
    expect(enhanceCarousel(hero())).toBeNull();
  });
});

describe("navigation drawer", () => {
  it("opens and closes as a button, with focus and aria-expanded", () => {
    load("/");
    expect(enhanceDrawer(document)).toBe(true);
    const menu = getByRole(document.body, "button", { name: "Open menu" });
    expect(menu.getAttribute("aria-expanded")).toBe("false");
    menu.click();
    const sidebar = document.getElementById("sidebar");
    expect(sidebar?.classList.contains("is-open")).toBe(true);
    expect(menu.getAttribute("aria-expanded")).toBe("true");
    expect(document.activeElement?.getAttribute("aria-label")).toBe("Close menu");
    expect(document.querySelector(".scrim")?.hasAttribute("hidden")).toBe(false);
    key(document.body, "Escape");
    expect(sidebar?.classList.contains("is-open")).toBe(false);
    expect(document.activeElement).toBe(menu);
    key(menu, " ");
    expect(sidebar?.classList.contains("is-open")).toBe(true);
    (document.querySelector(".scrim") as HTMLElement).click();
    expect(sidebar?.classList.contains("is-open")).toBe(false);
    key(menu, "a");
    menu.click();
    getByRole(document.body, "button", { name: "Close menu" }).click();
    expect(sidebar?.classList.contains("is-open")).toBe(false);
  });

  it("reports when there is no drawer", () => {
    document.body.innerHTML = "<p>nothing</p>";
    expect(enhanceDrawer(document)).toBe(false);
  });
});

describe("enlarged image view (FR9.2)", () => {
  function stubDialog(): void {
    HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
      this.setAttribute("open", "");
    };
    HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
      this.removeAttribute("open");
      this.dispatchEvent(new Event("close"));
    };
  }

  it("opens a modal dialog on the clicked image, steps and returns focus", () => {
    stubDialog();
    load("/work/alpha");
    expect(enhanceLightbox(document)).toBe(2);
    const first = document.querySelector<HTMLAnchorElement>(".gallery__btn") as HTMLAnchorElement;
    first.focus();
    first.click();
    const dialog = document.querySelector("dialog.lightbox") as HTMLDialogElement;
    expect(dialog.hasAttribute("open")).toBe(true);
    const image = dialog.querySelector("img") as HTMLImageElement;
    expect(image.getAttribute("src")).toContain("/media/ast_PlaceholderalphaImage1/w1600.jpg");
    expect(image.alt).toBe("ALPHA one");
    expect(dialog.querySelector(".lightbox__caption")?.textContent).toBe("One");
    expect(dialog.querySelector(".lightbox__count")?.textContent).toBe("1 / 2");
    getByRole(dialog, "button", { name: "Next image" }).click();
    expect(dialog.querySelector(".lightbox__caption")?.textContent).toBe("ALPHA two");
    key(dialog, "ArrowRight");
    expect(dialog.querySelector(".lightbox__count")?.textContent).toBe("1 / 2");
    key(dialog, "ArrowLeft");
    getByRole(dialog, "button", { name: "Previous image" }).click();
    expect(dialog.querySelector(".lightbox__count")?.textContent).toBe("1 / 2");
    getByRole(dialog, "button", { name: "Close" }).click();
    expect(dialog.hasAttribute("open")).toBe(false);
    expect(document.activeElement).toBe(first);
    first.click();
    dialog.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(dialog.hasAttribute("open")).toBe(false);
    expect(document.querySelectorAll("dialog")).toHaveLength(1);
  });

  it("leaves modified clicks to the browser", () => {
    stubDialog();
    load("/work/alpha");
    enhanceLightbox(document);
    const link = document.querySelector(".gallery__btn") as HTMLElement;
    link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, ctrlKey: true }));
    expect(document.querySelector("dialog")).toBeNull();
  });

  it("keeps the plain links when dialogs are unsupported or there is no gallery", () => {
    load("/work/alpha");
    const proto = HTMLDialogElement.prototype as unknown as { showModal?: unknown };
    const original = proto.showModal;
    proto.showModal = undefined;
    try {
      expect(enhanceLightbox(document)).toBe(0);
    } finally {
      proto.showModal = original;
    }
    load("/");
    expect(enhanceLightbox(document)).toBe(0);
  });
});

describe("entry point", () => {
  it("enhances every part of the page", () => {
    load("/");
    enhance(document);
    expect(document.querySelector(".hero__controls")?.hasAttribute("hidden")).toBe(false);
    expect(document.querySelector(".menu-btn")?.getAttribute("role")).toBe("button");
  });
});
