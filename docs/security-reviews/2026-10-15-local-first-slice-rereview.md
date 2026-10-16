# Security re-review: local-first slice, with Cloudflare Pages packaging and deploy

patch-id: 2ea6960374b66f6a2cd20162a7db25eea8a046fa
verdict: READY

- **Pull request:** #19 "[Draft, do not merge] Local-first slice: local Studio, Git-backed
  content, approved-design renderer (ADR-013)".
  - Head b0a7e12843a682b0b83a30ac2c813c089d121e6e, base `origin/main`.
  - The identity above is the one `scripts/check_security_review.py --base origin/main --head
    b0a7e12` printed locally.
  - This record follows `2026-10-15-local-first-slice.md`, which covered 83b2d74. That record
    is now history only.
- **Reviewer:** aidlc-devsecops-agent, a separate Claude session (Claude Opus 5.5) that did not
  author the change or its fixes. Re-reviewed 2026-10-15. I changed no code.
  - I did not run `deploy-pages --execute` and did not contact Cloudflare. The one network
    call was `npm view wrangler@4.146.0 version`, to the npm registry.
  - My probes ran from a scratch folder outside the repository, against temporary content
    repositories.
- **Verdict basis:** no Critical or High finding is open.
  - **Fixed and verified by probe:** LS-1, LS-3, LS-4, LS-5 and LS-6.
  - **Partly fixed:** LS-2 (the stack now starts, but `slice-e2e` is still red) and LS-7.
  - **Closed as a procedural control:** LS-8.
  - **New and open:** three Medium and four Low findings on the Pages boundary, NP-1 to NP-7.
  - The required gate is still red because of LS-2, so the merge stays blocked until it
    passes.

## Scope

I reviewed `git diff 83b2d74..b0a7e12` in full:
- **Fix files:** `location.py`, `model.py`, `store.py`, `images.py`, `c2.py`, `service.py`,
  `gitrepo.py` and `server.py`, plus `local/api.Dockerfile` and its dockerignore.
- **New Pages boundary:**
  - `backend/portfolio_studio/pages.py` and `scan.py`;
  - the build manifest and saved scan inputs in `build.py`;
  - `package-pages` and `deploy-pages` in `cli.py`;
  - `POST /api/site/package`;
  - the Studio's "Package for Pages (staging)" button (`SiteView.tsx`, `api.ts`);
  - the rights-review UI (`Editor.tsx`, `PublishDialog.tsx`);
  - `docs/LOCAL-STUDIO.md`.
- **Tests:** the new and changed tests.

I compared the headers against NFR15 and FR4.4 in `inception/requirements-analysis/requirements.md`
and against `local/nginx.conf`.

## Status of the first review's findings

- **LS-1 (Medium): fixed.** `enclosing_work_trees` walks every enclosing work tree, and their
  remotes are checked as well. Remotes are matched on the `mbroadfo/architect-portfolio` path
  on any host. Probes:
  - A nested repository inside an outer repository is refused.
  - A standalone repository is refused when its remote is any of these:
    - HTTPS;
    - `git@gh-personal:…` (an SSH host alias);
    - `ssh://…:22/MBROADFO/Architect-Portfolio/` (mixed case);
    - an `insteadOf` alias (`pub:ap`);
    - a push-only URL.
  - `…/architect-portfolio-content.git` is accepted, which is correct.
- **LS-2 (Medium): partly fixed, still open.**
  - **What is fixed:** the API image now copies `styles/` and `licences/`, and the stack
    starts.
  - **What still fails:** in `gh pr checks 19` for b0a7e12, `slice-e2e` fails the
    public-output scan with `assets/site.a8f1af1889.js: static asset differs from its source`.
    The renderer stage of the Docker build (`node:22-slim`, `hash-assets.mjs`) produces a
    `site.js` that differs from the committed `assets/site.js` (`bfa9a436f7`). Locally on
    Windows, `hash-assets.mjs --check` passes.
  - **Impact:** the scan fails closed, as it should. But the served script and the committed,
    reviewed script are not reproducibly the same, and the end-to-end evidence is still
    missing.
  - **Suggested fix:** make the bundle deterministic across platforms, or have the image
    serve the committed `assets/` rather than rebuilding them. Then get `slice-e2e` green.
- **LS-3 (Low): fixed.**
  - `Sec-Fetch-Site: cross-site` and `same-site` now get 403 on every route, including the
    preview GET and `POST /api/site/package`.
  - `none` (direct navigation) and `same-origin` are still served for reads.
  - A changing request with `none` gets 403.
- **LS-4 (Low): fixed.**
  - Renames retry on transient Windows errors.
  - **Probe:** I injected failures into both the swap and the restore. The error names
    `.site.previous-<stamp>`, and that folder is kept intact. The next build puts it back
    first and then succeeds.
  - **Residual:** see NP-7 (Pages packaging does not use the retry).
- **LS-5 (Low): fixed.**
  - The titles Con, NUL, com1, Lpt9 and aux become `<name>-project`.
  - The slugs `con`, `nul`, `com1`, `lpt1` and `prn` are refused with 422; `con-x` is
    accepted.
  - `check_id` also refuses reserved names.
- **LS-6 (Low): fixed.**
  - A two-frame MPO carrying EXIF with GPS and camera model is accepted. Only the primary
    frame's pixels are used, and no EXIF or MPF data survives.
  - The secondary frames are never decoded. A secondary of 11000×3000 is not decoded at all;
    it stays only in the private original.
- **LS-7 (Low): partly fixed, accepted.**
  - **Fixed:** `generation` is now the constant `PUBLIC_GENERATION = 0`. `commit_count` is
    removed. Pages uploads only `site/`, not the build manifest or the artifact manifest.
  - **Remaining:** the `studio.json` site block still reaches the build without a Publish
    confirmation. It cannot be edited in the Studio and its defaults are already public, so I
    accept this as informational.
- **LS-8 (Low): closed as a procedural control.** The editor now has a prominent
  rights-review fieldset. The Publish review shows the rights-review state, including a
  warning when no review is required. Michael's judgement remains the control, as FR10.6
  intends.

## Pages boundary: what I verified holds

- **Packaging:**
  - It refuses a missing build, a build with no recorded scan, and a build whose files or
    saved scan inputs differ from the digests recorded at build time. Probe: an extra file in
    `build/site` was refused.
  - It copies the build and re-runs `scan_output.py` on the copy with the saved inputs.
    Probe: I tampered with the build *and* updated its manifest digests to match. Packaging
    still refused it, because the re-scan flagged the injected text.
  - `_headers` is the only file it adds.
  - Packaging into the code repository is refused. Artifacts are written under the content
    repository's `build/`, which Git ignores (probed with `git check-ignore`).
- **Changed files before a deploy (probed):** an extra file, or a changed file without a
  manifest update, is refused by `verify_artifact`. Verification runs again right before the
  upload.
- **Argument injection (probed):**
  - Project names must match `^[a-z0-9](…)$`.
  - Branches must start with an alphanumeric character, so `--help`, `-x` and
    `--production-branch` cannot become options.
  - `main&calc` was refused because the artifact was a staging one (the other guards caught
    it first). The branch pattern itself also excludes `&`.
  - Every value is a separate argument, and no shell is used on POSIX (see NP-4 for Windows).
- **Production guards (probed):** a production deploy needs all of:
  - `--production`;
  - `--i-have-owner-authorization`;
  - an artifact whose manifest says `mode: production`;
  - an explicit branch other than `staging`.

  Each missing piece was refused. A staging deploy accepts only `--branch staging`, and
  `Staging` with a capital S was refused. `POST /api/site/package` packages staging only.
- **Credentials:**
  - They are read only from the environment and reported as "set" or "NOT set". Probe: the
    token and account id never appeared in the output.
  - They are never placed on the command line.
  - Only `deploy-pages --execute` would use them.
- **Wrangler isolation (probed with an injected runner):**
  - Wrangler runs in an empty temporary folder.
  - `GIT_DIR` points at a path that does not exist, and `GIT_CEILING_DIRECTORIES` is set. Git
    fails with "not a git repository" both in that folder and inside the artifact's `site/`,
    which itself sits inside the content repository. So the content history cannot be read.
  - The commit message is `build-<stamp> (<mode>)` and holds no content.
  - `WRANGLER_SEND_METRICS=false`. Version 4.146.0 exists on npm.
- **NFR15 headers in `_headers`, on `/*`:**
  - CSP `default-src 'self'; frame-ancestors 'none'`;
  - HSTS `max-age=31536000`;
  - `nosniff`;
  - `Referrer-Policy: strict-origin-when-cross-origin`.

  This matches the U0 `local/nginx.conf` set, plus HSTS. `no-cache` applies to pages, and
  `/assets/*` and `/media/*` are immutable.
- **noindex:** staging adds `X-Robots-Tag: noindex` on `/*`, covering pages and media.
  Production omits it.
- **404 model (`served_file`):** `..`, encoded traversal, `/_headers` and unknown paths map to
  the root `404.html` with status 404.

## New findings

### NP-1. Medium: open. `deploy-pages` trusts the artifact's own manifest, so a consistently edited or hand-made artifact deploys

- **Location:** `backend/portfolio_studio/pages.py`, `verify_artifact` and `plan_deploy`.
- **Evidence (probes):**
  1. **A tampered package.** In a real package I added `site/_worker.js` (a Pages Function,
     which is server-side code) and replaced `index.html` with "PRIVATE DRAFT TEXT". Then I
     recomputed `manifest.json`. `plan_deploy` returned `executable: True` with no refusals.
  2. **Headers stripped.** I replaced `_headers` with a rule that has no CSP and no noindex,
     and recomputed the manifest. It was still executable.
  3. **A forged production artifact.** I changed `mode` to `production` in a staging
     artifact's manifest. With the flags it was executable, with no refusals.
  4. **A hand-made folder.** I wrote a folder with a forged `portfolio-pages-artifact/1`
     manifest and arbitrary HTML. It was executable.
- **Cause:**
  - The manifest is the only reference, and it sits inside the artifact.
  - Deploy does not re-run the scan.
  - Deploy does not check `_headers` against `headers_file(mode, …)`.
  - Deploy does not bind the artifact to a build or package record held elsewhere.
  - Deploy does not refuse Pages' special files: `_worker.js`, `_routes.json`, `_redirects`,
    `functions/`.
- **Impact:** the guarantee "deployment uses only an explicitly approved, validated artifact"
  holds only against accidental edits, not against an agent or person who edits the
  manifest too. The dry run would still say "all match the manifest".
- **Suggested fix:**
  - At deploy, re-run `scan_output.py` on `site/` (without `_headers`) using the build's
    saved scan inputs.
  - Regenerate `_headers` and require an exact match.
  - Refuse Pages special files and any key outside the scanned set.
  - Have `package-pages` print, and record in the content repository, the SHA-256 of
    `manifest.json`. Have `--execute` require it as `--expect-manifest <sha>`, so the value
    Michael approves is bound to what is uploaded.

### NP-2. Medium: open. The local production deploy path does not match the affirmed deployment policy, and its authorization is a self-asserted flag

- **Location:** `pages.py`, `plan_deploy` and `package_pages`; `cli.py`, `deploy-pages` and
  `package-pages`; `docs/LOCAL-STUDIO.md`, "Production".
- **Evidence:**
  - `team.md` § Deployment says every production deploy runs only in the GitHub `production`
    environment, with Michael personally approving the run.
  - This change adds a production deploy run locally with wrangler, gated only by
    `--production --i-have-owner-authorization`. Any agent with the Cloudflare credentials in
    its environment can type that flag.
  - ADR-013 is "accepted in principle" and does not record a production deployment mechanism.
    LOCAL-STUDIO.md says Michael approved Pages *for staging*.
- **Impact:** this governs public production deployment, the charter §7 rule "never deploy
  publicly without explicit authorization". The control is procedural only, and it differs
  from the recorded team practice.
- **Suggested fix:** take one of two routes.
  - Disable `--production` in `deploy-pages` until Michael approves an ADR or `team.md`
    amendment for the production mechanism.
  - Or route production through a GitHub `production` environment job that uploads a given
    artifact, with Michael as required reviewer and the token as an environment secret.

### NP-3. Medium: open. Take-down does not remove content from earlier Pages deployments

- **Location:** `docs/LOCAL-STUDIO.md`, "Rollback" and the take-down text; FR8.
- **Evidence:**
  - Every Pages Direct Upload creates a deployment with its own permanent
    `<hash>.<project>.pages.dev` address.
  - The docs rely on keeping earlier deployments and artifacts for rollback.
  - After a take-down, the next build and deploy leave the exhibit out of the current alias
    only. Every earlier deployment still serves the exhibit and its images.
  - `/media/*` is also sent as `immutable` for a year, so browsers keep their own copies.
- **Impact:** FR8 says take-down removes the exhibit from the public site. On Pages it stays
  publicly reachable to anyone holding an older deployment address. That includes production
  deployment addresses, which the documented Access policy on preview deployments may not
  cover.
- **Suggested fix:**
  - Document and automate a take-down step that deletes every earlier deployment containing
    the exhibit (wrangler `pages deployment delete`, or the dashboard).
  - Remove or retire the artifacts that contain it.
  - Confirm on the first staging deploy which deployment addresses Access covers.

### NP-4. Low: open. On Windows the deploy command runs through `npx.cmd`, and wrangler is fetched at deploy time

- **Location:** `pages.py`, `subprocess_runner` and the `plan_deploy` command list; `cli.py`
  (`shutil.which("npx")`).
- **How the command runs:** `shutil.which("npx")` returns
  `C:\Users\Mike\AppData\Roaming\npm\npx.CMD`, so the argument list passes through `cmd.exe`.
  `cmd.exe` interprets `&`, `|` and `%VAR%`, and Python does not escape them for batch files.
- **What can reach it today:** the project name, branch and commit message are restricted to
  safe characters. The artifact path is not: it comes from `--artifact`. A folder name such as
  `pages-x&calc`, or one holding `%CLOUDFLARE_API_TOKEN%`, would be interpreted by the shell.
- **Fetched at deploy time:**
  - `npx --yes wrangler@4.146.0` downloads wrangler when the deploy runs. The version is
    exact, but npm checks the download only against registry metadata, not against a
    committed lockfile.
  - Wrangler searches parent folders for configuration, and the temporary folder's parents
    include `%TEMP%` and the user profile.
- **Suggested fix:**
  - Refuse artifact paths outside `[A-Za-z0-9._:\\/ -]`.
  - Better, install wrangler as a pinned dev dependency with a lockfile and run
    `node <path>/wrangler-dist/cli.js` directly.

### NP-5. Low: open. The FR4.4 download headers are incomplete, and Pages behaviour is unverified

- **Location:** `pages.py`, `headers_file` and `DOWNLOAD_TYPES`.
- **Missing header:** FR4.4 requires public downloads to carry
  `Content-Security-Policy: sandbox; default-src 'none'`. The download rule does not detach
  and replace the site CSP, so downloads would carry `default-src 'self'` instead.
- **PDF type:** PDFs get `application/pdf`. FR4.4 says `application/octet-stream` unless NFR
  Design fixes a more specific type.
- **Not live today:** attachments are limited to zero (C2 `attachments: max 0`), so none of
  this is reachable yet. Fix it before attachments are enabled.
- **Unverified on a live deployment:**
  - whether Pages lets `_headers` override `Content-Type`;
  - the trailing-slash redirect;
  - the 404 handling.

  `category-404.html` is uploaded and can be fetched as a normal page (at `/category-404`).
  That is harmless, but confirm it on the first staging deploy, as the docs say.

### NP-6. Low: open. The staging guards depend on Cloudflare project settings the tool does not check

- **Location:** `pages.py`, `plan_deploy` (`STAGING_BRANCH`); `docs/LOCAL-STUDIO.md`,
  one-time setup.
- **Evidence:**
  - "Staging" means `--branch staging` on whatever project is named.
  - If the project's production branch is `staging`, a "staging" deploy is a production
    deploy, with noindex.
  - Staging is private only if Michael enables the Access policy on preview deployments.
    Otherwise it is publicly reachable, though noindex.
  - The tool checks neither setting.
- **Suggested fix:**
  - Use a dedicated staging project, and refuse the production project's name for staging.
  - Or record the production branch name in the artifact or in configuration, and refuse
    when it is `staging`.
  - Add the Access check to the first-deploy checklist.

### NP-7. Low: open. The artifact rename has no retry, so a Pages test is flaky on Windows

- **Location:** `pages.py`, `package_pages` (`temporary.rename(target)`).
- **Evidence:**
  - It uses a plain rename, not `rename_with_retry`.
  - `test_dry_run_prints_the_command_and_summary_and_never_the_token` failed once in the full
    local run, and once in 3 runs of `test_pages.py`. It passed in every later isolated run.
  - The likely cause is the same transient Windows sharing error as LS-4. I did not capture
    the traceback.
- **Impact:** packaging fails closed, so this is reliability only.
- **Suggested fix:** use `rename_with_retry`.

## Automated verification I relied on

- **Local tests:**
  - **Command:** `python -m pytest backend/tests/unit/studio tests/scripts -q`, at b0a7e12.
  - **Result:** 426 passed and 1 failed. The failure is NP-7.
  - **Re-runs of `test_pages.py`:** 7 of 8 passed (3 runs, then 5 more).
- **My probes:** 21 scratch tests covering LS-1 to LS-7 and the Pages boundary, described
  above. All ran with injected runners; nothing was uploaded.
- **GitHub CI** (`gh pr checks 19`, run 38777122368, head b0a7e12):
  - **Pass:** CodeQL (javascript-typescript and python), gitleaks, audit, python, web, guard,
    changes, workflow-lint.
  - **Fail:** `slice-e2e` (LS-2: static asset differs from its source), `review-check` (no
    record yet for this identity) and `gate`.
  - The dependency audits ran in the `audit` job, which passed.
  - No preview or staging deployment exists, so no post-deploy header smoke check has run
    (NFR15).
