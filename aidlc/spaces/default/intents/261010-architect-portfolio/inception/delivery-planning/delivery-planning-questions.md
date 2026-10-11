# Delivery Planning — Questions

**Inputs:**
- requirements — `../requirements-analysis/requirements.md`;
- mockups — `../refined-mockups/mockups.md`;
- components — `../domain-design/components.md`;
- unit-of-work, unit-of-work-dependency and unit-of-work-story-map — `../units-generation/`;
- contract-summary — `../contract-design/contract-summary.md`;
- team-practices — `../practices-discovery/team-practices.md`, as affirmed in `aidlc/spaces/default/memory/team.md` and `project.md`;
- decisions D-01 to D-28 and P-01 to P-08.

Each answer comes from those approved records. Michael's standing instructions are to "handle routine decisions autonomously using the approved charter, recorded decisions, and sensible defaults" and to "return only for the required approval gate or a genuinely consequential decision" (P-05, P-08).

A **Bolt** is one build pass over part of a unit of work. It ends in working, tested code merged through one pull request, normally within one to two days (team practice, Way of Working).

## Strategic Questions

### Q1. What should be built first?

A. Follow the approved dependency graph. Within each set of units that are ready together, put risk first: the security boundaries and the contracts every unit builds against. Within each unit, build the thinnest piece that runs end to end first.
B. Value first: the visible public site before anything else.
C. A formal walking skeleton across all units before anything else.
X. Other (please specify)

[Answer]: Revised at Michael's Request Changes (2026-10-11): an early, thin, end-to-end walking slice first, as the delivery-only unit U0, with CI first (S0) (D1 in `bolt-plan.md`). After it comes the approved dependency graph one unit at a time, with the Studio moved earlier and risk first where the order is open.

Michael's words: "Introduce an early, thin, end-to-end walking slice: a local or preview implementation demonstrating a project created, saved, previewed and published as a static public page, using fake or isolated dependencies initially."

The original answer, A, is kept below for the record. Team practice (Walking Skeleton) says the plan declares `skeleton: off`, so there is no skeleton ceremony. It also says Delivery Planning "orders the work so the thinnest integrated path comes first" and lists four things to prove early:
- the public page builds and is served;
- the API answers a health check;
- CI passes using OIDC;
- the Terraform plan is clean.

The concentration of risk in four boundaries (ADR-001) argues for doing those early. Construction runs one unit at a time, following the approved graph (unit-major, serial).

### Q2. Should the work be scored with a formal model?

A. A light score in the style of WSJF (Weighted Shortest Job First): value plus time criticality plus risk reduction, divided by size. It is used only to break ties within a ready set, and is recorded in `risk-and-sequencing-rationale.md`.
B. A full WSJF backlog.
C. No scoring.
X. Other (please specify)

[Answer]: A — the dependency graph already fixes most of the order. A light score is enough to explain the remaining choices, and a full backlog would be ceremony for one owner.

### Q3. How big is one Bolt?

A. A slice of one unit, sized to one pull request merged within one to two days. Large units are split into several Bolts, using the size scale (S = 1 Bolt, M = 2, L = 3 or 4, XL = 5 or more).
B. One Bolt per unit.
C. Thin slices that cut across units.
X. Other (please specify)

[Answer]: A, unchanged. Bolts are still pull-request sized: 34 in total, with S0 to S3 and B05a added and B30 moved into Build and Test. Each unit's engine checkpoint presents its demonstration, progress, review recommendations and individual Bolt decisions together (D2-A).

This follows team practice (one short-lived branch per Bolt, merged within one to two days, one squash commit) and the size scale in `unit-of-work.md`. Under unit-major Construction, cross-unit slices would contradict the approved iteration order.

### Q4. Can Bolts be built at the same time?

A. Construction runs one Bolt at a time from this session (unit-major, serial). Independent coding agents may work in parallel on isolated branches only when Michael starts them, and the workflow state keeps exactly one owner.
B. Swarm execution.
X. Other (please specify)

[Answer]: Revised after evaluation (revisions 3 and 4): stay unit-major and serial. The engine's parallel swarm was evaluated and is not recommended now:
- it lands one squash commit per unit, while team practice needs one per Bolt;
- `org.md` fixes the merge target as `main`;
- preview deployments and security reviews are serial bottlenecks anyway.

The changes swarm would need are listed in `bolt-plan.md`, for Michael to choose later.

The original answer, A, is kept for the record. The recorded Construction settings are checkpoints enabled, unit-major, serial. Project rule: exactly one owner of the workflow state (P-05: Claude Code). Changing to parallel execution is Michael's choice and is not assumed.

### Q5. What outside this team could hold the work up?

[Answer]: Mainly Michael's own approvals and account setup. There are no external teams. The full list is in `external-dependency-map.md`, with an owner, lead time, the Bolt it blocks, and a fallback for each. The most material items:
- the one-time AWS bootstrap: state bucket, OIDC provider and roles;
- approval to create the `preview` environment;
- the free Auth0 and MongoDB Atlas tenants;
- the GitHub read-only credential;
- the AI provider choice and spending approval;
- authorization to merge Construction pull requests.

### Q6. What is the biggest worry, so it is tackled early?

[Answer]: That a boundary is wrong in a way only found late:
- private material leaking to the public site (NFR2);
- an authorization gap in the Studio (FR1);
- untrusted uploads (FR4.2, FR4.4);
- SSRF in the link check (NFR17);
- a race in publication (ADR-004, ADR-012).

The plan answers this in three ways:
- the contracts and their contract tests come first (U1);
- owner-only access comes first in the back end (U3);
- each sensitive unit carries its invariant tests and an independent security review in its own Definition of Done.

## Per-Bolt Questions

These are answered for every Bolt in `bolt-plan.md`: which units it bundles, whether it is the walking skeleton (none is, under `skeleton: off`), its Definition of Done, what shipping it will tell us, and who owns it.

Team Formation was skipped in the approved `classic`-based plan, so every Bolt is executed by aidlc-developer-agent. The supporting roles are listed in `team-allocation.md`.

## Construction Staffing

### Q7. How should Construction be staffed?

A. From this session: one owner of the workflow state, with the recorded execution settings.
B. Each team owns a unit and approves its work independently.
X. Other (please specify)

[Answer]: A — there is one owner and no separate teams (P-05; team practice, Way of Working: "exactly one agent or harness owns that state at any time"). Unit ownership stays at its default, solo.

## Assumptions & Open Questions

- **Verification command.** The repository has no runnable check yet. It is greenfield, with no application code. So no Construction verification command is proposed now: the field stays unset, and the first unit checkpoint asks Michael to choose one. Leaving it unset is not an approval of anything.
- **Construction autonomy.** Whether Construction continues automatically or stops at each checkpoint is offered when Construction starts (team practice: `skeleton: off`). It is not assumed here.
