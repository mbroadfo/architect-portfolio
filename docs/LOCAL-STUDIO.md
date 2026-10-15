# Local Studio (L2, ADR-013)

The Studio runs only on Michael's machine. Content lives in a **private** Git repository beside this public code repository. The public site is generated **only** from published versions. It is checked by the public-output scan before it replaces the previous build.

## Prerequisites (once)

```bash
# Python 3.12+ virtual environment, then the Studio's locked dependencies
python -m pip install --require-hashes -r backend/requirements-studio.lock
# The Studio page
npm --prefix web/local-studio ci && npm --prefix web/local-studio run build
# The shared renderer CLI (web/slice-renderer/dist/cli.cjs)
npm --prefix web/slice-renderer ci && npm --prefix web/slice-renderer run build:cli
```

Run the commands below from `backend/`, or put `backend/` on `PYTHONPATH`. `--content` defaults to `../architect-portfolio-content`, beside the main checkout.

## Commands

| Command | What it does |
|---|---|
| `python -m portfolio_studio init` | Creates the private content repository: `git init`, a README and a `.gitignore`. There is no remote. |
| `python -m portfolio_studio import-prototype --project stars` | Creates a **Draft** from the approved prototype's copy and live captures. It never publishes. Only `stars` and `baduk` are accepted. |
| `python -m portfolio_studio serve [--port 8765]` | Starts the Studio at `http://127.0.0.1:8765/`. It also serves the generated site at `http://127.0.0.1:8766/` (`--site-port 0` turns that off). |
| `python -m portfolio_studio build [--out DIR]` | Generates the public site from published versions only. The default output is `<content>/build/site`. |
| `python -m portfolio_studio serve-site [--port 8766]` | Serves the generated site with the public security headers. |
| `python -m portfolio_studio backup --to FILE.bundle` | Writes a verified `git bundle` of the whole content repository. |
| `python -m portfolio_studio package-pages [--staging \| --production --i-have-owner-authorization]` | Packages the last scanned build for Cloudflare Pages as `<content>/build/pages-<timestamp>/`. It uploads nothing. Staging is the default. |
| `python -m portfolio_studio deploy-pages --artifact DIR [--project P] [--branch staging] [--execute]` | Prints a **dry run** by default. It uploads only with `--execute` and every guard in place (below). |

`serve` and `build` accept `--renderer-root DIR`, a renderer folder that holds `dist/cli.cjs`, `assets/` and `src/*strings.json`. The default is `web/slice-renderer`.

## Content repository layout

```
README.md                        private; never push to a public remote
studio.json                      public site block: owner name, GitHub profile
projects/<id>/project.json       the draft (revision, text, sections, links, access, images)
projects/<id>/originals/         private original uploads (may contain GPS); never published
projects/<id>/derived/<ref>/     sanitized WebP and JPEG variants (w480/w960/w1600)
published/<id>.json              frozen published version: C2 exhibit fields + SHA-256 of
                                 each derivative, bound to the confirmed draft revision
published/media/<ref>/           the derivatives the published versions use
published/featured-order.json    published carousel order (project ids)
withdrawn/<id>.json              take-down record (status "Taken down")
build/                           generated site output (not committed)
```

Every create, save, upload, publish, update, take-down and featured-order change is one commit. `git log` is the activity log, and the Studio's Activity screen shows it.

## How to publish

1. **Projects:** open the project.
2. **Edit it.** Every image needs alt text, and one image is the lead image. The live URL becomes public only when it is both **authorized** and **included at Publish**. Save your changes.
3. **Preview** shows the saved draft, rendered by the shared renderer in a sandboxed frame. It is marked "Preview — not public".
4. **Review publication** (or **Review update**) lists everything that becomes public: text, images with alt text, links, the live URL, badges, repositories with their GitHub check, category, featured status and rights review. Publish is blocked when the title is empty, there is no lead image, alt text is missing, or a rights review is outstanding.
5. Confirming publishes exactly that reviewed revision. If the draft changed in between, the confirmation is refused.
6. **Public site → Build the public site.** If the build or the scan fails, the previous site stays in place. **View the generated site** opens it.

**Take down** removes the published version and its media. The next build leaves the exhibit out. The Studio content is kept.

## Staging on Cloudflare Pages (Direct Upload)

Michael approved Cloudflare Pages for staging. Creating any Cloudflare resource, connecting the domain, deploying and spending each still need his explicit authorization. The commands below make **no Cloudflare call** except `deploy-pages --execute`.

### What a package is

`package-pages` takes the build currently in place (`build/site`). It accepts the build only when that build passed the public-output scan and its files still match the SHA-256 digests recorded when it passed. It writes:

```
build/pages-<UTC timestamp>/
  site/            uploaded to Pages: the build's files, unchanged, plus _headers
  manifest.json    never uploaded: every file's SHA-256 and size, the source build id and its
                   scan result, the exhibits and revisions it contains, staging or production
```

- **Checks before writing:** it re-verifies every copied file. It re-runs `scripts/scan_output.py` on the copy, using the inputs saved with the build (`build/site.scan-inputs/`).
- **What it adds:** `_headers` is the only file it adds. No `_redirects` file is needed.
- **Refusals:**
  - no build;
  - a build without a passed scan;
  - a build changed after its scan;
  - any file over 25 MiB;
  - more than 20,000 files;
  - more than 100 header rules.
- **Headers (`_headers`) on every path:**
  - CSP `default-src 'self'; frame-ancestors 'none'`;
  - HSTS `max-age=31536000`;
  - `nosniff`;
  - `Referrer-Policy: strict-origin-when-cross-origin`;
  - `Cache-Control: no-cache` for pages.
- **Long-lived files:** `/assets/*` and `/media/*` are immutable for a year. Their names carry a hash or a unique asset reference.
- **Downloads**, when there are any, get `Content-Disposition: attachment` and a fixed type (FR4.4).
- **Staging vs production:**
  - Staging packages add `X-Robots-Tag: noindex` everywhere. Pages also adds it on preview deployments.
  - A production package (`--production`) omits it and is refused without `--i-have-owner-authorization`.

**Addresses on Pages.** The build already writes Pages-servable files:

| Address | File |
|---|---|
| `/` | `index.html` |
| `/work/` | `work/index.html` |
| `/work/<slug>` | `work/<slug>/index.html` |
| `/category/<slug>` | `category/<slug>/index.html` |

- **Trailing slash:** following Pages' documented folder handling, Pages answers `/work/<slug>` with a redirect to `/work/<slug>/`. Both forms are valid site links.
- **Missing pages:** an address with no file gets the root `404.html` with status 404, for an exhibit or a category that is not on display.
- **Category pages:** a missing category therefore shows the general "This exhibit isn't on display" page, with the correct 404 status, rather than the category wording. `category-404.html` stays in the package because the scan expects it.
- **Unverified:** the redirect and 404 behaviour come from Pages' documentation and have not been checked against a live deployment. Confirm them on the first staging deployment.

### Michael's one-time setup (needs his authorization)

1. In the Cloudflare dashboard, create a Pages project with **Direct Upload**. A Direct Upload project can never switch to Git integration, and that is intended: no Git connection. Note its name and its production branch.
2. Create an API token scoped to **Account → Cloudflare Pages → Edit**, for this account only, with nothing else.
3. Enable an **Access policy for preview deployments** on the project, so `staging.<project>.pages.dev` is reachable only by Michael.
4. Keep the token out of every file. Set it only in the shell that runs the deploy:
   `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.

### Each staging deployment

1. In the Studio: publish what should be public, then use **Public site → Build the public site**. Check it at http://127.0.0.1:8766/.
2. **Public site → Package for Pages (staging)**, or `python -m portfolio_studio package-pages`.
3. Dry run: `python -m portfolio_studio deploy-pages --artifact <content>/build/pages-<timestamp> --project <name>`. It prints:
   - the exact wrangler command;
   - the exhibits and revisions, the file count and total bytes;
   - whether each credential is set (never its value);
   - that every file matches the manifest.

   It uploads nothing.
4. After Michael's authorization, execute it: the same command plus `--branch staging --execute`.
   - Wrangler (pinned version) receives the credentials only through the environment.
   - It runs from an empty temporary folder with Git disabled, so it cannot read or send the private content repository's history.
   - The artifact is verified again just before the upload.
   - The deployment is a **preview** deployment at `staging.<project>.pages.dev`.

**Production** needs a package made with `--production --i-have-owner-authorization`, and `deploy-pages --production --i-have-owner-authorization --branch <production branch> --execute`. It must never be used without Michael's recorded authorization.

### Rollback

- In the Pages dashboard, use **Rollback** on the previous deployment.
- Or redeploy an earlier `build/pages-<timestamp>` artifact with `deploy-pages`. Artifacts are kept until you delete them, and each one is verified against its manifest before it is uploaded.

## Backup

Back up with `backup --to D:\backups\portfolio-content-YYYYMMDD.bundle` (outside the code repository). To restore, run `git clone <bundle> architect-portfolio-content`. A private remote for off-machine backup **needs Michael's explicit authorization first**.

## Security model

- **Location:** the Studio refuses a content directory that:
  - is inside the code repository (any work tree);
  - is inside any other Git work tree, even as a nested repository of its own, including a separate clone of the public repository;
  - has, or sits inside a repository that has, a remote naming `mbroadfo/architect-portfolio` on any host or URL form (HTTPS, SSH, an SSH host alias), after resolving `insteadOf` rewrites.

  Site output and backups inside the code repository are refused too.
- **Loopback only:** the server binds `127.0.0.1` and refuses any other address.
- **Host header:** requests must name `127.0.0.1:<port>` or `localhost:<port>`. This defends against DNS rebinding.
- **Cross-site requests:** any request whose `Sec-Fetch-Site` is present and is neither `same-origin` nor `none` is refused on every route, so another website cannot even start a preview.
- **Requests that change data** must carry:
  - the Studio's own `Origin`;
  - `X-Studio-Request: 1`, which no cross-site form or image can send without a CORS preflight, and the server never grants one;
  - `Sec-Fetch-Site: same-origin`, whenever the browser sends that header.
- **Headers on the Studio pages:**
  - CSP `default-src 'self'` with `frame-ancestors 'none'`;
  - `nosniff`, `no-referrer`, COOP and CORP `same-origin`;
  - `no-store`.
- **Preview pages** are framed only by the Studio itself, sandboxed, and run no scripts.
- **One writer:** an OS-level lock (`.studio.lock`) admits one Studio process per content repository. Each operation is serialized and committed. A failed commit restores the files.
- **Uploads:**
  - JPEG (including multi-picture JPEGs from phones, of which only the primary image is used), PNG or WebP, identified by file signature;
  - at most 10 MB, 40 megapixels and 12,000 px on a side, checked before decoding;
  - re-encoded to pixels only, so no EXIF, GPS, ICC or XMP survives;
  - originals stay in `projects/<id>/originals/` and are never published.
- **Repositories:** visibility and licence are read from the public GitHub API without credentials. Any error, 404, rate limit, rename or private answer means "Source private", and no name or link is published.
- **Build:**
  - it reads only `published/`;
  - the snapshot is validated against closed C2 models;
  - media must match the digests frozen at publish;
  - `scripts/scan_output.py` must report no findings before the atomic swap.
- **Names:** Windows reserved device names (`con`, `nul`, `aux`, `prn`, `com1`–`com9`, `lpt1`–`lpt9`) are refused as addresses. A title that maps to one gets a suffix, so "Con" becomes `con-project`.
- **Build swap:** the previous build is moved aside under a new name and deleted only after the new build is in place. Renames retry on transient Windows sharing errors. If even the restore fails, the error names the folder that holds the complete previous build, and the next build puts it back first.
- **Nothing private in the output:** the C2 `generation` is a fixed value, not the content repository's commit count. Pages uploads only `site/`.
- **Logs** record method, route template, status and duration, never content.

There is no sign-in, because the Studio is not reachable from other machines. It protects nothing against other software already running as Michael on this machine.
