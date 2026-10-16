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
# Only for staging deploys: the pinned wrangler (tools/pages-deploy/package-lock.json)
npm --prefix tools/pages-deploy ci --ignore-scripts
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
| `python -m portfolio_studio package-pages [--staging \| --production]` | Packages the last scanned build for Cloudflare Pages as `<content>/build/pages-<timestamp>/` and registers it in `deployments/packages.json`. Staging is the default; production packages are never deployed by this tool. |
| `python -m portfolio_studio deploy-pages --artifact DIR [--project P] [--execute]` | Prints a **dry run** by default. It uploads to the `staging` branch only, with `--execute` and every guard in place (below). |
| `python -m portfolio_studio prune-deployments [--project P] [--execute]` | Prints a **dry run** by default. With `--execute`, deletes every older staging deployment except the newest. |

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
deployments/packages.json        the Pages package register: each package and staging deployment
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

Michael approved Cloudflare Pages **for staging only**. Creating any Cloudflare resource, connecting the domain, deploying and spending each still need his explicit authorization. Only `deploy-pages --execute` and `prune-deployments --execute` contact Cloudflare.

**Production is not deployable from this tool.** Team practice puts every production deploy in a run of the GitHub `production` environment that Michael approves as its required reviewer. A production mechanism for Pages, for example a `production` environment job that uploads a registered artifact with the token as an environment secret, needs its own design, an ADR or `team.md` amendment, and Michael's approval. `package-pages --production` exists only to inspect a package without `noindex`. `deploy-pages` refuses production artifacts and has no production, branch or authorization flag; the branch is always `staging`.

### What a package is

`package-pages` takes the build currently in place (`build/site`). It accepts the build only when that build passed the public-output scan and its files still match the SHA-256 digests recorded when it passed. It writes:

```
build/pages-<UTC timestamp>/
  site/            uploaded to Pages: the build's files, unchanged, plus _headers
  scan-inputs/     the build's scan inputs, so a deploy can re-run the same scan
  manifest.json    never uploaded: every file's SHA-256 and size, the source build id and its
                   scan result, the exhibits and revisions, staging or production
```

- **Register:** each package is recorded in `deployments/packages.json` in the private content repository and committed there. The record holds the manifest's SHA-256, the build id, the mode, the exhibits and revisions, the public media and downloads, and the digests of the scan inputs. Each staging deployment is recorded there too.
- **Checks before writing:** every copied file is re-verified, and `scripts/scan_output.py` runs again on the copy.
- **What it adds:** `_headers` only. No `_redirects`, `_routes.json`, `_worker.js` or `functions/`.
- **Refusals:** no build; a build without a passed scan; a build changed after its scan; any file over 25 MiB; more than 20,000 files; more than 100 header rules.
- **Headers on every path:** CSP `default-src 'self'; frame-ancestors 'none'`; HSTS `max-age=31536000`; `nosniff`; `Referrer-Policy: strict-origin-when-cross-origin`; `Cache-Control: no-cache` for pages; and, for staging, `X-Robots-Tag: noindex`. Pages also adds noindex on preview deployments.
- **Long-lived files:** `/assets/*` and `/media/*` are immutable for a year. Their names carry a content hash or a unique asset reference, so a changed image is always a new address.
- **Downloads (FR4.4)**, when attachments are enabled:
  - `Content-Type: application/octet-stream` for every type, PDF included;
  - `Content-Disposition: attachment`;
  - `X-Content-Type-Options: nosniff`;
  - `Content-Security-Policy: sandbox; default-src 'none'`.

  Each replaces the site-wide value with `! <header>`, because Pages joins repeated headers with commas. Whether Pages lets `_headers` override `Content-Type` must be confirmed on the first deployment that has a download.

**Addresses on Pages.** The build already writes Pages-servable files:

| Address | File |
|---|---|
| `/` | `index.html` |
| `/work/` | `work/index.html` |
| `/work/<slug>` | `work/<slug>/index.html` |
| `/category/<slug>` | `category/<slug>/index.html` |

- **Trailing slash:** following Pages' documented folder handling, `/work/<slug>` redirects to `/work/<slug>/`. Both forms are valid site links.
- **Missing pages:** an address with no file gets the root `404.html` with status 404. That covers an exhibit or a category that is not on display, so a missing category shows the general "This exhibit isn't on display" wording.
- **`category-404.html`** stays in the package because the scan expects it. It can be fetched as an ordinary page at `/category-404`, which is harmless.
- **Unverified:** the redirect, the 404 behaviour and the header override come from Pages' documentation and have not been checked against a live deployment. Confirm them on the first staging deployment.

### What `deploy-pages` checks

`deploy-pages` reads only the register and the artifact. It trusts nothing the artifact says about itself. Before any upload, it:

1. **Checks the path:** the artifact must be an absolute `<content>/build/pages-<timestamp>` path with no shell metacharacters.
2. **Checks the register:** the artifact's `manifest.json` SHA-256 must be registered. The register entry and the manifest must agree on folder, build id, exhibits and mode, and the mode must be `staging`.
3. **Checks the files:** `site/` must hold exactly the manifest's files with their digests. Any Pages special file is refused: `_worker.js` as a file or folder, `functions/`, `_routes.json`, `_redirects`, any other `_` file, and any dotfile.
4. **Regenerates `_headers`** from this code and the mode, and requires the packaged one to be byte-identical.
5. **Re-runs the scan:** `scripts/scan_output.py` runs again on `site/` without `_headers`, using the artifact's scan inputs, whose digests must match the register.
6. **Executes only with every guard:** `--execute`, `--project`, and both credentials in the environment.
7. **Reads the production branch** from the Cloudflare API: `GET /accounts/{account}/pages/projects/{project}`. The deploy is refused if the branch is not set or is `staging`.
8. **Uploads to `--branch staging`**, then records the deployment in the register.

How wrangler runs:

- **Pinned locally:** `tools/pages-deploy`, version 4.149.0, installed with `npm ci` from the committed lockfile.
- **No shell:** it runs as `node <...>/wrangler/bin/wrangler.js` with an argument list, never through `npx` or `cmd.exe`.
- **No configuration:** it runs from an empty temporary folder. `pages deploy` in this wrangler version has no `--config` flag, so the tool instead refuses to run if a `wrangler.toml`, `wrangler.json` or `wrangler.jsonc` exists in that folder or any parent.
- **No Git:** Git is disabled (`GIT_DIR` points at a missing folder), so wrangler cannot read or send the private repository's commit messages.
- **Credentials:** they reach wrangler and the API only through the environment. They are never printed, stored or put on a command line.

### Take-down and old deployments (FR8)

Every Pages deployment keeps a permanent address of its own, `<hash>.<project>.pages.dev`. A taken-down exhibit therefore stays reachable at the addresses of older deployments until they are deleted.

- **Automatic prune:** after a successful deploy, if the new package drops any exhibit or public file that the previously deployed package had, `deploy-pages --execute` runs the prune. The prune deletes every `staging` preview deployment except the newest, using `wrangler pages deployment delete <id> --force`. Production deployments are never touched. The deploy then warns that cached copies may persist briefly.
- **Manual prune:** `python -m portfolio_studio prune-deployments --project <name>` is a dry run. Add `--execute` to delete.
- **What take-down relies on:** the immutable `/media` cache is safe because every address is content-addressed. Take-down depends on the prune plus the old address no longer being linked from any page. Browsers and Cloudflare's edge may keep cached copies until they expire. For production, the take-down procedure must also include a Cloudflare cache purge.
- **Rollback** means redeploying an earlier **registered** artifact with `deploy-pages`. It never means keeping old deployments around, and an artifact containing a taken-down exhibit must not be redeployed.

### Michael's one-time setup (needs his authorization)

1. In the Cloudflare dashboard, create a Pages project with **Direct Upload**, and set its **production branch to `production`**. The tool refuses to deploy when the production branch is unset or `staging`. A Direct Upload project can never switch to Git integration, which is intended.
2. Create an API token scoped to **Account → Cloudflare Pages → Edit**, for this account only, with nothing else.
3. Enable an **Access policy for preview deployments**, so `staging.<project>.pages.dev` and every per-deployment address are reachable only by Michael. The tool cannot verify this setting. Check it on the first deployment, including which addresses the policy covers.
4. Set `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` only in the shell that runs the deploy. Never write them to a file.
5. Install the pinned wrangler: `npm --prefix tools/pages-deploy ci --ignore-scripts`.

### Each staging deployment

1. **Build:** in the Studio, publish what should be public, then **Public site → Build the public site**. Check it at http://127.0.0.1:8766/.
2. **Package:** **Public site → Package for Pages (staging)**, or `python -m portfolio_studio package-pages`. This registers and commits the package.
3. **Dry run:** `python -m portfolio_studio deploy-pages --artifact <content>/build/pages-<timestamp> --project <name>`. It runs every check above and prints the exact command, the registered manifest digest, the exhibits and revisions, the file count and bytes, and whether each credential is set. It uploads nothing.
4. **Execute**, after Michael's authorization: the same command plus `--execute`.

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
- **Pages boundary:** a deploy needs a registered package, re-validates it in full and goes to staging only; see "What `deploy-pages` checks".
- **Logs** record method, route template, status and duration, never content.

There is no sign-in, because the Studio is not reachable from other machines. It protects nothing against other software already running as Michael on this machine.
