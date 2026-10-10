// Prototype behaviour: featured carousel, mobile menu, scope-notes overlay.
// No autoplay (WCAG 2.2.2); the page is fully readable without this script.
(() => {
  "use strict";

  // Featured: the three public launch candidates. Risk is not featured until
  // Michael approves its public image, description and live link (D-22).
  const slides = [
    {
      img: "assets/live/stars.jpg",
      alt: "STARS: a 3D atlas of real stars around the Sun, with Sirius, Procyon and Altair labelled",
      pos: "50% 50%",
      chip: "Live capture · stars.xaminisalamini.com",
      title: ["STARS"],
      meta: ["Astronomy", "3D", "Runs in your browser"],
      desc: "Fly through the real galaxy — 123,000 stars at their true 3D positions, with instruments no planetarium ships: measurement tethers, closure rates, deep-time scrubbing.",
    },
    {
      img: "assets/live/baduk-board.jpg",
      alt: "A 9×9 Go game in progress between two bots, with the move log beside the board",
      pos: "50% 40%",
      light: true,
      chip: "Live capture · baduk.xaminisalamini.com",
      title: ["Baduk"],
      meta: ["Go", "AI coach", "Runs in your browser"],
      desc: "Learn Go by playing it — four bots from random to search-ahead, and a coach that explains every move.",
    },
    {
      img: "assets/draft/dice-hero.jpg",
      alt: "Two dice on a green gaming table",
      pos: "30% 50%",
      chip: "Draft image · concept art",
      title: ["Monopoly", "Arena"],
      meta: ["AI bots", "Simulation", "Runs in your browser"],
      desc: "A full rules engine and animated board for pitting AI strategies against each other — or training new ones.",
    },
  ];

  const hero = document.querySelector(".hero");
  const img = hero.querySelector(".hero__img");
  const title = hero.querySelector(".hero__title");
  const meta = hero.querySelector(".hero__meta");
  const desc = hero.querySelector(".hero__desc");
  const chip = hero.querySelector(".hero__media .draft-chip");
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
      title.replaceChildren(...s.title.flatMap((line, k) => (k ? [" ", document.createElement("br"), line] : [line])));
      meta.replaceChildren(...s.meta.flatMap((m, k) => {
        if (!k) return [m];
        const dot = document.createElement("span");
        dot.textContent = "·";
        return [" ", dot, " ", m];
      }));
      desc.textContent = s.desc;
      img.classList.toggle("is-light", !!s.light);
      chip.textContent = s.chip;
      chip.classList.toggle("draft-chip--live", s.chip.startsWith("Live"));
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
    if (e.key === "ArrowRight") go(current + 1);
    if (e.key === "ArrowLeft") go(current - 1);
  });

  // Mobile drawer
  const sidebar = document.getElementById("sidebar");
  const menuBtn = document.querySelector(".menu-btn");
  const closeBtn = document.querySelector(".close-btn");
  const scrim = document.querySelector(".scrim");
  function setMenu(open) {
    sidebar.classList.toggle("is-open", open);
    menuBtn.setAttribute("aria-expanded", String(open));
    scrim.hidden = !open;
    (open ? closeBtn : menuBtn).focus();
  }
  menuBtn.addEventListener("click", () => setMenu(true));
  closeBtn.addEventListener("click", () => setMenu(false));
  scrim.addEventListener("click", () => setMenu(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sidebar.classList.contains("is-open")) setMenu(false);
  });

  document.querySelector(".search").addEventListener("submit", (e) => e.preventDefault());

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
