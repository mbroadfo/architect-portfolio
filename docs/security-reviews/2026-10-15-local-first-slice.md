# Security review: local-first slice (local Studio, Git-backed content, static site build)

patch-id: 06e1071f55d11f2e8430b9bb29507de020e393a7
verdict: READY

- **Pull request:** #19 "[Draft, do not merge] Local-first slice: local Studio, Git-backed
  content, approved-design renderer (ADR-013)".
  - Head 83b2d7422834d5430e16b48620451512320cb9da, base `origin/main`.
  - The identity above is the one `python scripts/check_security_review.py --base origin/main
    --head HEAD` printed locally. The CI `review-check` log for 83b2d74 printed the same value.
- **Reviewer:** aidlc-devsecops-agent, a separate Claude session (Claude Opus 5.5) that did not
  author the change. Reviewed 2026-10-15. I changed no code. My probes ran from a scratch
  folder outside the repository, against temporary content repositories. I did not touch the
  owner's real content repository.
- **Verdict basis:** no Critical or High finding is open. There are two Medium and six Low
  findings, all open (LS-1 to LS-8).
  - LS-2 means the required `slice-e2e` check is red on this head, so the gate blocks the
    merge until it is fixed.
  - Fixing LS-2 changes the patch identity, which needs a new review record.

## Scope

I reviewed the diff from `origin/main`, concentrating on what is new since the reviewed U0
slice (`git diff origin/slice/walking-slice..HEAD`). I checked it against ADR-013 and against
FR4.2, FR4.5, FR4.10, FR7.1–7.5, FR8, FR10.6/10.7, NFR2, NFR9 and NFR15.

- `backend/portfolio_studio/`: all modules:
  - `server.py`, `site_server.py`, `service.py`, `store.py`, `build.py`;
  - `c2.py`, `model.py`, `images.py`, `github.py`;
  - `location.py`, `gitrepo.py`, `locking.py`, `importer.py`, `renderer.py`, `cli.py`.
- `backend/tests/unit/studio/`, and `backend/requirements-studio.in` and `.lock`.
- `web/local-studio/src/`: the API client, the editor, the preview frame, the publish and
  take-down dialogs, and `index.html` and `vite.config.ts`.
- `web/slice-renderer/`:
  - the page templates (`layout.tsx`, `home.tsx`, `catalog.tsx`, `exhibit.tsx`, `parts.tsx`,
    `pages.tsx`);
  - the client script (`src/client/*`, `assets/site.js`), the CSS and fonts with their OFL
    licences, `scripts/hash-assets.mjs` and `visual/`.
- `scripts/scan_output.py`:
  - count strings;
  - normalized multi-line text;
  - vocabulary fragments.
- `.github/workflows/ci.yml`, `.github/security-sensitive-paths.txt`,
  `scripts/verify-checks.toml` and `docs/LOCAL-STUDIO.md`.

**Not covered:** while I reviewed, the worktree held uncommitted edits by the author that are
not part of 83b2d74. They add:

- `backend/portfolio_studio/pages.py` and `scan.py`;
- a `POST /api/site/package` route;
- a `deploy-pages` CLI;
- changes to `build.py`, `cli.py`, `server.py` and `web/local-studio/src/`.

This record covers only the committed head 83b2d74. Committing those edits changes the patch
identity and needs a new review. They touch the Pages deployment boundary, so that review
should cover them in full.

## What I verified holds

I checked each point below by reading the code and, where marked, with a probe against the
test client or the service.

- **Loopback only (probed):** `check_bind_host` refuses every address other than `127.0.0.1`.
- **DNS rebinding (probed):** the Host header must be exactly `127.0.0.1:<port>` or
  `localhost:<port>`. These were all refused with 421:
  - `evil.example`;
  - a trailing dot, upper case, a missing port or a trailing space;
  - `[::1]:8765` and `0x7f000001:8765`.
  
  The preview route is covered too. The site server on port 8766 makes the same check.
- **CSRF from other local pages (probed):** a mutating request needs:
  - the exact Studio `Origin`;
  - `X-Studio-Request: 1`;
  - `Sec-Fetch-Site: same-origin` when the browser sends it.

  These were all refused with 403:
  - `Origin: null`;
  - a trailing slash, port 8766, or an upper-case scheme;
  - no Origin header at all;
  - `Sec-Fetch-Site: same-site`.

  `OPTIONS` gets 405 with no CORS headers. `Cross-Origin-Resource-Policy: same-origin` and
  `frame-ancestors 'none'` stop other origins reading or framing responses.
- **Path traversal (probed):** these all returned 404:
  - encoded `../` in `/media`, `/ui`, `/assets`, `/preview` and `/api/projects/{id}`;
  - an encoded `%2e%2e`.

  Ids, slugs and asset refs are anchored patterns. `_ui_file` checks containment after
  `resolve()`. Static assets must match their hash.
- **Git command injection:** git runs from an argument list with no shell. Titles reach git
  only as the value after `-m`. Paths come from validated ids. `--no-verify` skips the commit
  hooks.
- **Uploads (FR4.2, probed):**
  - **Type:** checked by file signature, and Pillow's detected format must agree. A GIF behind
    a JPEG signature, SVG, RIFF/WAVE, a truncated JPEG and an empty file were all refused.
  - **Size and pixels:** the 10 MB limit applies while reading. The side and pixel limits are
    checked from the header before decoding. PNG headers declaring 30000², 12000², 11999×3500,
    12001×10 and 100000×1 were all refused before any full decode.
  - **Metadata removed:** I sent a JPEG carrying EXIF with GPS and camera model, an ICC
    profile, a COM comment, an XMP APP1 segment and appended data. None of it survived into
    any derivative. The same held for PNG `tEXt`/`iTXt` chunks with trailing data, and for
    WebP EXIF and ICC. EXIF orientation is applied.
  - **Originals:** they stay under `projects/<id>/originals/`, and only digest-checked
    derivatives are ever copied to `published/`.
- **Publication boundary (FR7.1–7.5, NFR2, probed):**
  - **Drafts stay out of the build.** A draft saved after publishing does not reach
    `SiteBuilder.snapshot()`.
  - **The review is bound to its revision.** Publishing against a review whose draft has
    changed since is refused.
  - **Publish freezes what was reviewed.** It freezes the exhibit prepared at review time,
    and every derivative is checked against the digest recorded at upload.
  - **The build reads only `published/`.** It validates against closed C2 models and
    re-checks every media digest. It runs `scan_output.py` before the swap, and the previous
    output survives any failure.
  - **The review lists everything that becomes public:** text, images with alt text and
    captions, links, the live URL with its reason, badges, confirmed-public repositories,
    category, featured status and rights review.
- **Take down (FR8, probed):** take-down removes the published version and its media, and the
  next snapshot has no exhibits and no digests.
- **FR4.10 repository visibility:** it fails closed. A 404, 403, 429, any other status, a
  transport error, unreadable JSON, a non-public answer or a rename all mean "Source private",
  and no name, URL or licence is published. The Repository URL pattern is strict.
- **FR10.7 live URL:** the live URL is public only when it is included and authorized. The
  importer leaves both off.
  - The STARS and Baduk live URLs are already in the approved records (the launch inventory
    and the prototype).
  - No Risk or Monopoly value is added.
- **Escaping (FR4.5):** all owner text is rendered as React text, and there is no
  `dangerouslySetInnerHTML` or `innerHTML` in the renderer or the Studio. Link and live URLs
  must be `https://`. The client script builds DOM nodes only.
- **No tracking (NFR9):** `site.js` makes no network, storage, cookie or beacon calls.
- **Public headers (NFR15):** the site server sends:
  - `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`;
  - `nosniff`;
  - `Referrer-Policy: strict-origin-when-cross-origin`.
- **Preview isolation (probed):** preview pages run no scripts:
  - the CSP has `default-src 'none'` and `sandbox allow-same-origin`, with no
    `allow-scripts`;
  - `frame-ancestors 'self'`;
  - the Studio's iframe has `sandbox="allow-same-origin"`.
- **Logs:** the request log holds the method, route template, status and duration. The
  service logs hold only project ids.

## Findings

### LS-1. Medium: open. The location check accepts a content repository nested inside another repository

- **Location:** `backend/portfolio_studio/location.py`, `check_content_dir`.
- **Evidence (probe):**
  - I made an outer Git repository with `origin` set to
    `https://github.com/mbroadfo/architect-portfolio.git`, and inside it an `inner/` folder
    that is a Git repository of its own. `check_content_dir(inner)` **accepted** it.
  - This is because `git rev-parse --show-toplevel` from `inner` returns `inner` itself. The
    "inside another Git repository" check therefore never runs, and only the inner
    repository's remotes are inspected.
  - `code_roots()` covers only this repository's own work trees, not a separate clone of the
    public repository.
  - `PUBLIC_CODE_REPOSITORY` matches only the literal `github.com` host, so it misses an SSH
    host alias such as `git@gh-personal:mbroadfo/architect-portfolio.git` and `insteadOf`
    rewrites.
- **Impact:** `docs/LOCAL-STUDIO.md` and ADR-013 say a content directory inside another Git
  repository is refused. That is not true for a nested repository.
  - Git would record only a gitlink, not file contents, if the outer clone ran `git add -A`.
  - But the private content would sit inside a public-repository checkout, where agents and
    tools working on that clone can read it and copy it into tracked files.
- **Suggested fix:**
  - Also run `toplevel(resolved.parent)` and refuse when it returns any repository.
  - Check that enclosing repository's remotes too.
  - Match the remote path `mbroadfo/architect-portfolio` whatever the host.

### LS-2. Medium: open. The required end-to-end, integration and isolation checks do not run on this head

- **Location:**
  - `local/api.Dockerfile`, lines 8–13;
  - `local/api.Dockerfile.dockerignore`;
  - `web/slice-renderer/scripts/hash-assets.mjs`.
- **Evidence:** in `gh pr checks 19`, `slice-e2e` fails with
  `Error: ENOENT: no such file or directory, open 'styles/site.css'`.
  - `hash-assets.mjs` now reads `web/slice-renderer/styles/`.
  - The API image does not copy that folder, and its dockerignore does not include it.
  - As a result the verification stack never starts. `slice-integration`, `slice-e2e` and
    `verify-docker-isolation` all fail without testing anything.
- **Impact:** the U0 publication-boundary end-to-end checks and the header and isolation
  checks give no evidence for this head. The gate is red, so the merge is blocked.
- **Suggested fix:** copy `web/slice-renderer/styles` in `api.Dockerfile`, allow it in the
  dockerignore, and re-run CI. That changes the patch identity, so a new review record is
  needed.

### LS-3. Low: open. A cross-site GET can trigger preview rendering and GitHub checks

- **Location:** `backend/portfolio_studio/server.py`, `_refusal` (it checks Origin only for
  mutating methods) and the `/preview/{project_id}/{page}` route.
- **Evidence:**
  - A page on any origin can cause `GET http://127.0.0.1:8765/preview/stars/exhibit`, for
    example with an `<img>`. The Host is valid, so the request is served.
  - Every call starts the Node renderer: three previews made three renderer calls in my probe.
  - When the cache has expired (60 s after a failure, 600 s after a success), the call also
    makes uncredentialed GitHub API requests.
  - The response cannot be read because of CORP `same-origin`, and project ids are guessable
    slugs.
- **Impact:** CPU and outbound-request use only. There is no disclosure and no state change.
- **Suggested fix:** refuse any request whose `Sec-Fetch-Site` is present and is neither
  `same-origin` nor `none`, or at least do so for `/preview/` and `/api/`.

### LS-4. Low: open. The build swap is not reliable on Windows, and its rollback can be lost

- **Location:** `backend/portfolio_studio/build.py`, `_swap`.
- **Evidence:**
  - Locally on Windows, `staging.rename(output)` failed intermittently with `WinError 5
    Access is denied`.
  - The full run had 1 failure in 374 tests. Three re-runs of `test_build.py` failed, passed,
    then failed, each time on a different test.
  - On a clean export of 83b2d74, 1 of 5 runs of `test_build.py` failed the same way.
  - When the restore `previous.rename(output)` also fails, its `OSError` escapes without
    being handled. The output is then missing, and the next build's
    `shutil.rmtree(previous)` deletes the only copy before it swaps.
- **Impact:** this is fail-safe for publication, because nothing unscanned is ever put in
  place. But the "previous build is the rollback" property and the local test reliability do
  not hold on the owner's platform.
- **Suggested fix:**
  - Retry the renames with a short backoff.
  - Never delete `.previous` while `output` is missing.
  - Turn a failed restore into a `BuildFailedError` that says where the previous build is.

### LS-5. Low: open. Windows reserved device names are accepted as project ids and slugs

- **Location:**
  - `backend/portfolio_studio/model.py`: `ID_PATTERN` and `SLUG_PATTERN`;
  - `service.create` and `propose_slug`.
- **Evidence (probe):**
  - The title "Con" gives 500 `GIT_FAILED`.
  - The title "Nul" gives an unhandled `FileNotFoundError` from writing
    `projects/nul/project.json.tmp`, which reaches the client as a generic 500.
  - The slugs `con`, `nul` and `aux` save successfully. The build would then write
    `work/nul/index.html`.
  - The transaction restore left the repository clean.
- **Impact:** availability and robustness only.
- **Suggested fix:** refuse the reserved names (CON, PRN, AUX, NUL, COM1–9, LPT1–9) in ids and
  slugs, or add a suffix to them.

### LS-6. Low: open. Multi-picture JPEGs are rejected

- **Location:** `backend/portfolio_studio/images.py`, `_open_checked`.
- **Evidence (probe):** a two-frame MPO, the format many phone and camera JPEGs use, is
  refused with "the image content does not match its signature".
- **Impact:** this fails closed, so it is usability only. Michael will hit it with phone
  photos.
- **Suggested fix:** accept `MPO` behind a JPEG signature and decode only frame 0. The
  existing pixel limits and pixels-only re-encoding still apply.

### LS-7. Low (informational): open. Two values reach the build without a Publish confirmation

- **Location:**
  - `store.settings()` (`studio.json`);
  - `SiteBuilder.snapshot()`, where `generation` is `git rev-list --count HEAD`.
- **Evidence:**
  - The public `site` block (owner name and GitHub profile URL) is read from `studio.json`
    and does not go through a Publish confirmation.
  - The snapshot `generation` is the private repository's commit count, so it moves with
    every draft save.
  - Neither can be edited through the Studio. The defaults are already-public values.
  - `generation` is not rendered into the pages. It appears only in `<out>.build.json`,
    beside the output.
- **Impact:** small gaps in "nothing public without explicit confirmation" (FR7.1). Recheck
  them when the Cloudflare Pages deploy is designed: the deploy must upload only the scanned
  output folder, never the manifest beside it.

### LS-8. Low (informational): open. The rights-review block depends on the owner flagging the project

- **Location:** `backend/portfolio_studio/service.py`, `blockers`, and
  `model.py`, `rightsReviewRequired` (default `False`).
- **Evidence:** the importer refuses Monopoly and Risk. But a Monopoly-like exhibit created
  by hand in the Studio is blocked only if Michael ticks "rights review required".
- **Impact:** the FR10.6 block is a procedural control here. Consider showing the rights
  review in the Publish review even when it is "not required", as an explicit
  acknowledgement.

## Accepted by design (not findings)

- **Other software on this machine:** the Studio does not protect against it (stated in
  `docs/LOCAL-STUDIO.md`). This covers:
  - an edited `.git/config` in the content repository, such as `core.fsmonitor` or
    `core.hooksPath` with a post-commit hook;
  - symbolic links planted in the content repository.

  The media digest checks would still catch a derivative swapped for an original.
- **The public-output scan's limits:** its allow-list is built from the same `published/`
  files as the snapshot. It guards against renderer and template injection and unauthorized
  bytes. It cannot judge whether published text is appropriate; the Publish review is the
  control for that.

## Automated verification I relied on

- **Local tests:**
  - **Command:** `python -m pytest backend/tests/unit/studio tests/scripts -q`, run from the
    worktree with the main checkout's `.venv`.
  - **Result:** 373 passed and 1 failed. The failure is the Windows rename flake in LS-4.
  - **Re-runs of `test_build.py`:** 1 of 3 passed fully; the other two each failed one test,
    with the same `WinError 5`.
  - **Against a clean `git archive` of 83b2d74:** the 77 Studio tests passed twice in a row.
    Five runs of `test_build.py` had one failure, the same flake.
- **My probes:** about 20 scratch tests, covering Host, Origin, traversal, slugs, draft
  leakage, a stale review, metadata, pixel bombs, malformed files, MPO, preview headers,
  chunked upload, take-down and nested repositories. All are described above.
  - The symlink probe could not run: creating a symbolic link needs a privilege this Windows
    account lacks.
- **Dependency audits:**
  - `npm audit --audit-level=high` in `web/local-studio` and in `web/slice-renderer` found
    0 vulnerabilities.
  - `pip-audit --require-hashes -r backend/requirements-studio.lock` found no known
    vulnerabilities.
- **GitHub CI** (`gh pr checks 19`, run 38773165046, head 83b2d74):
  - **Pass:** CodeQL (javascript-typescript and python), gitleaks, audit, python, web, guard,
    changes, workflow-lint.
  - **Fail:** `slice-e2e` (LS-2), `review-check` (no record existed yet) and `gate`, which
    fails because of both.
  - The approval and privacy invariant tests for the Studio ran in the `python` job, which
    passed.
  - No preview-environment end-to-end run exists for this change, because no preview
    environment exists yet.
