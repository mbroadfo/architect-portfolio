// Home page behaviour: featured carousel (FR9.7), selected-work cards, mobile menu and the
// scope-notes overlay. No autoplay (WCAG 2.2.2); the hero is readable without this script.
(() => {
  "use strict";
  const D = window.PORTFOLIO;
  const S = window.Shell;

  // Featured: published exhibits only, in the owner's order (FR9.7). Risk is not published.
  const slides = D.projects
    .filter((p) => p.featured && !p.pending)
    .sort((a, b) => a.featured - b.featured)
    .map((p) => ({
      slug: p.slug, img: p.lead.src, alt: p.lead.alt, pos: p.lead.pos, light: p.slug === "baduk",
      chip: p.lead.kind === "live" ? `Live capture · ${new URL(p.access.liveUrl).host}` : "Draft image · concept art",
      title: p.title.split(" "), meta: p.meta, desc: p.summary, live: p.access.liveUrl,
    }));

  const hero = document.querySelector(".hero");
  const img = hero.querySelector(".hero__img");
  const title = hero.querySelector(".hero__title");
  const meta = hero.querySelector(".hero__meta");
  const desc = hero.querySelector(".hero__desc");
  const chip = hero.querySelector(".hero__media .draft-chip");
  const view = hero.querySelector(".hero__view");
  const open = hero.querySelector(".hero__open");
  const index = hero.querySelector(".hero__index");
  const dots = [...hero.querySelectorAll(".hero__dots button")];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let current = 0;

  const pad = (n) => String(n).padStart(2, "0");
  hero.querySelector(".hero__total").textContent = pad(slides.length);

  function render(i) {
    const s = slides[i];
    const apply = () => {
      img.src = s.img;
      img.alt = s.alt;
      img.style.objectPosition = s.pos;
      img.classList.toggle("is-light", !!s.light);
      chip.textContent = s.chip;
      chip.classList.toggle("draft-chip--live", s.chip.startsWith("Live"));
      title.replaceChildren(...s.title.flatMap((line, k) => (k ? [" ", document.createElement("br"), line] : [line])));
      meta.replaceChildren(...s.meta.flatMap((m, k) => {
        if (!k) return [m];
        const dot = document.createElement("span");
        dot.textContent = "·";
        return [" ", dot, " ", m];
      }));
      desc.textContent = s.desc;
      view.href = `project.html?p=${s.slug}`;
      open.hidden = !s.live;
      if (s.live) open.href = s.live;
      index.textContent = pad(i + 1);
      dots.forEach((d, k) => d.setAttribute("aria-current", String(k === i)));
      img.classList.remove("is-out");
    };
    if (reduced) return apply();
    img.classList.add("is-out");
    setTimeout(apply, 220);
  }

  function go(i) {
    current = (i + slides.length) % slides.length;
    render(current);
  }

  hero.querySelectorAll(".round-btn").forEach((b) =>
    b.addEventListener("click", () => go(current + Number(b.dataset.dir))));
  dots.forEach((d, k) => d.addEventListener("click", () => go(k)));
  hero.addEventListener("keydown", (e) => {
    if (e.target.closest("a")) return;
    if (e.key === "ArrowRight") go(current + 1);
    if (e.key === "ArrowLeft") go(current - 1);
  });

  // Selected work: published exhibits, then the pending launch candidate (prototype review only).
  document.getElementById("work-cards").innerHTML =
    S.published().concat(D.projects.filter((p) => p.pending)).map(S.card).join("");

  // Mobile drawer
  const sidebar = document.getElementById("sidebar");
  const menuBtn = document.querySelector(".menu-btn");
  const closeBtn = document.querySelector(".close-btn");
  const scrim = document.querySelector(".scrim");
  function setMenu(isOpen) {
    sidebar.classList.toggle("is-open", isOpen);
    menuBtn.setAttribute("aria-expanded", String(isOpen));
    scrim.hidden = !isOpen;
    (isOpen ? closeBtn : menuBtn).focus();
  }
  menuBtn.addEventListener("click", () => setMenu(true));
  closeBtn.addEventListener("click", () => setMenu(false));
  scrim.addEventListener("click", () => setMenu(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sidebar.classList.contains("is-open")) setMenu(false);
  });

  // Scope notes overlay (prototype aid): toggle, or open with ?notes
  const toggle = document.querySelector(".notes-toggle");
  function setNotes(on) {
    document.body.classList.toggle("notes-on", on);
    toggle.setAttribute("aria-pressed", String(on));
    toggle.textContent = on ? "Hide scope notes" : "Show scope notes";
  }
  toggle.addEventListener("click", () => setNotes(!document.body.classList.contains("notes-on")));
  if (new URLSearchParams(location.search).has("notes")) setNotes(true);
})();
