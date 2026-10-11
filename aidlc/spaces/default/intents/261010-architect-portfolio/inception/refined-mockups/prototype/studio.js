// Studio prototype (S1–S8). Simulated, in-memory only: nothing is saved, sent, checked or
// published. Contracts it demonstrates: FR1 (owner sign-in), FR2 (discovery), FR3 (title-only
// projects, statuses), FR4 (images, attachments, access metadata), FR5 (AI panel states),
// FR6 (preview), FR7 (publish confirmation), FR8 (take-down), FR9.7/9.8 (featured, category),
// FR10.5–10.7 (reachability, rights review, withheld live URL).
(() => {
  "use strict";
  const D = window.PORTFOLIO;
  const S = window.Shell;
  const { esc, ic } = S;
  const main = document.getElementById("studio-main");
  const bar = document.querySelector(".studio-bar");
  const status = document.getElementById("sr-status");
  const NOW = "2026-10-10 23:04 UTC";
  const FEATURED_MAX = 5;

  // ------------------------------------------------------------------ state
  const initialStatus = { stars: "Published", baduk: "Changes since last publish", "monopoly-arena": "Draft", risk: "Draft" };
  let projects = D.projects.map((p, n) => {
    const imgs = [];
    if (p.lead) imgs.push({ src: p.lead.src, alt: p.lead.alt, lead: true, kind: p.lead.kind });
    for (const g of p.gallery) if (!imgs.some((i) => i.src === g.src)) imgs.push({ src: g.src, alt: g.alt, lead: false, kind: g.kind });
    return {
      id: p.slug, title: p.title, summary: p.summary || "", category: p.category, featured: p.featured || 0,
      status: initialStatus[p.slug] || "Draft", provisional: p.provisional,
      rightsReview: !p.provisional, liveWithheld: !!p.access.liveWithheld, liveAuthorized: !p.access.liveWithheld,
      liveUrl: p.access.liveUrl || "", access: p.access.requirement, phone: p.access.phone,
      repos: p.repos.map((r) => ({ name: r.url ? r.url.split("/").pop() : null, visibility: r.visibility, licence: r.licence, url: r.url, readAt: NOW })),
      narrative: Object.assign({ inspiration: "", challenges: "", decisions: "", implementation: "", outcomes: "", lessons: "" }, p.narrative),
      images: imgs, files: [], revision: 10 + n, updated: "2026-10-10",
    };
  });
  const activity = [
    { t: "2026-10-10 22:41", a: "Published", p: "STARS" },
    { t: "2026-10-10 22:44", a: "Published", p: "Baduk" },
    { t: "2026-10-10 22:52", a: "Saved changes", p: "Baduk" },
  ];
  const repos = [
    ["stars", "public", "2026-08-17"], ["baduk", "public", "2026-08-25"], ["monopoly-arena", "public", "2026-08-17"],
    ["architect-portfolio", "public", "2026-10-10"], ["ai-arcade", "public", "2026-10-07"], ["zork-observatory", "public", "2026-10-01"],
    ["doom-slayer", "public", "2026-09-30"], ["DriveMinder", "public", "2026-09-24"], ["spa-on-aws", "public", "2026-07-19"],
    ["craps_simulator", "public", "2026-07-16"], [null, "private", "—"],
  ];
  let signedIn = false;
  let editing = null;      // { id, buffer, dirty }
  let pendingHash = null;

  const find = (id) => projects.find((p) => p.id === id);
  const announce = (msg) => { status.textContent = ""; setTimeout(() => { status.textContent = msg; }, 30); };
  const catOptions = (sel) => `<option value="">No category</option>` +
    D.categories.map((c) => `<option value="${c.id}"${sel === c.id ? " selected" : ""}>${esc(c.name)}</option>`).join("");
  const statusPill = (s) => `<span class="status status--${s.split(" ")[0].toLowerCase()}">${esc(s)}</span>`;
  const isPublic = (p) => p.status === "Published" || p.status === "Changes since last publish";

  // Badges derived from access metadata only (FR4.10); fail closed on unconfirmed visibility.
  function badgesFor(p) {
    const out = [];
    const urlIncluded = p.liveUrl && (!p.liveWithheld || p.liveAuthorized);
    if (urlIncluded && p.access === "open") out.push("In browser");
    if (urlIncluded && p.access === "sign-in") out.push("Sign-in required");
    if (urlIncluded && p.access === "invitation") out.push("By invitation");
    if (p.phone === "desktop") out.push("Best on desktop");
    for (const r of p.repos) {
      if (r.visibility !== "public") out.push("Source private");
      else out.push(r.licence ? `Open source · ${r.licence}` : "Source available");
    }
    return out;
  }

  // Simulated reachability check (FR10.5, NFR17 labels). The real check runs server-side.
  function reach(url) {
    if (!url) return null;
    let u;
    try { u = new URL(url); } catch { return { label: "Not reachable", note: "This isn't a valid address." }; }
    if (u.protocol !== "https:" || (u.port && u.port !== "443")) return { label: "Not reachable", note: "Only https on port 443 is checked." };
    if (/^(localhost|127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|\[)/.test(u.hostname) || /^\d+$/.test(u.hostname))
      return { label: "Refused (non-public address)", note: "No request was sent." };
    return { label: "Reachable", note: `at ${NOW} (simulated). Reachability shows only that the address answered; it is not a security or publication check.` };
  }

  function blockers(p) {
    const b = [];
    if (!p.title.trim()) b.push(["Add a title", "f-title"]);
    if (!p.images.some((i) => i.lead)) b.push(["Choose a lead image", "f-images"]);
    p.images.forEach((im, k) => { if (!im.alt.trim()) b.push([`Add alt text to image ${k + 1}`, `alt-${k}`]); });
    if (p.provisional && !p.rightsReview) b.push(["Complete the rights review (FR10.6)", "f-rights"]);
    if (p.files.some((f) => f.state === "checking")) b.push(["Wait for file checks to finish", "f-files"]);
    return b;
  }

  // ----------------------------------------------------------------- router
  function route() {
    const h = location.hash.replace(/^#/, "") || "signin";
    if (editing && editing.dirty && !h.startsWith(`edit/${editing.id}`)) {
      pendingHash = h;
      history.replaceState(null, "", `#edit/${editing.id}`);
      document.getElementById("dlg-leave").showModal();
      document.getElementById("leave-stay").focus();
      return;
    }
    const [view, arg] = h.split("/");
    if (view !== "signin" && view !== "private" && !signedIn) { signedIn = true; }
    bar.hidden = view === "signin" || view === "private";
    document.querySelectorAll("[data-nav]").forEach((a) => a.toggleAttribute("aria-current", a.dataset.nav === view));
    if (view !== "edit") editing = null;
    const views = { signin, private: privateView, projects: projectsView, discover, edit: editor, preview, featured, activity: activityView };
    (views[view] || projectsView)(arg);
    main.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  // ------------------------------------------------------------------ views
  function signin() {
    signedIn = false;
    main.innerHTML = `
      <section class="signin" aria-labelledby="signin-h">
        <p class="studio-mark studio-mark--lg">Michael Broadfoot <span>Studio</span></p>
        <h1 id="signin-h">Sign in to the Studio</h1>
        <p class="signin__lede">This workspace is private. Sign-in uses the identity provider and always asks for a second factor.</p>
        <a class="btn btn--primary btn--wide" href="#projects">Continue to sign in ${ic("i-arrow")}</a>
        <p class="signin__fine" data-note="FR1.1: owner matched on issuer + immutable subject; no self-registration">Only the owner's account is admitted. There is no sign-up.</p>
        <a class="link-quiet" href="#private">See what anyone else sees</a>
      </section>`;
  }

  function privateView() {
    main.innerHTML = `
      <section class="signin" aria-labelledby="private-h">
        <p class="studio-mark studio-mark--lg">Michael Broadfoot <span>Studio</span></p>
        <h1 id="private-h">This workspace is private.</h1>
        <p class="signin__lede">You're signed in with an account that isn't the owner's, so nothing here is shown (FR1.1).</p>
        <a class="btn btn--ghost" href="#signin">Sign out</a>
      </section>`;
  }

  function projectsView(arg) {
    const list = arg === "empty" ? [] : projects;
    main.innerHTML = `
      <header class="studio-head">
        <div><h1>Projects</h1><p class="studio-head__sub">${list.length} ${list.length === 1 ? "project" : "projects"} · nothing changes on the public site until you publish</p></div>
        <div class="studio-head__actions">
          <button class="btn btn--primary" type="button" data-act="new">${ic("i-plus")} New project</button>
          <a class="btn btn--ghost" href="#discover">${ic("i-github")} Discover a repository</a>
        </div>
      </header>
      ${list.length ? `
      <div class="ptable" role="table" aria-label="Projects">
        <div class="ptable__row ptable__row--head" role="row">
          <span role="columnheader">Project</span><span role="columnheader">Category</span><span role="columnheader">Status</span>
          <span role="columnheader">Featured</span><span role="columnheader">Source</span><span role="columnheader"><span class="visually-hidden">Actions</span></span>
        </div>
        ${list.map((p) => `
        <div class="ptable__row" role="row">
          <span role="cell" class="ptable__title"><a href="#edit/${p.id}">${esc(p.title || "Untitled")}</a>${p.provisional ? ` <span class="tag tag--warn" title="Rights review outstanding (FR10.6)">Provisional</span>` : ""}</span>
          <span role="cell" data-label="Category">${p.category ? esc(D.cat(p.category).name) : "—"}</span>
          <span role="cell" data-label="Status">${statusPill(p.status)}</span>
          <span role="cell" data-label="Featured">${p.featured ? `${ic("i-star")} ${p.featured}` : "—"}</span>
          <span role="cell" data-label="Source">${p.repos.length ? p.repos.map((r) => r.visibility === "public" ? esc(r.name) : "PRIVATE").join(", ") : "No repository"}</span>
          <span role="cell" class="ptable__actions">
            <a class="btn btn--sm btn--ghost" href="#edit/${p.id}">${ic("i-edit")} Edit</a>
            <a class="btn btn--sm btn--ghost" href="#preview/${p.id}">${ic("i-eye")} Preview</a>
            ${isPublic(p) ? `<button class="btn btn--sm btn--danger" type="button" data-act="takedown" data-id="${p.id}">Take down</button>` : ""}
          </span>
        </div>`).join("")}
      </div>` : `
      <div class="empty" data-note="FR3.5: empty state offers New project and Discover">
        ${ic("i-grid", "ic ic--xl")}
        <h2>No projects yet</h2>
        <p>Start from a title, a drawing, a photograph — or a GitHub repository.</p>
        <div class="studio-head__actions">
          <button class="btn btn--primary" type="button" data-act="new">${ic("i-plus")} New project</button>
          <a class="btn btn--ghost" href="#discover">${ic("i-github")} Discover a GitHub repository</a>
        </div>
      </div>`}`;
  }

  function discover() {
    const linked = (name) => projects.find((p) => p.repos.some((r) => r.name === name));
    main.innerHTML = `
      <header class="studio-head">
        <div><h1>Discover a repository</h1><p class="studio-head__sub">Read-only GitHub access · linking never changes a repository or publishes anything (FR2.5)</p></div>
      </header>
      <label class="field field--search"><span class="field__label">Search repositories</span><input type="search" id="repo-q" placeholder="Name"></label>
      <ul class="repo-list" id="repo-list">
        ${repos.map(([name, vis, upd]) => {
          const p = name && linked(name);
          return `<li class="repo" data-name="${esc(name || "")}">
            <span class="repo__name">${name ? esc(name) : `<em>Private repository</em> <span class="repo__hint">(name hidden in this public prototype)</span>`}</span>
            <span class="repo__vis${vis === "private" ? " repo__vis--private" : ""}">${vis === "private" ? "PRIVATE" : "public"}</span>
            <span class="repo__upd">Updated ${upd}</span>
            ${p ? `<a class="btn btn--sm btn--ghost" href="#edit/${p.id}">Open ${esc(p.title)}</a>`
                : `<button class="btn btn--sm btn--ghost" type="button" data-act="new" data-repo="${esc(name || "private")}">Create project</button>`}
          </li>`;
        }).join("")}
      </ul>
      <p class="repo-empty" id="repo-empty" hidden>No repository matches. Your search is kept.</p>`;
    const q = document.getElementById("repo-q");
    q.addEventListener("input", () => {
      let shown = 0;
      document.querySelectorAll(".repo").forEach((li) => {
        const hit = li.dataset.name.toLowerCase().includes(q.value.trim().toLowerCase());
        li.hidden = !hit; shown += hit;
      });
      document.getElementById("repo-empty").hidden = shown > 0;
    });
  }

  function editor(id) {
    const p = find(id);
    if (!p) { projectsView(); return; }
    editing = { id, dirty: false };
    const narr = D.narrativeOrder;
    const repoPublic = p.repos.some((r) => r.visibility === "public");
    main.innerHTML = `
      <header class="studio-head studio-head--editor">
        <div>
          <a class="back-link" href="#projects">${ic("i-prev")}Projects</a>
          <h1 id="editor-h">${esc(p.title || "Untitled")}</h1>
          <p class="studio-head__sub">${statusPill(p.status)} <span class="savestate" id="savestate" aria-live="polite">Saved · revision ${p.revision}</span></p>
        </div>
        <div class="studio-head__actions">
          <button class="btn btn--ghost" type="button" data-act="save" id="btn-save">Save</button>
          <a class="btn btn--ghost" href="#preview/${p.id}">${ic("i-eye")} Preview</a>
          <button class="btn btn--primary" type="button" data-act="publish" data-id="${p.id}">${isPublic(p) ? "Review update" : "Review publication"}</button>
        </div>
      </header>
      <a class="skip-ai" href="#ai-panel">Jump to AI suggestions</a>
      <div class="editor">
        <form class="editor__form" id="editor-form" novalidate>
          <fieldset class="fs" id="f-basics"><legend>Basics</legend>
            <label class="field"><span class="field__label">Title <span class="req">required</span></span>
              <input id="f-title" name="title" value="${esc(p.title)}"></label>
            ${p.provisional ? `<p class="field__note field__note--warn">${ic("i-alert")} Working title — provisional until the rights review is complete (FR10.6).</p>` : ""}
            <label class="field"><span class="field__label">Summary</span>
              <textarea name="summary" rows="2">${esc(p.summary)}</textarea></label>
            <div class="field-row">
              <label class="field"><span class="field__label">Primary category</span>
                <select name="category">${catOptions(p.category)}</select>
                <span class="field__hint">One primary category in this release (FR9.8).</span></label>
              <div class="field"><span class="field__label" id="feat-l">Home page</span>
                <label class="check"><input type="checkbox" name="featured" ${p.featured ? "checked" : ""} aria-describedby="feat-h"> Feature in the carousel</label>
                <span class="field__hint" id="feat-h">Goes public with this project's Publish or Update. Change the order under Featured order.</span>
                <span class="field__error" id="feat-err" hidden>Up to ${FEATURED_MAX} projects can be featured. Unfeature one first.</span></div>
            </div>
          </fieldset>

          <fieldset class="fs" id="f-story"><legend>Story</legend>
            <p class="field__hint">Empty sections are left off the public page.</p>
            ${narr.map(([k, label]) => `<label class="field"><span class="field__label">${label}</span><textarea name="n-${k}" rows="3">${esc(p.narrative[k] || "")}</textarea></label>`).join("")}
          </fieldset>

          <fieldset class="fs" id="f-images"><legend>Images</legend>
            <p class="field__hint">JPEG, PNG, WebP or HEIC, up to 10 MB each. HEIC photos are converted to web images; only the converted copy is ever published. Every image needs alt text.</p>
            <ul class="assets">${p.images.map((im, k) => `
              <li class="asset">
                <img src="${im.src}" alt="">
                <label class="field"><span class="field__label">Alt text for image ${k + 1}</span><input id="alt-${k}" name="alt-${k}" value="${esc(im.alt)}"></label>
                <label class="check"><input type="radio" name="lead" value="${k}" ${im.lead ? "checked" : ""}> Lead image</label>
              </li>`).join("") || `<li class="asset asset--empty">No images yet.</li>`}
            </ul>
            <button class="btn btn--ghost btn--sm" type="button" data-act="add-image">${ic("i-upload")} Add images</button>
          </fieldset>

          <fieldset class="fs" id="f-files"><legend>Maker and design files</legend>
            <p class="field__hint">PDF, SKP, FCStd, DXF, STL, ZIP or VSDX, up to 50 MB each. Files are offered as downloads only if you include them at Publish; they're never shown in the browser.</p>
            <ul class="assets" id="file-list">${filesHtml(p)}</ul>
            <button class="btn btn--ghost btn--sm" type="button" data-act="add-file">${ic("i-upload")} Add files</button>
          </fieldset>

          <fieldset class="fs" id="f-links"><legend>Links and access</legend>
            ${p.liveWithheld ? `
            <label class="field"><span class="field__label">Live app URL</span>
              <input value="Withheld from this public prototype" disabled aria-describedby="live-h"></label>
            <p class="field__note field__note--warn" id="live-h">${ic("i-lock")} Excluded from every public export until you record that the live URL is authorized after a privacy and security review (FR10.7).</p>
            <label class="check" id="f-live-auth"><input type="checkbox" name="liveAuthorized" ${p.liveAuthorized ? "checked" : ""}> Live URL authorized for publication</label>`
            : `
            <label class="field"><span class="field__label">Live app URL <span class="opt">optional</span></span>
              <input name="liveUrl" type="url" value="${esc(p.liveUrl)}" placeholder="https://"></label>`}
            <div class="field-row">
              <label class="field"><span class="field__label">Access to the linked app</span>
                <select name="access">${[["open", "Open — no account"], ["sign-in", "Sign-in required"], ["invitation", "By invitation"]].map(([v, l]) => `<option value="${v}"${p.access === v ? " selected" : ""}>${l}</option>`).join("")}</select></label>
              <label class="field"><span class="field__label">Phone suitability</span>
                <select name="phone">${[["suitable", "Works on phones"], ["desktop", "Desktop only"], ["unknown", "Not yet tested"]].map(([v, l]) => `<option value="${v}"${p.phone === v ? " selected" : ""}>${l}</option>`).join("")}</select></label>
            </div>
            <div class="field"><span class="field__label">Repositories <span class="opt">optional</span></span>
              <ul class="repo-linked">${p.repos.map((r) => `
                <li>${r.visibility === "public" ? `${ic("i-github")} ${esc(r.name)} <span class="repo__vis">public</span> <span class="repo__upd">${r.licence ? esc(r.licence) : "no licence"} · read from GitHub ${esc(r.readAt)}</span>`
                  : `${ic("i-lock")} <em>Private repository</em> <span class="repo__vis repo__vis--private">PRIVATE</span> <span class="repo__upd">never linked or named publicly</span>`}</li>`).join("") || `<li class="repo__upd">No repository linked. That's fine — repositories are optional.</li>`}
              </ul>
              <a class="btn btn--ghost btn--sm" href="#discover">${ic("i-link")} Link a repository</a></div>
            ${p.provisional ? `
            <div class="field" id="f-rights"><span class="field__label">Rights review</span>
              <label class="check"><input type="checkbox" name="rightsReview" ${p.rightsReview ? "checked" : ""}> Rights review complete — names and artwork cleared</label>
              <span class="field__hint">Required before this project can be published (FR10.6).</span></div>` : ""}
            <div class="field"><span class="field__label">Public badges (derived, not editable)</span>
              <div class="card__foot" id="badge-preview">${badgesFor(p).map((b) => `<span class="badge">${esc(b)}</span>`).join("")}</div></div>
          </fieldset>
        </form>

        <aside class="editor__aside">
          <section class="panel" id="ai-panel" tabindex="-1" aria-labelledby="ai-h">
            <h2 id="ai-h">${ic("i-sparkle")} AI description</h2>
            ${p.repos.length === 0
              ? `<p>Suggestions need a linked repository (FR5.1). Write this project's text yourself, or link a repository.</p>`
              : `<p><strong>Provider:</strong> none approved yet.</p>
                 <p>AI suggestions need your approval of pay-per-use spending and a monthly limit before anything is sent (FR5.8).${repoPublic ? "" : " This project's repository is private, so the provider must also be approved for private content (FR5.9)."}</p>
                 <button class="btn btn--ghost btn--sm" type="button" disabled>Suggest description</button>`}
          </section>
          <section class="panel" aria-labelledby="card-h">
            <h2 id="card-h">${ic("i-image")} Card preview</h2>
            <ul class="cards cards--1">${S.card(toPublic(p))}</ul>
          </section>
        </aside>
      </div>`;

    const form = document.getElementById("editor-form");
    form.addEventListener("input", (e) => {
      editing.dirty = true;
      document.getElementById("savestate").textContent = "Unsaved changes · the public copy is unchanged";
      if (e.target.name === "featured" && e.target.checked && projects.filter((x) => x.featured && x.id !== p.id).length >= FEATURED_MAX) {
        e.target.checked = false;
        document.getElementById("feat-err").hidden = false;
      }
    });
  }

  function filesHtml(p) {
    return p.files.map((f, k) => `
      <li class="asset asset--file">
        ${ic("i-file")}
        <span class="asset__name">${esc(f.name)} <span class="repo__upd">${esc(f.type)} · ${esc(f.size)}</span></span>
        <span class="asset__state${f.state === "accepted" ? " asset__state--ok" : ""}" aria-live="polite">${f.state === "checking" ? "Checking file…" : `${ic("i-check")} Accepted`}</span>
        <label class="check"><input type="checkbox" name="include-${k}" ${f.include ? "checked" : ""}> Include at Publish</label>
      </li>`).join("") || `<li class="asset asset--empty">No files yet.</li>`;
  }

  function collect(p) {
    const f = new FormData(document.getElementById("editor-form"));
    p.title = (f.get("title") || "").toString();
    p.summary = (f.get("summary") || "").toString();
    p.category = (f.get("category") || "").toString() || null;
    const feat = f.get("featured") === "on";
    if (feat && !p.featured) p.featured = Math.max(0, ...projects.map((x) => x.featured)) + 1;
    if (!feat) p.featured = 0;
    for (const [k] of D.narrativeOrder) p.narrative[k] = (f.get(`n-${k}`) || "").toString();
    p.images.forEach((im, k) => { im.alt = (f.get(`alt-${k}`) || "").toString(); im.lead = String(k) === f.get("lead"); });
    p.files.forEach((fl, k) => { fl.include = f.get(`include-${k}`) === "on"; });
    if (!p.liveWithheld) p.liveUrl = (f.get("liveUrl") || "").toString().trim();
    else p.liveAuthorized = f.get("liveAuthorized") === "on";
    p.access = f.get("access"); p.phone = f.get("phone");
    if (p.provisional) p.rightsReview = f.get("rightsReview") === "on";
  }

  function save() {
    const p = find(editing.id);
    collect(p);
    p.revision += 1;
    if (p.status === "Published") p.status = "Changes since last publish"; // FR3.2
    activity.push({ t: NOW.slice(0, 16), a: "Saved changes", p: p.title || "Untitled" });
    editing.dirty = false;
    editor(p.id);
    document.getElementById("savestate").textContent = `Saved · revision ${p.revision} · the public copy is unchanged`;
    announce(`Saved revision ${p.revision}. Nothing has been published.`);
  }

  function preview(id) {
    const p = find(id);
    if (!p) { projectsView(); return; }
    const pub = toPublic(p);
    const c = p.category && D.cat(p.category);
    main.innerHTML = `
      <div class="preview-banner" role="note">${ic("i-eye")} Preview — not public</div>
      <header class="studio-head">
        <div><a class="back-link" href="#edit/${p.id}">${ic("i-prev")}Back to editor</a><h1>${esc(p.title || "Untitled")}</h1>
        <p class="studio-head__sub">Exactly as visitors would see it after Publish — card, featured slide and category placement (FR6.1).</p></div>
      </header>
      <div class="preview-grid">
        <section class="panel"><h2>Gallery card</h2><ul class="cards cards--1">${S.card(pub)}</ul></section>
        <section class="panel"><h2>Featured carousel</h2>${p.featured
          ? `<div class="mini-slide">${p.images.find((i) => i.lead) ? `<img src="${p.images.find((i) => i.lead).src}" alt="">` : ""}<div><p class="eyebrow">Featured</p><p class="mini-slide__t">${esc(p.title)}</p></div></div><p class="field__hint">Position ${p.featured} of the featured order.</p>`
          : `<p class="field__hint">Not featured — it won't appear in the carousel.</p>`}</section>
        <section class="panel"><h2>Category page</h2>${c ? `<p>Listed under <strong>${esc(c.name)}</strong>.</p>` : `<p class="field__hint">No category — it appears in the gallery only.</p>`}</section>
      </div>
      ${p.id && D.find(p.id) && !D.find(p.id).pending ? `<p><a class="btn btn--ghost" href="project.html?p=${p.id}">${ic("i-external")} Open the full page preview</a></p>` : ""}`;
  }

  function featured() {
    const list = projects.filter((p) => p.featured).sort((a, b) => a.featured - b.featured);
    main.innerHTML = `
      <header class="studio-head">
        <div><h1>Featured order</h1><p class="studio-head__sub">${list.length} of ${FEATURED_MAX} featured · drafts count, but appear only once published (FR9.7)</p></div>
        <div class="studio-head__actions"><button class="btn btn--primary" type="button" data-act="order">Update featured order…</button></div>
      </header>
      <ol class="order" id="order-list">${list.map((p, k) => `
        <li class="order__item">
          <span class="order__n">${k + 1}</span>
          <span class="order__t">${esc(p.title)} ${statusPill(p.status)}</span>
          <span class="order__btns">
            <button class="icon-btn" type="button" data-move="-1" data-id="${p.id}" aria-label="Move ${esc(p.title)} up" ${k === 0 ? "disabled" : ""}>${ic("i-prev")}</button>
            <button class="icon-btn" type="button" data-move="1" data-id="${p.id}" aria-label="Move ${esc(p.title)} down" ${k === list.length - 1 ? "disabled" : ""}>${ic("i-arrow")}</button>
          </span>
        </li>`).join("")}</ol>
      <p class="field__hint">Reordering here is private until you confirm "Update featured order".</p>`;
  }

  function activityView() {
    main.innerHTML = `
      <header class="studio-head"><div><h1>Activity</h1><p class="studio-head__sub">Every publish, update and take-down (FR7.7) · example entries</p></div></header>
      <ol class="activity">${activity.slice().reverse().map((e) => `<li><span class="activity__t">${esc(e.t)}</span> <strong>${esc(e.a)}</strong> · ${esc(e.p)}</li>`).join("")}</ol>`;
  }

  // ------------------------------------------------------- publish (S6)
  function toPublic(p) {
    const src = D.find(p.id);
    return {
      slug: p.id, title: p.title || "Untitled", summary: p.summary, category: p.category, icon: src ? src.icon : "i-hammer",
      provisional: p.provisional && !p.rightsReview, pending: false,
      lead: p.images.find((i) => i.lead) ? { src: p.images.find((i) => i.lead).src, kind: p.images.find((i) => i.lead).kind, alt: "" } : null,
      access: { liveUrl: p.liveWithheld && !p.liveAuthorized ? null : p.liveUrl, liveWithheld: p.liveWithheld && !p.liveAuthorized, requirement: p.access, phone: p.phone },
      repos: p.repos.map((r) => ({ visibility: r.visibility, licence: r.licence })),
    };
  }

  function openPublish(id) {
    const p = find(id);
    if (editing && editing.id === id) collect(p);
    const dlg = document.getElementById("dlg-publish");
    const b = blockers(p);
    const update = isPublic(p);
    const r = !p.liveWithheld || p.liveAuthorized ? reach(p.liveUrl) : null;
    const text = [["Title", p.title], ["Summary", p.summary], ...D.narrativeOrder.map(([k, l]) => [l, p.narrative[k]])].filter(([, v]) => v && v.trim());
    const files = p.files.filter((f) => f.include);
    dlg.innerHTML = `
      <div class="sdialog__body sdialog__body--scroll">
        <h2 id="dlg-publish-h">${update ? "Update the public exhibit" : "Publish"} · ${esc(p.title || "Untitled")}</h2>
        <p class="sdialog__lede">Everything below becomes public exactly as shown — revision ${p.revision}. Edits made after you confirm are not included.</p>
        <div class="inventory" tabindex="0" aria-label="What will become public">
          ${b.length ? `<section class="inv inv--block" id="pub-blockers"><h3>${ic("i-alert")} Before you can publish</h3><ul>${b.map(([t, f]) => `<li><a href="#edit/${p.id}" data-focus="${f}">${esc(t)}</a></li>`).join("")}</ul></section>` : ""}
          <section class="inv"><h3>Text</h3><ul>${text.map(([l, v]) => `<li><strong>${esc(l)}</strong> — ${esc(v.length > 140 ? v.slice(0, 140) + "…" : v)}</li>`).join("") || "<li>None</li>"}</ul>
            <p class="inv__note">AI-originated text: none.</p></section>
          <section class="inv"><h3>Images</h3><ul class="inv__imgs">${p.images.map((im) => `<li><img src="${im.src}" alt=""><span>${im.lead ? "<strong>Lead</strong> · " : ""}${im.alt ? esc(im.alt) : `<em class="inv__bad">No alt text</em>`}</span></li>`).join("") || "<li>None</li>"}</ul></section>
          <section class="inv"><h3>Files</h3>${files.length ? `<ul>${files.map((f) => `<li><strong>${esc(f.name)}</strong> · ${esc(f.type)} · ${esc(f.size)} · published unchanged
              <ul class="inv__meta"><li>Embedded metadata: ${f.meta ? esc(f.meta) : "Metadata could not be read"}</li>${f.entries ? `<li>Contains: ${f.entries.map((e) => /(^\.env$|\.git\/|id_rsa|\.pem$)/.test(e) ? `<span class="inv__bad">${esc(e)} (looks like a secret)</span>` : esc(e)).join(", ")}</li>` : ""}</ul></li>`).join("")}</ul>` : "<p>None included.</p>"}</section>
          <section class="inv"><h3>Links and access</h3><ul>
            ${p.liveWithheld && !p.liveAuthorized ? `<li>${ic("i-lock")} Live URL <strong>not published</strong> — not yet authorized (FR10.7).</li>`
              : p.liveUrl ? `<li>Live app: <code>${esc(p.liveUrl)}</code> (published exactly as entered) — <strong>${esc(r.label)}</strong> ${esc(r.note)}</li>` : "<li>No live app link.</li>"}
            ${p.repos.map((x) => x.visibility === "public" ? `<li>Source: <code>${esc(x.name)}</code> — visibility confirmed public from GitHub at ${esc(x.readAt)} · ${x.licence ? esc(x.licence) : "no licence → \"Source available\""}</li>`
              : `<li>${ic("i-lock")} Private repository — no name or link is published; badge reads "Source private".</li>`).join("")}
            <li>Badges: ${badgesFor(p).map(esc).join(" · ") || "none"}</li></ul></section>
          <section class="inv"><h3>Placement</h3><ul>
            <li>Category: ${p.category ? esc(D.cat(p.category).name) : "none — gallery only"}</li>
            <li>Featured: ${p.featured ? `yes, position ${p.featured}` : "no"}</li></ul></section>
          ${p.repos.some((x) => x.visibility !== "public") ? `<section class="inv inv--warn"><h3>${ic("i-lock")} Private source</h3><p>Only the reviewed text above becomes public. The repository stays private and is never linked (D-15, D-22).</p></section>` : ""}
          ${p.provisional ? `<section class="inv inv--warn"><h3>${ic("i-alert")} Rights review</h3><p>${p.rightsReview ? "Recorded as complete." : "Outstanding — names and artwork must be cleared before publishing (FR10.6)."}</p></section>` : ""}
        </div>
        <div class="sdialog__actions sdialog__actions--sticky">
          <button class="btn btn--ghost" type="button" data-act="close">Cancel</button>
          <button class="btn btn--primary" type="button" data-act="confirm-publish" data-id="${p.id}" ${b.length ? "disabled aria-describedby=\"pub-blockers\"" : ""}>${update ? "Update the public exhibit" : "Publish this revision"}</button>
        </div>
      </div>`;
    dlg.showModal();
    dlg.querySelector('[data-act="close"]').focus();
  }

  function confirmPublish(id) {
    const p = find(id);
    const update = isPublic(p);
    p.status = "Published";
    activity.push({ t: NOW.slice(0, 16), a: update ? "Updated public exhibit" : "Published", p: p.title });
    document.getElementById("dlg-publish").close();
    editing = null;
    location.hash = "#projects";
    announce(`${p.title} ${update ? "updated" : "published"} (simulated). It would be public within 5 minutes.`);
  }

  // ----------------------------------------------------- take-down (S7)
  function openTakedown(id) {
    const p = find(id);
    const dlg = document.getElementById("dlg-takedown");
    dlg.innerHTML = `
      <div class="sdialog__body">
        <h2 id="dlg-takedown-h">Take down ${esc(p.title)}?</h2>
        <ul class="sdialog__list">
          <li>Removes its page, gallery card, images and files from this site and its delivery cache within 5 minutes.</li>
          ${p.featured ? `<li>Removes it from the featured carousel. Its featured slot is released and won't come back automatically.</li>` : ""}
          ${p.category ? `<li>Removes it from ${esc(D.cat(p.category).name)}. If that leaves the category empty, the category is hidden.</li>` : ""}
          <li>Keeps everything in the Studio, so you can publish it again later.</li>
          <li>Can't withdraw copies already downloaded, or held in other caches, search engines or archives (FR8.4).</li>
        </ul>
        <div class="sdialog__actions">
          <button class="btn btn--ghost" type="button" data-act="close">Cancel</button>
          <button class="btn btn--danger" type="button" data-act="confirm-takedown" data-id="${p.id}">Take down ${esc(p.title)}</button>
        </div>
      </div>`;
    dlg.showModal();
    dlg.querySelector('[data-act="close"]').focus();
  }

  function confirmTakedown(id) {
    const p = find(id);
    p.status = "Taken down";
    p.featured = 0; // FR8.2: slot released
    activity.push({ t: NOW.slice(0, 16), a: "Taken down", p: p.title });
    document.getElementById("dlg-takedown").close();
    projectsView();
    announce(`${p.title} taken down (simulated). Studio content kept.`);
  }

  // ------------------------------------------------ featured order (S8)
  function openOrder() {
    const list = projects.filter((p) => p.featured).sort((a, b) => a.featured - b.featured);
    const pub = list.filter((p) => isPublic(p));
    const dlg = document.getElementById("dlg-order");
    dlg.innerHTML = `
      <div class="sdialog__body">
        <h2 id="dlg-order-h">Update featured order</h2>
        <p class="sdialog__lede">The home page carousel will show, in this order:</p>
        <ol class="sdialog__list">${pub.map((p) => `<li>${esc(p.title)}</li>`).join("") || "<li>Nothing — the carousel is hidden.</li>"}</ol>
        ${list.length > pub.length ? `<p class="field__hint">Not shown until published: ${list.filter((p) => !isPublic(p)).map((p) => esc(p.title)).join(", ")}.</p>` : ""}
        <div class="sdialog__actions">
          <button class="btn btn--ghost" type="button" data-act="close">Cancel</button>
          <button class="btn btn--primary" type="button" data-act="confirm-order">Update featured order</button>
        </div>
      </div>`;
    dlg.showModal();
    dlg.querySelector('[data-act="close"]').focus();
  }

  // ------------------------------------------------------------- events
  document.addEventListener("click", (e) => {
    if (e.target.closest(".skip")) { e.preventDefault(); main.focus(); return; } // hash routing: don't navigate
    const t = e.target.closest("[data-act], [data-move], [data-focus]");
    if (!t) return;
    const act = t.dataset.act;
    if (t.dataset.focus) {
      e.preventDefault();
      t.closest("dialog").close();
      const el = document.getElementById(t.dataset.focus);
      if (el) { (el.matches("input,select,textarea") ? el : el.querySelector("input,select,textarea") || el).focus(); }
      return;
    }
    if (t.dataset.move) {
      const list = projects.filter((p) => p.featured).sort((a, b) => a.featured - b.featured);
      const i = list.findIndex((p) => p.id === t.dataset.id), j = i + Number(t.dataset.move);
      [list[i].featured, list[j].featured] = [list[j].featured, list[i].featured];
      featured();
      document.querySelector(`[data-id="${t.dataset.id}"][data-move="${t.dataset.move}"]`)?.focus();
      announce("Order changed privately. Confirm Update featured order to publish it.");
      return;
    }
    if (act === "new") {
      const dlg = document.getElementById("dlg-new");
      document.getElementById("new-category").innerHTML = catOptions("");
      document.getElementById("new-title").value = t.dataset.repo && t.dataset.repo !== "private" ? t.dataset.repo : "";
      dlg.dataset.repo = t.dataset.repo || "";
      document.getElementById("new-error").hidden = true;
      dlg.showModal();
      document.getElementById("new-title").focus();
    }
    if (act === "save") save();
    if (act === "publish") openPublish(t.dataset.id);
    if (act === "confirm-publish") confirmPublish(t.dataset.id);
    if (act === "takedown") openTakedown(t.dataset.id);
    if (act === "confirm-takedown") confirmTakedown(t.dataset.id);
    if (act === "order") openOrder();
    if (act === "confirm-order") {
      activity.push({ t: NOW.slice(0, 16), a: "Updated featured order", p: "Home page" });
      document.getElementById("dlg-order").close();
      announce("Featured order updated (simulated).");
    }
    if (act === "close") t.closest("dialog").close();
    if (act === "add-file" && editing) {
      const p = find(editing.id);
      collect(p);
      p.files.push({ name: "hall-table-plan.vsdx", type: "VSDX", size: "1.2 MB", state: "checking", include: true,
        meta: "Creator “M. Broadfoot”; application Microsoft Visio", entries: ["[Content_Types].xml", "visio/document.xml", "visio/pages/page1.xml", "docProps/core.xml"] });
      document.getElementById("file-list").innerHTML = filesHtml(p);
      editing.dirty = true;
      document.getElementById("savestate").textContent = "Unsaved changes · the public copy is unchanged";
      setTimeout(() => { p.files.forEach((f) => { f.state = "accepted"; }); const fl = document.getElementById("file-list"); if (fl) fl.innerHTML = filesHtml(p); announce("hall-table-plan.vsdx accepted."); }, 900);
    }
    if (act === "add-image") announce("In the product this opens the file picker. Uploads go straight to private storage and are checked before use.");
  });

  document.getElementById("form-new").addEventListener("submit", (e) => {
    const dlg = document.getElementById("dlg-new");
    if (e.submitter && e.submitter.value === "cancel") return;
    const title = document.getElementById("new-title").value.trim();
    if (!title) { e.preventDefault(); document.getElementById("new-error").hidden = false; document.getElementById("new-title").focus(); return; }
    const repo = dlg.dataset.repo;
    const id = "new-" + Date.now().toString(36);
    projects.push({
      id, title, summary: "", category: document.getElementById("new-category").value || null, featured: 0, status: "Draft",
      provisional: false, rightsReview: true, liveWithheld: false, liveAuthorized: true, liveUrl: "", access: "open", phone: "unknown",
      repos: repo && repo !== "private" ? [{ name: repo, visibility: "public", licence: null, url: null, readAt: NOW }] : repo === "private" ? [{ name: null, visibility: "private", licence: null }] : [],
      narrative: { inspiration: "", challenges: "", decisions: "", implementation: "", outcomes: "", lessons: "" },
      images: [], files: [], revision: 1, updated: "2026-10-10",
    });
    activity.push({ t: NOW.slice(0, 16), a: "Created draft", p: title });
    setTimeout(() => { location.hash = `#edit/${id}`; announce(`Draft “${title}” created. Nothing is public.`); }, 0);
  });

  document.getElementById("leave-stay").addEventListener("click", () => { document.getElementById("dlg-leave").close(); pendingHash = null; });
  document.getElementById("leave-discard").addEventListener("click", () => {
    document.getElementById("dlg-leave").close();
    editing = null;
    if (pendingHash) { location.hash = "#" + pendingHash; pendingHash = null; }
  });

  // Scope-notes toggle (shared prototype aid)
  const toggle = document.querySelector(".notes-toggle");
  const setNotes = (on) => { document.body.classList.toggle("notes-on", on); toggle.setAttribute("aria-pressed", String(on)); toggle.textContent = on ? "Hide scope notes" : "Show scope notes"; };
  toggle.addEventListener("click", () => setNotes(!document.body.classList.contains("notes-on")));
  if (new URLSearchParams(location.search).has("notes")) setNotes(true);

  window.addEventListener("hashchange", route);
  route();
  window.StudioProto = { openPublish, openTakedown, openOrder, find }; // used by the screenshot/test script
})();
