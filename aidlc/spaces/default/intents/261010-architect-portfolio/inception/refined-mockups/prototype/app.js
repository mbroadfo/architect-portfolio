// Home page behaviour: featured carousel (FR9.7), selected-work cards, mobile menu and the
// scope-notes overlay. No autoplay (WCAG 2.2.2); the hero is readable without this script.
(() => {
  "use strict";
  const D = window.PORTFOLIO;
  const S = window.Shell;

  // Featured: published exhibits only, in the owner's order (FR9.7).
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
  // Dots, category tiles and category navigation are all derived from the loaded data set.
  document.getElementById("hero-dots").innerHTML = slides.map((s, k) =>
    `<button type="button" aria-label="Featured project ${k + 1}"${k ? "" : ' aria-current="true"'}></button>`).join("");
  const dots = [...hero.querySelectorAll(".hero__dots button")];
  const cats = S.liveCategories();
  const count = (c) => S.published().filter((p) => p.category === c.id).length;
  document.getElementById("nav-cats").innerHTML = cats.map((c) =>
    `<li><a href="catalog.html?category=${c.id}">${S.ic(c.icon)}${S.esc(c.name)}</a></li>`).join("");
  document.getElementById("type-tiles").innerHTML = cats.map((c) => `
          <li class="type">
            <a href="catalog.html?category=${c.id}">
              <span class="type__img"><img src="${c.image.src}" alt="" loading="lazy">${S.chip(c.image.kind, c.image.kind === "live" ? "Live" : "Draft")}</span>
              <span class="type__body">
                ${S.ic(c.icon, "ic ic--lg")}
                <span class="type__title">${S.esc(c.name)}</span>
                <span class="type__sub">${S.esc(c.sub)}</span>
                <span class="type__count">${count(c)} ${count(c) === 1 ? "project" : "projects"}</span>
              </span>
            </a>
          </li>`).join("");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let current = 0;

  const pad = (n) => String(n).padStart(2, "0");
  hero.querySelector(".hero__total").textContent = pad(slides.length);

  function render(i, immediate) {
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
    if (reduced || immediate) return apply();
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

  // Hero: the static markup is replaced from the data set's first featured exhibit at once.
  if (slides.length) render(0, true); else hero.hidden = true; // FR9.7: no empty frame

  // Selected work: published exhibits, then pending candidates (design-review data only).
  document.getElementById("work-cards").innerHTML =
    S.published().concat(S.pendingShown()).map(S.card).join("");

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
