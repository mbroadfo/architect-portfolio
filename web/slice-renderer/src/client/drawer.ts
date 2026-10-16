// Mobile navigation drawer (design-system-mapping: Sidebar / MobileBar / Drawer).
// Without this script the menu link targets #sidebar and CSS `:target` opens the drawer; the
// close link targets #main. With it, both behave as buttons: the menu reports aria-expanded,
// focus moves into the drawer and back, Escape and the scrim close it.

function actAsButton(link: HTMLElement, onActivate: () => void): void {
  link.setAttribute("role", "button");
  link.addEventListener("click", (event) => {
    event.preventDefault();
    onActivate();
  });
  link.addEventListener("keydown", (event) => {
    if (event.key !== " ") return;
    event.preventDefault();
    onActivate();
  });
}

/** Enhance the drawer; returns false when the page has no drawer markup. */
export function enhanceDrawer(doc: Document): boolean {
  const sidebar = doc.getElementById("sidebar");
  const menu = doc.querySelector<HTMLElement>(".menu-btn");
  const close = doc.querySelector<HTMLElement>(".close-btn");
  const scrim = doc.querySelector<HTMLElement>(".scrim");
  if (!sidebar || !menu || !close || !scrim) return false;

  const setOpen = (open: boolean): void => {
    sidebar.classList.toggle("is-open", open);
    menu.setAttribute("aria-expanded", String(open));
    scrim.hidden = !open;
    (open ? close : menu).focus();
  };

  menu.setAttribute("aria-expanded", "false");
  actAsButton(menu, () => setOpen(true));
  actAsButton(close, () => setOpen(false));
  scrim.addEventListener("click", () => setOpen(false));
  doc.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && sidebar.classList.contains("is-open")) setOpen(false);
  });
  return true;
}
