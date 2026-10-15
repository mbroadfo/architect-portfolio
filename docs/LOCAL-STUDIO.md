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

## Backup

Back up with `backup --to D:\backups\portfolio-content-YYYYMMDD.bundle` (outside the code repository). To restore, run `git clone <bundle> architect-portfolio-content`. A private remote for off-machine backup **needs Michael's explicit authorization first**.

## Security model

- **Location:** the Studio refuses a content directory inside the code repository (any work tree), inside another Git repository, or with a remote pointing at `github.com/mbroadfo/architect-portfolio`. Site output and backups inside the code repository are refused too.
- **Loopback only:** the server binds `127.0.0.1` and refuses any other address.
- **Host header:** requests must name `127.0.0.1:<port>` or `localhost:<port>`. This defends against DNS rebinding.
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
  - JPEG, PNG or WebP, identified by file signature;
  - at most 10 MB, 40 megapixels and 12,000 px on a side, checked before decoding;
  - re-encoded to pixels only, so no EXIF, GPS, ICC or XMP survives;
  - originals stay in `projects/<id>/originals/` and are never published.
- **Repositories:** visibility and licence are read from the public GitHub API without credentials. Any error, 404, rate limit, rename or private answer means "Source private", and no name or link is published.
- **Build:**
  - it reads only `published/`;
  - the snapshot is validated against closed C2 models;
  - media must match the digests frozen at publish;
  - `scripts/scan_output.py` must report no findings before the atomic swap.
- **Logs** record method, route template, status and duration, never content.

There is no sign-in, because the Studio is not reachable from other machines. It protects nothing against other software already running as Michael on this machine.
