// Catalog / category pages and project detail pages. Production pre-renders these at export
// (FR7.4); the prototype renders them client-side from data.js.
(() => {
  "use strict";
  const D = window.PORTFOLIO;
  const S = window.Shell;
  const { esc, ic } = S;
  const params = new URLSearchParams(location.search);
  const page = document.body.dataset.page;

  function notOnDisplay(main, kind) {
    document.title = `Not on display — Michael Broadfoot (Prototype R5)`;
    main.innerHTML = `
      <section class="section missing" aria-labelledby="missing-h" data-note="FR9.3 / FR9.8: production answers with HTTP 404">
        <p class="eyebrow">${kind === "category" ? "Category" : "Exhibit"}</p>
        <h1 id="missing-h">This ${kind === "category" ? "category" : "exhibit"} isn't on display</h1>
        <p class="page-head__lede">It may have been taken down, or it hasn't been published yet.</p>
        <a class="btn btn--primary" href="catalog.html">See all work ${ic("i-arrow")}</a>
      </section>`;
  }

  // ---------------------------------------------------------------- catalog
  function catalog() {
    const cid = params.get("category");
    S.render({ active: cid ? "" : "all", current: cid || "" });
    const main = document.querySelector("main");
    const live = S.liveCategories();
    const cat = cid ? live.find((c) => c.id === cid) : null;
    if (cid && !cat) { notOnDisplay(main, "category"); return; }

    const published = S.published();
    const shown = published.filter((p) => !cat || p.category === cat.id);
    // Prototype only: show the unpublished launch candidate in its pending state for design review.
    const pending = D.projects.filter((p) => p.pending && (!cat || p.category === cat.id));

    if (cat) {
      document.title = `${cat.name} — Michael Broadfoot (Prototype R5)`;
      document.getElementById("catalog-eyebrow").textContent = "Category";
      document.getElementById("catalog-h").textContent = cat.name;
      document.getElementById("catalog-lede").textContent = cat.sub + ".";
    }

    const chip = (href, label, n, on) =>
      `<a class="chip" href="${href}"${on ? ' aria-current="page"' : ""}>${esc(label)} <span class="chip__n">${n}</span></a>`;
    document.getElementById("catalog-chips").innerHTML =
      chip("catalog.html", "All", published.length, !cat) +
      live.map((c) => chip(`catalog.html?category=${c.id}`, c.name, D.byCategory(c.id).filter((p) => !p.pending).length, cat && cat.id === c.id)).join("");
    document.getElementById("catalog-chips").dataset.note = "Categories: one primary category per project; empty categories hidden (FR9.8)";

    document.getElementById("catalog-count").textContent =
      `${shown.length} published ${shown.length === 1 ? "exhibit" : "exhibits"}`;
    document.getElementById("catalog-cards").innerHTML = shown.concat(pending).map(S.card).join("");
  }

  // ---------------------------------------------------------------- project
  function project() {
    const p = D.find(params.get("p") || "");
    S.render({ current: p && !p.pending ? p.category : "" });
    const main = document.querySelector("main");
    if (!p || p.pending) { notOnDisplay(main, "exhibit"); return; }

    document.title = `${p.title} — Michael Broadfoot (Prototype R5)`;
    const c = D.cat(p.category);
    const repo = p.repos.find((r) => r.visibility === "public");
    const sections = D.narrativeOrder.filter(([k]) => p.narrative[k]);
    const navItems = [["story", "Story"], ...(p.gallery.length || p.galleryNote ? [["gallery", "Gallery"]] : []),
      ...(p.files.length ? [["downloads", "Downloads"]] : []), ["details", "Details"]];

    main.innerHTML = `
      <article class="exhibit"${p.provisional ? ' data-note="Title and artwork provisional until the rights review (FR10.6); cannot publish until it is complete"' : ""}>
        <header class="exhibit-hero">
          <div class="exhibit-hero__media">
            <img src="${p.lead.src}" alt="${esc(p.lead.alt)}" style="object-position:${p.lead.pos || "50% 50%"}">
            ${S.chip(p.lead.kind, p.lead.kind === "live" ? "Live capture" : "Draft image · concept art")}
          </div>
          <div class="exhibit-hero__copy">
            <a class="back-link" href="catalog.html${c ? `?category=${c.id}` : ""}">${ic("i-prev")}${c ? esc(c.name) : "All projects"}</a>
            <h1>${esc(p.title)}</h1>
            <p class="exhibit-hero__summary">${esc(p.summary)}</p>
            <p class="hero__meta">${p.meta.map(esc).join(" <span>·</span> ")}</p>
            <div class="hero__actions">
              ${p.access.liveUrl ? `<a class="btn btn--primary" href="${esc(p.access.liveUrl)}" rel="noopener">Open the app ${ic("i-external")}</a>` : ""}
              ${repo ? `<a class="btn btn--ghost" href="${esc(repo.url)}" rel="noopener">${ic("i-github")} View source</a>` : ""}
            </div>
            <div class="card__foot">${S.badgeHtml(p)}</div>
          </div>
        </header>

        <nav class="exhibit-nav" aria-label="On this page">
          ${navItems.map(([id, label]) => `<a href="#${id}">${label}</a>`).join("")}
        </nav>

        <div class="exhibit-body">
          <div class="exhibit-story" id="story">
            <p class="draft-note" data-note="Drafted from the public README; not owner-approved (FR10.1)">Draft case study · drafted from the project's public README · not yet approved</p>
            ${sections.map(([k, label]) => `
            <section class="story-section" aria-labelledby="s-${k}">
              <h2 id="s-${k}">${label}</h2>
              <p>${esc(p.narrative[k])}</p>
            </section>`).join("")}
          </div>

          <aside class="exhibit-details" id="details" aria-labelledby="details-h">
            <h2 id="details-h">Details</h2>
            <dl>
              ${c ? `<div><dt>${ic(c.icon)}Category</dt><dd><a href="catalog.html?category=${c.id}">${esc(c.name)}</a></dd></div>` : ""}
              <div><dt>${ic("i-cloud")}Access</dt><dd>${p.access.liveUrl ? "Runs in your browser · no account needed" : "Not available online"}</dd></div>
              <div><dt>${ic("i-gamepad")}Phones</dt><dd>${p.access.phone === "suitable" ? "Works on phones" : p.access.phone === "desktop" ? "Best on desktop" : "Not yet tested"}</dd></div>
              <div><dt>${ic("i-code")}Source</dt><dd>${repo ? (repo.licence ? `Open source · ${esc(repo.licence)}` : "Source available (all rights reserved)") : "Private"}</dd></div>
              <div><dt>${ic("i-grid")}Highlights</dt><dd>${p.meta.map(esc).join(", ")}</dd></div>
            </dl>
          </aside>
        </div>

        <section class="exhibit-gallery" id="gallery" aria-labelledby="gallery-h">
          <h2 id="gallery-h">Gallery</h2>
          ${p.gallery.length ? `<ul class="gallery">${p.gallery.map((g, i) => `
            <li><figure>
              <button class="gallery__btn" type="button" data-index="${i}" aria-label="Enlarge: ${esc(g.caption)}">
                <img src="${g.src}" alt="${esc(g.alt)}" loading="lazy" style="object-position:${g.pos || "50% 50%"}">
                ${S.chip(g.kind)}
              </button>
              <figcaption>${esc(g.caption)}</figcaption>
            </figure></li>`).join("")}</ul>`
            : `<p class="gallery-note" data-note="FR10.6: no artwork resembling third-party trade dress until the rights review">${esc(p.galleryNote || "No images yet.")}</p>`}
        </section>
      </article>`;

    lightbox(p.gallery);
  }

  function lightbox(items) {
    const dlg = document.getElementById("lightbox");
    if (!dlg || !items.length) return;
    const img = document.getElementById("lightbox-img");
    const cap = document.getElementById("lightbox-caption");
    const count = document.getElementById("lightbox-count");
    let at = 0, opener = null;
    const show = (i) => {
      at = (i + items.length) % items.length;
      img.src = items[at].src; img.alt = items[at].alt;
      cap.textContent = items[at].caption + (items[at].kind === "live" ? " · Live capture" : " · Draft image");
      count.textContent = `${at + 1} / ${items.length}`;
    };
    document.querySelectorAll(".gallery__btn").forEach((b) => b.addEventListener("click", () => {
      opener = b; show(Number(b.dataset.index)); dlg.showModal();
    }));
    dlg.querySelectorAll("[data-step]").forEach((b) => b.addEventListener("click", () => show(at + Number(b.dataset.step))));
    document.getElementById("lightbox-close").addEventListener("click", () => dlg.close());
    dlg.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") show(at + 1);
      if (e.key === "ArrowLeft") show(at - 1);
    });
    dlg.addEventListener("close", () => opener && opener.focus());
    dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  }

  if (page === "catalog") catalog();
  if (page === "project") project();
})();
