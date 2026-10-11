// Public-site shell for the catalog and project pages: prototype strip, sidebar, mobile bar,
// footer, mobile menu and the scope-notes overlay. Navigation lists only categories that have
// at least one published exhibit (FR9.1, FR9.8).
window.Shell = (() => {
  "use strict";
  const D = window.PORTFOLIO;
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const ic = (id, cls = "ic") => `<svg class="${cls}" aria-hidden="true"><use href="#${id}"/></svg>`;
  const published = () => D.projects.filter((p) => !p.pending);
  // ?export shows exactly what a production export would contain: no pending candidates (FR9.1, FR10.1).
  // Design-review data includes pending candidates; the export snapshot (export/publication.js)
  // contains none, so nothing here can surface them on the simulated public site.
  const pendingShown = () => D.projects.filter((p) => p.pending);
  const BANNER = {
    review: "<strong>Design review view</strong> · Shows unapproved launch candidates for review — this is not the public export · <em>Live captures</em> are from the deployed apps; <em>Draft</em> images are concept art · Copy is not owner-approved",
    export: "<strong>Simulated public export</strong> · Built only from the approved-publication snapshot · Approvals here are simulated for the prototype; nothing is published",
  };
  const liveCategories = () => D.categories.filter((c) => published().some((p) => p.category === c.id));

  // FR9.4 footer. Pages that replace <main> content re-append it (site.js).
  function footerHtml() {
    return `
      <footer class="site-foot">
        <p class="site-foot__mark">Michael Broadfoot</p>
        <ul>
          <li><a href="https://github.com/mbroadfo">${ic("i-github")}GitHub</a></li>
          <li><span class="owner-input owner-input--inline" data-note="Owner content input: the public email address (FR9.4). Becomes a mailto: link once Michael supplies it.">Email address to come</span></li>
        </ul>
        <p class="site-foot__copy">© 2026 Michael Broadfoot</p>
      </footer>`;
  }

  function render({ active = "", current = "" } = {}) {
    const nav = liveCategories().map((c) => `
          <li><a href="catalog.html?category=${c.id}"${current === c.id ? ' aria-current="page"' : ""}>${ic(c.icon)}${esc(c.name)}</a></li>`).join("");

    document.body.insertAdjacentHTML("afterbegin", `
  <a class="skip" href="#main">Skip to content</a>
  <div class="proto-strip" role="note">
    <p>${BANNER[D.mode] || BANNER.review}</p>
    <button class="notes-toggle" type="button" aria-pressed="false">Show scope notes</button>
  </div>`);

    const shell = document.querySelector(".shell");
    shell.insertAdjacentHTML("afterbegin", `
    <header class="mobile-bar">
      <a class="wordmark wordmark--stacked" href="index.html">Michael<br>Broadfoot</a>
      <button class="icon-btn menu-btn" type="button" aria-controls="sidebar" aria-expanded="false" aria-label="Open menu">${ic("i-menu")}</button>
    </header>
    <aside class="sidebar" id="sidebar" aria-label="Site">
      <div class="sidebar__top">
        <a class="wordmark" href="index.html">Michael Broadfoot</a>
        <p class="tagline">Systems Architect <span aria-hidden="true">·</span> Builder <span aria-hidden="true">·</span> Explorer</p>
        <button class="icon-btn close-btn" type="button" aria-label="Close menu">${ic("i-close")}</button>
      </div>
      <nav class="side-nav" aria-label="Primary">
        <ul>
          <li><a href="index.html"${active === "home" ? ' aria-current="page"' : ""}>${ic("i-home")}Home</a></li>
          <li><a href="catalog.html"${active === "all" ? ' aria-current="page"' : ""}>${ic("i-grid")}All Projects</a></li>
        </ul>
        <p class="side-nav__label" data-note="Only categories with a published exhibit appear (FR9.1)">Categories</p>
        <ul>${nav}
        </ul>
        <ul class="side-nav__secondary">
          <li><a href="index.html#about">${ic("i-info")}About</a></li>
        </ul>
      </nav>
      <figure class="credo">
        <blockquote>Good systems — in software, in wood, in life — start with structure, curiosity, and respect for the material.</blockquote>
        <figcaption class="signature">M. Broadfoot</figcaption>
      </figure>
    </aside>
    <div class="scrim" hidden></div>`);

    document.querySelector("main").insertAdjacentHTML("beforeend", footerHtml());

    document.querySelector("main").setAttribute("tabindex", "-1");
    wire();
  }

  function wire() {
    const sidebar = document.getElementById("sidebar");
    const menuBtn = document.querySelector(".menu-btn");
    const closeBtn = document.querySelector(".close-btn");
    const scrim = document.querySelector(".scrim");
    const setMenu = (open) => {
      sidebar.classList.toggle("is-open", open);
      menuBtn.setAttribute("aria-expanded", String(open));
      scrim.hidden = !open;
      (open ? closeBtn : menuBtn).focus();
    };
    menuBtn.addEventListener("click", () => setMenu(true));
    closeBtn.addEventListener("click", () => setMenu(false));
    scrim.addEventListener("click", () => setMenu(false));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && sidebar.classList.contains("is-open")) setMenu(false);
    });

    const toggle = document.querySelector(".notes-toggle");
    const setNotes = (on) => {
      document.body.classList.toggle("notes-on", on);
      toggle.setAttribute("aria-pressed", String(on));
      toggle.textContent = on ? "Hide scope notes" : "Show scope notes";
    };
    toggle.addEventListener("click", () => setNotes(!document.body.classList.contains("notes-on")));
    if (new URLSearchParams(location.search).has("notes")) setNotes(true);
  }

  function badgeHtml(p) {
    return (p.badges || D.badges(p)).map((b) => `<span class="badge${b.tone === "live" ? " badge--live" : b.tone === "pending" ? " badge--pending" : ""}">${esc(b.text)}</span>`).join("");
  }

  function chip(kind, text) {
    if (!kind) return "";
    return `<span class="draft-chip draft-chip--sm${kind === "live" ? " draft-chip--live" : ""}">${esc(text || (kind === "live" ? "Live capture" : "Draft image"))}</span>`;
  }

  // One card renderer for the home page, catalog and category pages.
  function card(p) {
    const c = D.cat(p.category);
    const img = p.lead
      ? `<a class="card__img" href="project.html?p=${p.slug}" tabindex="-1" aria-hidden="true"><img src="${p.lead.src}" alt="" loading="lazy" style="object-position:${p.lead.pos || "50% 50%"}">${chip(p.lead.kind)}</a>`
      : p.repos.some((r) => r.visibility === "private")
        ? `<div class="card__img card__img--empty"><span class="placeholder">${ic("i-flag", "ic ic--xl")}<span>Image awaiting approval</span><small>Source is private — nothing is drawn from it without approval (D-22)</small></span></div>`
        : `<div class="card__img card__img--empty"><span class="placeholder">${ic("i-image", "ic ic--xl")}<span>No lead image yet</span><small>Choose a lead image with alt text before publishing (FR7.3)</small></span></div>`;
    const title = p.pending
      ? `<h3>${ic(p.icon)}<span>${esc(p.title)}</span></h3>`
      : `<h3>${ic(p.icon)}<a href="project.html?p=${p.slug}">${esc(p.title)}</a></h3>`;
    const summary = p.summary
      ? `<p>${esc(p.summary)}</p>`
      : p.pending
        ? `<p class="pending">Description to come. It will be written only from material Michael approves for publication.</p>`
        : `<p class="pending">No summary yet.</p>`;
    const note = p.pending
      ? "Not published: content, rights (FR10.6) and live-URL (FR10.7) approvals outstanding — absent from the live site until approved"
      : p.provisional ? "Title and artwork provisional until the rights review (FR10.6)" : "";
    return `
          <li class="card${p.pending ? " card--pending" : ""}"${note ? ` data-note="${esc(note)}"` : ""}>
            ${img}
            <div class="card__body">
              ${c ? `<p class="card__cat">${esc(c.name)}</p>` : ""}
              ${title}
              ${summary}
              <div class="card__foot">${badgeHtml(p)}</div>
            </div>
          </li>`;
  }

  return { render, footerHtml, card, badgeHtml, chip, esc, ic, published, pendingShown, liveCategories, BANNER };
})();
