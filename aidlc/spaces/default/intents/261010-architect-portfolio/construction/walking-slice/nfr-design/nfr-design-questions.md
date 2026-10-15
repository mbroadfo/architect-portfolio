# NFR Design Questions — U0 walking-slice

**Inputs:**
- U0 NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- contract-summary (C2, C9, C11);
- components;
- team-practices;
- `nfr-design-questions.md`.

U0 is the delivery-only walking slice. S0 merges to `main`; S1 to S3 run only on the local stack.

Every answer is derived from the approved records and the U0 NFR requirements, under Michael's instruction to "continue autonomously". None of these questions is an owner decision.

## Questions

### Q1. How does the Python API render pages, given that the renderer is React?

A. The API calls the TypeScript slice renderer as a Node command-line subprocess. The snapshot goes in on stdin, and the rendered files come back as JSON on stdout. This mirrors the later U9 → U8 boundary, where Python is authoritative and Node only renders.
B. Render in Python.
X. Other (please specify)

[Answer]: A — Units Generation Q6 and constraints 2 to 4: React static generation, Python authoritative.

### Q2. How is the public folder swapped atomically?

A. Each Publish renders into `releases/<versionId>/`. The served path `public` is a symbolic link, replaced atomically with a rename of a temporary link, inside the Linux container volume. Old releases are pruned to the last three.
X. Other (please specify)

[Answer]: A — BR3.3 and REL-0.1. A symbolic-link swap is the standard atomic directory swap on Linux.

### Q3. Where does the local stack run?

A. Docker Compose on the developer's machine: MongoDB as a single-node replica set, the fake issuer, the API (Python, with a Node runtime for the renderer), and nginx serving `public` with the C9 headers. The Studio page runs on the Vite dev server on the host.
X. Other (please specify)

[Answer]: A — tech-stack decisions and NFR4.1 (free, local only).

### Q4. How are the S0 checks implemented?

A. GitHub Actions:
- `ci.yml` holds the aggregate job and its path-filtered steps;
- `codeql.yml` runs CodeQL;
- repository scripts implement the fake-identity-provider guard, the workflow lint and the content-bound review check;
- Dependabot keeps actions and dependencies updated.
X. Other (please specify)

[Answer]: A — BR5.1, BR5.2 and NFR13.1 to NFR13.6; team practice (Dependabot).

## Assumptions & Open Questions

None for the owner.
