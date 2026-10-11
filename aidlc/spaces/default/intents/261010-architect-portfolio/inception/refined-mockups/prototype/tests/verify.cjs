// Refined Mockups R5 — verification suite and screenshot capture.
//
// Usage (from this folder's parent, i.e. prototype/):
//   PW=<path to playwright package> AXE=<path to axe-core/axe.min.js> node tests/verify.cjs
// Serves the prototype over a local HTTP server on 127.0.0.1 (no file:// quirks; axe can preload
// stylesheets), writes screenshots to ../screenshots/r5-revision/ and results to tests/results.json.
// Every check reports PASS or FAIL with evidence; nothing is assumed.
const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require(process.env.PW || "playwright");

const ROOT = path.resolve(__dirname, "..");
const SHOTS = path.resolve(ROOT, "..", "screenshots", "r5-revision");
const AXE = fs.readFileSync(process.env.AXE, "utf8");
fs.mkdirSync(SHOTS, { recursive: true });
// Always rebuild the simulated public export from the approval model before testing it.
require("child_process").execFileSync(process.execPath, [path.join(ROOT, "tools", "build-export.cjs")], { stdio: "inherit" });
const EXPORT = path.join(ROOT, "export");
// Identifiers of unapproved candidates: names, slugs, live hosts and their assets. None may
// appear anywhere in the export payload — not merely be hidden in the DOM.
const FORBIDDEN = [/monopoly/i, /\brisk\b/i, /arena\.xaminisalamini/i, /dice-hero/i, /pending approval/i, /cat-wood|cat-code/i];

const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".jpg": "image/jpeg", ".png": "image/png", ".woff2": "font/woff2", ".txt": "text/plain", ".json": "application/json" };
const server = http.createServer((req, res) => {
  const rel = decodeURIComponent(new URL(req.url, "http://x").pathname).replace(/^\/+/, "");
  const file = path.resolve(ROOT, rel || "index.html");
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": MIME[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
});
let ORIGIN = "";
const url = (page) => ORIGIN + "/" + page;
const results = [];
const check = (id, name, pass, evidence) => { results.push({ id, name, pass: !!pass, evidence }); console.log(`${pass ? "PASS" : "FAIL"}  ${id}  ${name}${pass ? "" : "  — " + JSON.stringify(evidence)}`); };

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };

(async () => {
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  ORIGIN = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();

  async function open(page, vp = DESKTOP, opts = {}) {
    const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: vp.width < 500 ? 2 : 1, reducedMotion: opts.reducedMotion || "no-preference" });
    const p = await ctx.newPage();
    const errors = [], external = [];
    p.on("console", (m) => m.type() === "error" && errors.push(m.text().slice(0, 160)));
    p.on("pageerror", (e) => errors.push("pageerror: " + e.message.slice(0, 160)));
    p.on("request", (r) => { const u = r.url(); if (!u.startsWith(ORIGIN) && !/^(data|blob):/.test(u)) external.push(u); });
    await p.goto(url(page), { waitUntil: "load" });
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(350);
    return { ctx, p, errors, external };
  }
  // Full-page captures start from the top so sticky bars render where they belong.
  const shot = async (p, name, full = false) => { if (full) { await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(100); } return p.screenshot({ path: path.join(SHOTS, name + ".png"), fullPage: full }); };
  const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  async function axe(p) {
    await p.addScriptTag({ content: AXE });
    const r = await p.evaluate(async () => (await window.axe.run(document, { resultTypes: ["violations"] })).violations
      .filter((v) => v.impact === "serious" || v.impact === "critical")
      .map((v) => `${v.id} (${v.impact}): ${v.nodes.length} node(s) e.g. ${v.nodes[0].target.join(" ")}`));
    return r;
  }

  // ---------------------------------------------------------------- public pages
  const publicPages = [
    ["home", "index.html"], ["catalog", "catalog.html"], ["category-games", "catalog.html?category=games"],
    ["project-stars", "project.html?p=stars"], ["project-baduk", "project.html?p=baduk"],
    ["project-monopoly", "project.html?p=monopoly-arena"], ["not-on-display", "project.html?p=risk"],
    // simulated public export (approved-publication snapshot only)
    ["export-home", "export/index.html"], ["export-catalog", "export/catalog.html"], ["export-category-games", "export/catalog.html?category=games"],
    ["export-project-stars", "export/project.html?p=stars"], ["export-project-baduk", "export/project.html?p=baduk"],
    ["export-route-monopoly", "export/project.html?p=monopoly-arena"], ["export-route-risk", "export/project.html?p=risk"],
  ];
  for (const [name, page] of publicPages) {
    for (const [vpName, vp] of [["1440", DESKTOP], ["1024", { width: 1024, height: 900 }], ["768", { width: 768, height: 1024 }], ["390", PHONE]]) {
      const { ctx, p, errors, external } = await open(page, vp);
      const ov = await overflow(p);
      check(`R-${name}-${vpName}`, `${page} at ${vpName}px: no horizontal overflow, no console errors`, ov <= 0 && !errors.length, { overflowPx: ov, errors: [...errors] });
      if (vpName === "1440") {
        check(`P-${name}`, `${page}: requests nothing from a third-party origin (FR9.5)`, external.length === 0, [...external]);
        const before = errors.length;
        const v = await axe(p);
        check(`A-${name}`, `${page}: axe — no serious or critical violations, and the axe run logs no console errors`, v.length === 0 && errors.length === before, { violations: v, consoleErrorsDuringAxe: errors.slice(before) });
        if (name !== "export-route-risk") await shot(p, `${name}-desktop`, name !== "home"); // identical to the Monopoly route by design
        if (name === "home") await shot(p, "home-desktop-full", true);
      }
      if (vpName === "390" && name !== "export-route-risk") await shot(p, `${name}-mobile`, true);
      await ctx.close();
    }
  }

  // home: viewport-only mobile shot (first screen)
  { const { ctx, p } = await open("index.html", PHONE); await shot(p, "home-mobile-first-screen"); await ctx.close(); }

  // scope-notes overlay
  { const { ctx, p } = await open("index.html?notes", DESKTOP); await shot(p, "home-scope-notes", true); await ctx.close(); }

  // ---------------------------------------------------------------- keyboard & motion
  {
    const { ctx, p } = await open("index.html", DESKTOP);
    await p.keyboard.press("Tab");
    const first = await p.evaluate(() => document.activeElement.className + "|" + document.activeElement.textContent.trim());
    check("K-skip", "First Tab lands on 'Skip to content' (WCAG 2.4.1)", first.startsWith("skip|Skip to content"), first);
    await p.keyboard.press("Enter");
    const afterSkip = await p.evaluate(() => document.activeElement.id);
    check("K-skip-target", "Activating the skip link moves focus to main content", afterSkip === "main", afterSkip);

    // focus visibility on a sample of controls
    const vis = await p.evaluate(() => {
      const out = [];
      for (const sel of [".btn--primary", ".round-btn", ".side-nav a", ".chip, .link-more", ".notes-toggle"]) {
        const el = document.querySelector(sel); if (!el) continue;
        el.focus({ focusVisible: true });
        const cs = getComputedStyle(el);
        out.push({ sel, outline: cs.outlineStyle + " " + cs.outlineWidth });
      }
      return out;
    });
    await p.keyboard.press("Tab"); // ensure :focus-visible heuristics engage via keyboard
    const kbFocus = await p.evaluate(() => { const cs = getComputedStyle(document.activeElement); return cs.outlineStyle + " " + cs.outlineWidth; });
    check("K-focus-visible", "Keyboard focus shows a visible outline", !kbFocus.startsWith("none") && kbFocus !== "", { keyboardFocused: kbFocus, sample: vis });

    // carousel: arrow key advances, nothing auto-advances
    const idx0 = await p.textContent(".hero__index");
    await p.waitForTimeout(6000);
    const idxIdle = await p.textContent(".hero__index");
    check("C-no-autoplay", "Carousel does not advance on its own after 6 s (FR9.7, WCAG 2.2.2)", idx0 === idxIdle, { before: idx0, after: idxIdle });
    await p.focus('.round-btn[data-dir="1"]');
    await p.keyboard.press("Enter"); await p.waitForTimeout(400);
    const idx1 = await p.textContent(".hero__index");
    await p.keyboard.press("ArrowRight"); await p.waitForTimeout(400);
    const idx2 = await p.textContent(".hero__index");
    const live = await p.getAttribute(".hero__copy", "aria-live");
    check("C-keyboard", "Carousel next control and ArrowRight advance it; slide copy is announced politely", idx1 === "02" && idx2 === "03" && live === "polite", { idx1, idx2, live });
    const viewHref = await p.getAttribute(".hero__view", "href");
    check("C-links", "Featured slide links to its project page", viewHref === "project.html?p=monopoly-arena", viewHref);
    await shot(p, "home-desktop-slide3");
    await ctx.close();
  }
  {
    const { ctx, p } = await open("index.html", DESKTOP, { reducedMotion: "reduce" });
    const d = await p.evaluate(() => getComputedStyle(document.querySelector(".hero__img")).transitionDuration);
    check("M-reduced-motion", "Reduced motion removes the carousel transition", /^0s/.test(d), d);
    await ctx.close();
  }

  // ---------------------------------------------------------------- category & 404 rules
  {
    const { ctx, p } = await open("catalog.html?category=woodworking", DESKTOP);
    const h = await p.textContent("h1");
    check("F-empty-category", "A category with no published exhibit is not on display (FR9.8)", /isn't on display/.test(h), h);
    await shot(p, "category-empty-not-on-display");
    await ctx.close();
  }
  {
    const { ctx, p } = await open("catalog.html?category=games", DESKTOP);
    const chips = await p.$$eval(".chip", (els) => els.map((e) => e.textContent.replace(/\s+/g, " ").trim()));
    const n = await p.textContent("#catalog-count");
    check("F-counts", "Category counts include published exhibits only (FR9.1)", chips.includes("Games & AI Arenas 2") && /2 published/.test(n), { chips, n });
    const riskLink = await p.$$eval(".card--pending a", (as) => as.length);
    check("F-risk-nolink", "Unapproved Risk card has no link and no live URL", riskLink === 0, riskLink);
    await ctx.close();
  }
  {
    const { ctx, p } = await open("index.html", DESKTOP);
    const tiles = await p.$$eval(".types .type__title", (els) => els.map((e) => e.textContent));
    check("F-home-categories", "Home shows only populated categories (FR9.1)", tiles.length === 2 && !tiles.includes("Woodworking"), tiles);
    await ctx.close();
  }

  // project actions stay visible on phones
  {
    const { ctx, p } = await open("project.html?p=stars", PHONE);
    const src = await p.isVisible('a.btn:has-text("View source")');
    const app = await p.isVisible('a.btn:has-text("Open the app")');
    check("F-mobile-actions", "Project page on a phone shows both Open the app and View source", src && app, { src, app });
    await ctx.close();
  }

  // ---------------------------------------------------------------- approved-publication export
  {
    // 1. Static payload: every file shipped in export/ (FR7.1, FR10.1, FR10.6, FR10.7, NFR2).
    const files = [];
    const walk = (d) => { for (const f of fs.readdirSync(d)) { const full = path.join(d, f); fs.statSync(full).isDirectory() ? walk(full) : files.push(full); } };
    walk(EXPORT);
    const textual = files.filter((f) => /\.(html|js|css|json|txt)$/.test(f));
    const hits = [];
    for (const f of textual) { const t = fs.readFileSync(f, "utf8"); for (const re of FORBIDDEN) if (re.test(t)) hits.push(`${path.relative(EXPORT, f)}: ${re}`); }
    for (const f of files) for (const re of FORBIDDEN) if (re.test(path.relative(EXPORT, f))) hits.push(`file name ${path.relative(EXPORT, f)}`);
    check("X-payload", `Export payload (${files.length} files) contains no identifier of an unapproved candidate — Monopoly or Risk names, slugs, live hosts or assets`, hits.length === 0, hits);

    // 2. Snapshot schema: allow-listed fields only (FR4.10).
    const sandbox = { window: {} }; require("vm").createContext(sandbox);
    require("vm").runInContext(fs.readFileSync(path.join(EXPORT, "publication.js"), "utf8"), sandbox);
    const X = sandbox.window.PORTFOLIO;
    const allowed = new Set(["slug", "title", "category", "icon", "featured", "meta", "summary", "lead", "gallery", "narrative", "files", "badges", "access", "repos"]);
    const extra = X.projects.flatMap((q) => Object.keys(q).filter((k) => !allowed.has(k)).map((k) => `${q.slug}.${k}`));
    const accessExtra = X.projects.flatMap((q) => Object.keys(q.access).filter((k) => k !== "liveUrl").map((k) => `${q.slug}.access.${k}`));
    const privateRepos = X.projects.flatMap((q) => q.repos.filter((r) => r.visibility !== "public").map(() => q.slug));
    check("X-schema", "Snapshot holds only approved projects with allow-listed fields: no publication state, access internals or private repositories (FR4.10)",
      X.mode === "export" && X.projects.map((q) => q.slug).join() === "stars,baduk" && !extra.length && !accessExtra.length && !privateRepos.length,
      { projects: X.projects.map((q) => q.slug), extra, accessExtra, privateRepos });

    // 3. Assets: exactly the assets the approved projects use; no concept or unapproved art.
    const assetFiles = files.filter((f) => f.includes(`${path.sep}assets${path.sep}`)).map((f) => path.relative(EXPORT, f).split(path.sep).join("/")).sort();
    const referenced = [...new Set([...X.projects.flatMap((q) => [q.lead.src, ...q.gallery.map((g) => g.src)]), ...X.categories.map((c) => c.image.src)])].sort();
    check("X-assets", "Export ships exactly the assets its approved projects reference, and no draft or unapproved art", JSON.stringify(assetFiles) === JSON.stringify(referenced) && !assetFiles.some((a) => a.startsWith("assets/draft/")), { assetFiles, referenced });

    // 4. Runtime: rendered DOM and in-memory data on every export route, including direct routes.
    const routes = ["export/index.html", "export/catalog.html", "export/catalog.html?category=games", "export/catalog.html?category=astronomy",
      "export/project.html?p=stars", "export/project.html?p=baduk", "export/project.html?p=monopoly-arena", "export/project.html?p=risk"];
    for (const page of routes) {
      const { ctx, p } = await open(page, DESKTOP);
      const requests = [];
      p.on("request", (r) => requests.push(r.url()));
      await p.reload({ waitUntil: "load" }); await p.waitForTimeout(250);
      const html = await p.content();
      const data = await p.evaluate(() => JSON.stringify(window.PORTFOLIO));
      const leaks = FORBIDDEN.filter((re) => re.test(html) || re.test(data)).map(String);
      const outside = requests.filter((u) => !u.startsWith(`${ORIGIN}/export/`));
      const id = page.replace("export/", "").replace(/\.html/, "").replace(/[?=&]/g, "-");
      check(`X-route-${id}`, `${page}: no unapproved data in the rendered page or the loaded data, and every request stays inside export/`, !leaks.length && !outside.length, { leaks, outside });
      if (/monopoly-arena|risk/.test(page)) {
        const h = await p.textContent("h1");
        check(`X-direct-${id}`, `${page}: a direct route to an unapproved candidate shows "isn't on display" (FR9.3)`, /isn't on display/.test(h), h);
      }
      await ctx.close();
    }

    // 5. Featured, categories and counts derive from the snapshot.
    {
      const { ctx, p } = await open("export/index.html", DESKTOP);
      const total = await p.textContent(".hero__total");
      const dots = await p.$$eval(".hero__dots button", (b) => b.length);
      const seen = [await p.textContent(".hero__title")];
      for (let k = 0; k < 2; k++) { await p.click('.round-btn[data-dir="1"]'); await p.waitForTimeout(400); seen.push((await p.textContent(".hero__title")).trim()); }
      const tiles = await p.$$eval(".type", (els) => els.map((e) => e.querySelector(".type__title").textContent + " " + e.querySelector(".type__count").textContent));
      const cards = await p.$$eval("#work-cards .card h3", (els) => els.map((e) => e.textContent.trim()));
      check("X-derived-home", "Export home: carousel, category tiles, counts and gallery come only from approved projects (STARS, Baduk)",
        total === "02" && dots === 2 && seen.join("|").replace(/\s+/g, " ") === "STARS|Baduk|STARS" &&
        JSON.stringify(tiles) === JSON.stringify(["Games & AI Arenas 1 project", "Astronomy & Exploration 1 project"]) && JSON.stringify(cards) === JSON.stringify(["STARS", "Baduk"]),
        { total, dots, seen, tiles, cards });
      await ctx.close();
    }
    {
      const { ctx, p } = await open("export/catalog.html?category=games", DESKTOP);
      const chips = await p.$$eval(".chip", (els) => els.map((e) => e.textContent.replace(/\s+/g, " ").trim()));
      const cards = await p.$$eval(".card h3", (els) => els.map((e) => e.textContent.trim()));
      check("X-derived-catalog", "Export catalog and category page list and count only approved projects", JSON.stringify(chips) === JSON.stringify(["All 2", "Games & AI Arenas 1", "Astronomy & Exploration 1"]) && JSON.stringify(cards) === JSON.stringify(["Baduk"]), { chips, cards });
      await shot(p, "export-category-games-desktop", true);
      await ctx.close();
    }
  }

  // ---------------------------------------------------------------- email (FR9.4)
  for (const page of ["index.html", "catalog.html", "project.html?p=stars", "project.html?p=risk", "export/index.html", "export/catalog.html", "export/project.html?p=stars", "export/project.html?p=monopoly-arena"]) {
    const { ctx, p } = await open(page, DESKTOP);
    const footers = await p.$$eval("footer.site-foot", (f) => f.length);
    const github = await p.$$eval('.site-foot a[href="https://github.com/mbroadfo"]', (a) => a.length);
    check(`E-footer-${page.replace(/[/?=.]/g, "-")}`, `${page}: footer present once with the GitHub link and copyright (FR9.4)`, footers === 1 && github === 1, { footers, github });
    const fake = await p.$$eval('a[href="#contact"]', (a) => a.length);
    const mailto = await p.$$eval('.site-foot a[href^="mailto:"]', (a) => a.length);
    const pendingInput = await p.$$eval(".site-foot .owner-input", (e) => e.map((x) => x.textContent.trim()));
    check(`E-email-${page.replace(/[/?=.]/g, "-")}`, `${page}: no fake Email link — a real mailto: link, or the owner-content dependency shown as text`, fake === 0 && (mailto > 0 || pendingInput.some((t) => /Email address to come/.test(t))), { fake, mailto, pendingInput });
    await ctx.close();
  }

  // ---------------------------------------------------------------- lightbox
  {
    const { ctx, p } = await open("project.html?p=stars", DESKTOP);
    await p.focus(".gallery__btn");
    await p.keyboard.press("Enter"); await p.waitForTimeout(300);
    const openNow = await p.evaluate(() => document.getElementById("lightbox").open);
    await p.keyboard.press("ArrowRight"); await p.waitForTimeout(200);
    const count = await p.textContent("#lightbox-count");
    await shot(p, "project-stars-lightbox");
    await p.keyboard.press("Escape"); await p.waitForTimeout(200);
    const back = await p.evaluate(() => document.activeElement.classList.contains("gallery__btn"));
    check("D-lightbox", "Gallery opens an enlarged view by keyboard, arrows step, Escape closes and focus returns (FR9.2)", openNow && count === "2 / 3" && back, { openNow, count, back });
    await ctx.close();
  }

  // ---------------------------------------------------------------- Studio
  const studioViews = [["studio-signin", "studio.html#signin"], ["studio-private", "studio.html#private"], ["studio-projects", "studio.html#projects"],
    ["studio-empty", "studio.html#projects/empty"], ["studio-discover", "studio.html#discover"], ["studio-editor-stars", "studio.html#edit/stars"],
    ["studio-editor-risk", "studio.html#edit/risk"], ["studio-preview-baduk", "studio.html#preview/baduk"], ["studio-featured", "studio.html#featured"], ["studio-activity", "studio.html#activity"]];
  for (const [name, page] of studioViews) {
    for (const [vpName, vp] of [["1440", DESKTOP], ["390", PHONE]]) {
      const { ctx, p, errors, external } = await open(page, vp);
      const ov = await overflow(p);
      check(`R-${name}-${vpName}`, `${page} at ${vpName}px: no horizontal overflow, no console errors`, ov <= 0 && !errors.length, { overflowPx: ov, errors: [...errors] });
      if (vpName === "1440") {
        check(`P-${name}`, `${page}: no third-party requests`, external.length === 0, [...external]);
        const before = errors.length;
        const v = await axe(p);
        check(`A-${name}`, `${page}: axe — no serious or critical violations, and the axe run logs no console errors`, v.length === 0 && errors.length === before, { violations: v, consoleErrorsDuringAxe: errors.slice(before) });
      }
      await shot(p, `${name}-${vpName === "1440" ? "desktop" : "mobile"}`, true);
      await ctx.close();
    }
  }

  // title-only project (CR-02)
  {
    const { ctx, p } = await open("studio.html#projects", DESKTOP);
    await p.click('button[data-act="new"]');
    await p.waitForTimeout(150);
    const focused = await p.evaluate(() => document.activeElement.id);
    await shot(p, "studio-new-project-dialog");
    await p.click('#form-new button[value="create"]');
    const err = await p.isVisible("#new-error");
    await p.fill("#new-title", "Hall table");
    await p.selectOption("#new-category", "woodworking");
    await p.click('#form-new button[value="create"]');
    await p.waitForTimeout(300);
    const hash = await p.evaluate(() => location.hash);
    const ai = await p.textContent("#ai-panel");
    const status = await p.textContent(".studio-head__sub .status");
    check("S-title-only", "A project can be created with only a title; it starts as Draft with no repository, and the AI panel says suggestions need a repository (FR3.1, FR5.1)",
      focused === "new-title" && err && hash.startsWith("#edit/new-") && /need a linked repository/.test(ai) && status === "Draft", { focused, emptyTitleError: err, hash, status });
    const cardText = await p.textContent("#editor-form ~ .editor__aside .card");
    check("S-placeholder", "A title-only project's card says it needs a lead image, and never claims a private source it doesn't have", /No lead image yet/.test(cardText) && !/Source is private/.test(cardText), cardText.replace(/\s+/g, " ").trim().slice(0, 160));
    await p.click('button[data-act="add-file"]'); await p.waitForTimeout(1100);
    await shot(p, "studio-editor-title-only", true);
    await p.click('button[data-act="publish"]'); await p.waitForTimeout(250);
    const blk = await p.$$eval("#pub-blockers li", (l) => l.map((x) => x.textContent));
    const disabled = await p.isDisabled('[data-act="confirm-publish"]');
    const initial = await p.evaluate(() => document.activeElement.textContent.trim());
    await shot(p, "studio-publish-blocked-title-only");
    check("S-publish-blocked", "Publish is blocked with linked reasons when there's no lead image; initial focus is Cancel (FR7.3)", disabled && blk.some((b) => /lead image/.test(b)) && initial === "Cancel", { blk, disabled, initial });
    const meta = await p.textContent("#dlg-publish");
    check("S-file-inventory", "Publish confirmation lists attachment metadata and ZIP entries, published unchanged (FR7.2)", /Embedded metadata/.test(meta) && /Contains: \[Content_Types\]\.xml/.test(meta) && /published unchanged/.test(meta), "inventory text checked");
    await p.keyboard.press("Escape"); await p.waitForTimeout(200);
    const closed = await p.evaluate(() => !document.getElementById("dlg-publish").open);
    check("S-escape", "Escape cancels the confirmation", closed, closed);
    // leave guard
    await p.fill('textarea[name="summary"]', "A walnut hall table.");
    await p.evaluate(() => { location.hash = "#projects"; }); await p.waitForTimeout(250);
    const guard = await p.evaluate(() => document.getElementById("dlg-leave").open);
    const stay = await p.evaluate(() => document.activeElement.id);
    await shot(p, "studio-leave-guard");
    check("S-leave-guard", "Leaving with unsaved changes asks first, Stay focused (FR4.6)", guard && stay === "leave-stay", { guard, stay });
    await ctx.close();
  }

  // rights review blocks Monopoly (FR10.6)
  {
    const { ctx, p } = await open("studio.html#edit/monopoly-arena", DESKTOP);
    await p.click('button[data-act="publish"]'); await p.waitForTimeout(250);
    const blk = await p.$$eval("#pub-blockers li", (l) => l.map((x) => x.textContent));
    check("S-rights-block", "Monopoly cannot be published while the rights review is outstanding (FR10.6)", blk.some((b) => /rights review/.test(b)), blk);
    await shot(p, "studio-publish-blocked-rights-review");
    await ctx.close();
  }

  // Risk: live URL withheld (FR10.7)
  {
    const { ctx, p } = await open("studio.html#edit/risk", DESKTOP);
    await p.click('button[data-act="publish"]'); await p.waitForTimeout(250);
    const t = await p.textContent("#dlg-publish");
    check("S-risk-url", "Risk's live URL is excluded until authorized; the private repository is never named (FR10.7)", /not published/.test(t) && /no name or link is published/.test(t) && !/https?:\/\/(?!github)/.test(t.replace(/https:\/\/github\.com/g, "")), "inventory text checked");
    await shot(p, "studio-publish-risk-withheld");
    await ctx.close();
  }

  // ready publication with reachability label (FR10.5)
  {
    const { ctx, p } = await open("studio.html#edit/baduk", DESKTOP);
    await p.click('button[data-act="publish"]'); await p.waitForTimeout(250);
    const t = await p.textContent("#dlg-publish");
    const disabled = await p.isDisabled('[data-act="confirm-publish"]');
    check("S-reachable", "Ready update shows 'Reachable', never 'Verified', 'Safe' or 'Approved' (FR10.5)", !disabled && /Reachable/.test(t) && !/\b(Verified|Safe|Approved)\b/.test(t), { disabled });
    await shot(p, "studio-publish-ready-baduk");
    await p.click('[data-act="confirm-publish"]'); await p.waitForTimeout(300);
    const row = await p.textContent(".ptable");
    check("S-published", "Confirming moves Changes since last publish to Published (FR3.2)", /Baduk[\s\S]*Published/.test(row), "table text checked");
    await ctx.close();
  }

  // take-down (FR8)
  {
    const { ctx, p } = await open("studio.html#projects", DESKTOP);
    await p.click('button[data-act="takedown"][data-id="stars"]'); await p.waitForTimeout(250);
    const t = await p.textContent("#dlg-takedown");
    await shot(p, "studio-takedown-dialog");
    await p.click('[data-act="confirm-takedown"]'); await p.waitForTimeout(250);
    const row = await p.textContent(".ptable");
    check("S-takedown", "Take-down names the exhibit, covers the carousel and category, warns about outside copies, and releases the featured slot (FR8.2, FR8.4)",
      /Take down STARS/.test(t) && /featured carousel/.test(t) && /can't withdraw copies/i.test(t) && /STARS[\s\S]*Taken down/.test(row), "dialog and table text checked");
    await ctx.close();
  }

  // featured order private until confirmed (FR9.7)
  {
    const { ctx, p } = await open("studio.html#featured", DESKTOP);
    await p.click('[data-move="1"][data-id="stars"]'); await p.waitForTimeout(150);
    const first = await p.textContent(".order__item .order__t");
    await p.click('[data-act="order"]'); await p.waitForTimeout(200);
    const t = await p.textContent("#dlg-order");
    await shot(p, "studio-featured-order-confirm");
    check("S-order", "Reordering is private until 'Update featured order' lists the new public order; drafts are shown as not yet public (FR9.7)",
      /Baduk/.test(first) && /Update featured order/.test(t) && /Not shown until published: Monopoly Arena/.test(t), { first });
    await ctx.close();
  }

  // ---------------------------------------------------------------- contrast of token pairs (FR9.6, NFR8)
  {
    const { ctx, p } = await open("index.html", DESKTOP);
    const pairs = await p.evaluate(() => {
      const cs = getComputedStyle(document.documentElement);
      const v = (n) => cs.getPropertyValue(n).trim();
      const rgb = (hex) => hex.replace("#", "").match(/../g).map((h) => parseInt(h, 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
      const L = (hex) => { const [r, g, b] = rgb(hex); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
      const ratio = (a, b) => { const [x, y] = [L(v(a)), L(v(b))].sort((m, n) => n - m); return +((x + 0.05) / (y + 0.05)).toFixed(2); };
      const out = [];
      for (const fg of ["--text", "--text-2", "--muted", "--brass", "--brass-hi"]) for (const bg of ["--bg", "--bg-2", "--panel", "--panel-2"]) out.push([fg, bg, ratio(fg, bg)]);
      out.push(["--brass-ink", "--brass", ratio("--brass-ink", "--brass")], ["--brass-ink", "--brass-hi", ratio("--brass-ink", "--brass-hi")]);
      return out;
    });
    const low = pairs.filter(([, , r]) => r < 4.5);
    check("T-contrast", "Every text/background token pair is at least 4.5:1 (FR9.6, NFR8)", low.length === 0, { low, pairs });
    const nontext = await p.evaluate(() => {
      const cs = getComputedStyle(document.documentElement);
      const v = (n) => cs.getPropertyValue(n).trim();
      const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
      const L = (hex) => { const [r, g, b] = hex.replace("#", "").match(/../g).map((h) => lin(parseInt(h, 16) / 255)); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
      const ratio = (a, b) => { const [x, y] = [L(v(a)), L(v(b))].sort((m, n) => n - m); return +((x + 0.05) / (y + 0.05)).toFixed(2); };
      const out = [];
      for (const fg of ["--control-border", "--brass-hi"]) for (const bg of ["--bg", "--bg-2", "--panel", "--panel-2"]) out.push([fg, bg, ratio(fg, bg)]);
      return out;
    });
    const lowNT = nontext.filter(([, , r]) => r < 3);
    check("T-nontext", "Control borders and the focus ring are at least 3:1 against every surface (WCAG 1.4.11)", lowNT.length === 0, { low: lowNT, pairs: nontext });
    await ctx.close();
  }

  await browser.close();
  server.close();
  const passed = results.filter((r) => r.pass).length;
  fs.writeFileSync(path.join(__dirname, "results.json"), JSON.stringify({ run: new Date().toISOString(), passed, total: results.length, results }, null, 2));
  console.log(`\n${passed}/${results.length} checks passed`);
  process.exitCode = passed === results.length ? 0 : 1;
})();
