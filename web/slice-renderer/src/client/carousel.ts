// Featured carousel (FR9.7, NFR8): progressive enhancement of the server-rendered hero.
// Without this script the first featured exhibit shows and every featured exhibit is also in
// the gallery below. With it, previous/next buttons, a position indicator and dots appear.
// It never advances on its own (WCAG 2.2.2); a change of slide is announced politely; arrow
// keys work while focus is inside the carousel and not on a link; reduced motion skips the
// crossfade.

const pad = (n: number): string => String(n).padStart(2, "0");

function prefersReducedMotion(view: Window | null): boolean {
  return view?.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

interface Parts {
  slides: HTMLElement[];
  controls: HTMLElement;
  dotsHost: HTMLElement;
  status: HTMLElement;
  index: HTMLElement;
  total: HTMLElement;
  prev: HTMLButtonElement;
  next: HTMLButtonElement;
}

function findParts(hero: HTMLElement): Parts | null {
  const one = <T extends Element>(selector: string) => hero.querySelector<T>(selector);
  const parts = {
    slides: Array.from(hero.querySelectorAll<HTMLElement>(".hero__slide")),
    controls: one<HTMLElement>(".hero__controls"),
    dotsHost: one<HTMLElement>(".hero__dots"),
    status: one<HTMLElement>(".hero__status"),
    index: one<HTMLElement>(".hero__index"),
    total: one<HTMLElement>(".hero__total"),
    prev: one<HTMLButtonElement>(".hero__prev"),
    next: one<HTMLButtonElement>(".hero__next"),
  };
  const { slides, controls, dotsHost, status, index, total, prev, next } = parts;
  if (slides.length < 2 || !controls || !dotsHost || !status || !index || !total) return null;
  if (!prev || !next) return null;
  return { slides, controls, dotsHost, status, index, total, prev, next };
}

function makeDots(parts: Parts, doc: Document): HTMLButtonElement[] {
  return parts.slides.map((_slide, position) => {
    const dot = doc.createElement("button");
    dot.type = "button";
    dot.setAttribute("aria-label", `Featured project ${position + 1}`);
    parts.dotsHost.append(dot);
    return dot;
  });
}

/** Enhance one `.hero` carousel. Returns the slide selector, or null when there is nothing to do. */
export function enhanceCarousel(hero: HTMLElement): ((position: number) => void) | null {
  const parts = findParts(hero);
  if (!parts) return null;
  const doc = hero.ownerDocument;
  const reduced = prefersReducedMotion(doc.defaultView);
  const dots = makeDots(parts, doc);
  const count = parts.slides.length;
  let current = Math.max(
    0,
    parts.slides.findIndex((slide) => !slide.hidden),
  );

  const show = (position: number, announce: boolean): void => {
    current = (position + count) % count;
    parts.slides.forEach((slide, k) => {
      slide.hidden = k !== current;
      slide.classList.toggle("is-entering", k === current && announce && !reduced);
    });
    dots.forEach((dot, k) => dot.setAttribute("aria-current", String(k === current)));
    parts.index.textContent = pad(current + 1);
    if (announce) {
      const title = parts.slides[current]?.getAttribute("aria-label") ?? "";
      parts.status.textContent = `${title}, featured project ${current + 1} of ${count}`;
    }
  };

  parts.prev.addEventListener("click", () => show(current - 1, true));
  parts.next.addEventListener("click", () => show(current + 1, true));
  dots.forEach((dot, k) => dot.addEventListener("click", () => show(k, true)));
  hero.addEventListener("keydown", (event) => {
    if (event.target instanceof Element && event.target.closest("a")) return;
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    show(current + (event.key === "ArrowRight" ? 1 : -1), true);
  });

  parts.total.textContent = pad(count);
  parts.controls.hidden = false;
  parts.dotsHost.hidden = false;
  show(current, false);
  return (position: number) => show(position, true);
}
