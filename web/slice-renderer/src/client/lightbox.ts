// Enlarged image view (FR9.2; accessibility checklist "Enlarged image view"). Each gallery
// image is a link to its largest variant, so without this script it opens the image itself.
// With it, the link opens a native modal <dialog>: named previous/next buttons, arrow keys
// step, Escape closes (native), and focus returns to the image that opened it. The dialog is
// built with DOM methods only: no HTML strings, no inline styles or handlers.

const SVG_NS = "http://www.w3.org/2000/svg";
const ICONS = {
  prev: ["M19 12H5", "m11 6-6 6 6 6"],
  next: ["M5 12h14", "m13 6 6 6-6 6"],
} as const;

interface Item {
  href: string;
  alt: string;
  caption: string;
}

function icon(doc: Document, paths: readonly string[]): SVGSVGElement {
  const svg = doc.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "ic");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  for (const d of paths) {
    const path = doc.createElementNS(SVG_NS, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

function button(doc: Document, className: string, label: string): HTMLButtonElement {
  const element = doc.createElement("button");
  element.type = "button";
  element.className = className;
  element.setAttribute("aria-label", label);
  return element;
}

function itemFor(link: HTMLAnchorElement): Item {
  const alt = link.querySelector("img")?.getAttribute("alt") ?? "";
  const caption = link.closest("figure")?.querySelector("figcaption")?.textContent ?? "";
  return { href: link.href, alt, caption: caption || alt };
}

interface Viewer {
  dialog: HTMLDialogElement;
  show: (position: number) => void;
  step: (delta: number) => void;
}

function buildViewer(doc: Document, items: Item[]): Viewer {
  const dialog = doc.createElement("dialog");
  dialog.className = "lightbox";
  dialog.setAttribute("aria-labelledby", "lightbox-caption");
  const frame = doc.createElement("div");
  frame.className = "lightbox__frame";
  const image = doc.createElement("img");
  const caption = doc.createElement("p");
  caption.className = "lightbox__caption";
  caption.id = "lightbox-caption";
  const controls = doc.createElement("div");
  controls.className = "lightbox__controls";
  const prev = button(doc, "round-btn", "Previous image");
  prev.append(icon(doc, ICONS.prev));
  const next = button(doc, "round-btn", "Next image");
  next.append(icon(doc, ICONS.next));
  const count = doc.createElement("span");
  count.className = "lightbox__count";
  const close = doc.createElement("button");
  close.type = "button";
  close.className = "btn btn--ghost lightbox__close";
  close.textContent = "Close";
  if (items.length > 1) controls.append(prev, count, next);
  controls.append(close);
  frame.append(image, caption, controls);
  dialog.append(frame);
  doc.body.append(dialog);

  let at = 0;
  const show = (position: number): void => {
    at = (position + items.length) % items.length;
    const item = items[at] as Item;
    image.src = item.href;
    image.alt = item.alt;
    caption.textContent = item.caption;
    count.textContent = `${at + 1} / ${items.length}`;
  };
  const step = (delta: number): void => show(at + delta);
  prev.addEventListener("click", () => step(-1));
  next.addEventListener("click", () => step(1));
  close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight") step(1);
    if (event.key === "ArrowLeft") step(-1);
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  return { dialog, show, step };
}

function isPlainClick(event: MouseEvent): boolean {
  return event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey;
}

/** Enhance the gallery links; returns the number of images wired, 0 when unsupported. */
export function enhanceLightbox(doc: Document): number {
  const links = Array.from(doc.querySelectorAll<HTMLAnchorElement>(".gallery__btn"));
  const dialogClass = doc.defaultView?.HTMLDialogElement;
  if (links.length === 0 || typeof dialogClass?.prototype.showModal !== "function") return 0;
  const items = links.map(itemFor);
  let viewer: Viewer | null = null;
  let opener: HTMLElement | null = null;

  links.forEach((link, position) => {
    link.addEventListener("click", (event) => {
      if (!isPlainClick(event)) return;
      event.preventDefault();
      if (!viewer) {
        viewer = buildViewer(doc, items);
        viewer.dialog.addEventListener("close", () => opener?.focus());
      }
      opener = link;
      viewer.show(position);
      viewer.dialog.showModal();
    });
  });
  return links.length;
}
