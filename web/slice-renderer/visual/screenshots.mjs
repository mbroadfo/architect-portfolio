/* global window, document -- used inside page.evaluate callbacks, which run in the browser */
// Visual comparison of the renderer against the owner-approved prototype (not part of CI).
//
//   node visual/screenshots.mjs --release <folder>/release --prototype <prototype>/export \
//     --out <screenshot folder>
//
// Serves the release built by visual/build_release.py on 127.0.0.1 with the NFR15 policy
// `default-src 'self'; frame-ancestors 'none'`, screenshots home, catalog, a category page and
// the STARS page at 1440 and 390 px (renderer-*.png), and the prototype's export pages from
// file:// (prototype-*.png). It also reports CSP violations, requests to any other origin, and
// axe-core serious or critical violations (axe runs in a separate context that bypasses CSP,
// because axe is injected by the test). Playwright and axe-core come from web/node_modules.
import { createServer } from "node:http";
import { mkdirSync, readFileSync, statSync } from "node:fs";
import { createRequire } from "node:module";
import { extname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "@playwright/test";

const require = createRequire(import.meta.url);
const AXE_SOURCE = readFileSync(require.resolve("axe-core/axe.min.js"), "utf-8");
const CSP = "default-src 'self'; frame-ancestors 'none'";
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".woff2": "font/woff2",
  ".jpg": "image/jpeg",
  ".webp": "image/webp",
};
const WIDTHS = [1440, 390];
const PAGES = [
  ["home", "/", "index.html"],
  ["catalog", "/work/", "catalog.html"],
  ["category", "/category/astronomy", "catalog.html?category=astronomy"],
  ["stars", "/work/stars", "project.html?p=stars"],
];

function option(name) {
  const index = process.argv.indexOf(`--${name}`);
  const value = index >= 0 ? process.argv[index + 1] : undefined;
  if (!value) throw new Error(`missing --${name}`);
  return resolve(value);
}

function fileFor(root, urlPath) {
  const clean = decodeURIComponent(urlPath.split("?")[0]);
  const candidates = [join(root, clean), join(root, clean, "index.html")];
  return candidates.find((file) => {
    try {
      return file.startsWith(root) && statSync(file).isFile();
    } catch {
      return false;
    }
  });
}

function serve(root) {
  const server = createServer((request, response) => {
    const file = fileFor(root, request.url ?? "/");
    const status = file ? 200 : 404;
    const body = readFileSync(file ?? join(root, "404.html"));
    response.writeHead(status, {
      "content-type": TYPES[extname(file ?? ".html")] ?? "application/octet-stream",
      "content-security-policy": CSP,
      "x-content-type-options": "nosniff",
    });
    response.end(body);
  });
  return new Promise((done) => server.listen(0, "127.0.0.1", () => done(server)));
}

async function axeCounts(browser, url, width) {
  const context = await browser.newContext({ bypassCSP: true, viewport: { width, height: 900 } });
  const page = await context.newPage();
  await page.goto(url, { waitUntil: "networkidle" });
  await page.evaluate(AXE_SOURCE);
  const violations = await page.evaluate(async () => {
    const result = await window.axe.run(document, { resultTypes: ["violations"] });
    return result.violations.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }));
  });
  await context.close();
  return violations.filter((v) => v.impact === "serious" || v.impact === "critical");
}

async function shootRenderer(browser, origin, out, report) {
  for (const width of WIDTHS) {
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await context.newPage();
    const foreign = [];
    const cspErrors = [];
    page.on("request", (request) => {
      if (!request.url().startsWith(origin)) foreign.push(request.url());
    });
    page.on("console", (message) => {
      if (/Content Security Policy/i.test(message.text())) cspErrors.push(message.text());
    });
    for (const [name, path] of PAGES) {
      await page.goto(origin + path, { waitUntil: "networkidle" });
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: join(out, `renderer-${name}-${width}.png`), fullPage: true });
      const serious = await axeCounts(browser, origin + path, width);
      const controls = await page.locator(".hero__controls:not([hidden])").count();
      report.push({ page: name, width, axeSeriousOrCritical: serious, carouselControls: controls });
    }
    report.push({ width, foreignRequests: foreign, cspErrors });
    await context.close();
  }
}

async function shootPrototype(browser, prototype, out) {
  for (const width of WIDTHS) {
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await context.newPage();
    for (const [name, , file] of PAGES) {
      const [base, query] = file.split("?");
      const url = pathToFileURL(join(prototype, base)).href + (query ? `?${query}` : "");
      await page.goto(url, { waitUntil: "load" });
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: join(out, `prototype-${name}-${width}.png`), fullPage: true });
    }
    await context.close();
  }
}

const release = option("release");
const prototype = option("prototype");
const out = option("out");
mkdirSync(out, { recursive: true });
const server = await serve(release);
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch();
const report = [];
try {
  await shootRenderer(browser, origin, out, report);
  await shootPrototype(browser, prototype, out);
} finally {
  await browser.close();
  server.close();
}
console.log(JSON.stringify(report, null, 2));
