# Risk and Sequencing Rationale (revision 6)

**Inputs:**
- unit-of-work-dependency (the approved dependency graph);
- unit-of-work;
- components (the scenarios CS and PB);
- contract-summary;
- requirements;
- team-practices;
- Michael's Request Changes at the Delivery Planning gate, 2026-10-11:
  - working software as early as possible;
  - less administrative overhead;
  - the same engineering discipline;
- the advisory reviews of revisions 2 to 5, and the consistency check of revision 6.

A **Bolt** is one build pass over part of a unit of work, ending in working, tested code merged through one pull request. A **walking slice** is the smallest piece of real code that runs end to end. This document explains the order in `bolt-plan.md`.

## The Approach

1. **Walking slice first, with CI underneath it and a preview path soon after.** Martin Fowler and Alistair Cockburn recommend building the walking skeleton first: it proves the parts connect and gives working software immediately. S0 lays down the CI that every later pull request depends on, and B05a (M2) makes preview verification real for every 🧪 Bolt.
2. **Then the approved graph, one unit at a time, with the Studio moved earlier.** Construction stays unit-major and serial, so landing per Bolt stays simple and traceable. D1 adds ordering-only edges, so the Studio (U11) is built straight after the renderer it needs.
3. **Risk first wherever the order is open.** The riskiest boundaries come early:
   - owner-only access (U3, M3);
   - SSRF (U6, M4);
   - untrusted uploads (U4, M4);
   - the publication boundary (U8 and U9, M5).
4. **Ties are broken with a light score:** (value + time criticality + risk reduction) ÷ size, in the style of WSJF (Weighted Shortest Job First; Reinertsen, SAFe).

## Why the Slice Is a Unit of Its Own (D1)

Under the current settings (unit-major, serial), the engine builds **each unit completely, one after another**, in dependency order. A slice that crosses U3, U7, U8, U9 and U11 can therefore come first only as its own unit placed first.

| Option | First end-to-end demo | Changes needed | Verdict |
|---|---|---|---|
| **A. Delivery-only unit U0, placed first by ordering-only edges (recommended)** | M1, after the four slice Bolts | Units Generation amendment (D1). The 11 units' boundaries, components and contracts do not change | Recommended |
| B. No new unit; each unit's first Bolt is its slice portion | Only once U9 lands (M5), about 24 Bolts in | None | Too late for the goal |
| C. Engine walking-skeleton mode (`skeleton: on`) plus a slice unit | The same as A | D1, **plus** changing the team practice's "Walking Skeleton" section from scope-dependent to on | A works without the practice change. C would add a formal skeleton checkpoint, which A's verification command already provides |

The edges U1 → U0 and U2 → U0 are **ordering-only**. The slice's real data flow runs the other way: it consumes the approved C2 schema. The edges U4, U5, U6 → U11 are also ordering-only, and put the Studio earlier.

## Build Order and Its Justification

| Order | Unit | Milestone | Why here |
|---|---|---|---|
| 1 | U0 walking-slice | M1 | CI in place, then working software immediately. It proves the package host, renderer, static output, Studio page and allow-list connect |
| 2 | U1 contracts | M2 | Every unit builds against it. It formalises the C2 schema and the R-07 and R-08 tests |
| 3 | U2 platform | M2 | The foundation, OIDC plan and CDN contract, and **B05a, the per-pull-request preview deploy path**. With E2 approved, every 🧪 Bolt from here is verified in preview and merged after approval |
| 4 | U3 studio-api | M3 | The authorization boundary. It replaces the slice's Projects and owner check |
| 5 | U7 site-renderer | M3 | The real public pages and the Node/browser parity proof. It replaces the slice's renderer |
| 6 | U11 studio-web | M3 | **The real Studio user interface, moved from 11th to 6th.** It validates the agreed experience and the C1 contract against the real U3. The Studio calls only real endpoints. Upload, suggestion and publication show "not available yet" until U4, U5 and U9 land. Contract fakes exist only in U11's tests |
| 7 to 9 | U4, U5, U6 | M4 | The untrusted-file and SSRF boundaries, and the AI gates (fake provider, nothing spent). The Studio switches to their real endpoints |
| 10 | U8 site-publisher | M5 | R-07 enforcement, and real public storage writes |
| 11 | U9 publication | M5 | The publication boundary and the concurrency guarantees (CS-01 to CS-20). The slice is retired |
| 12 | U10 content-backup | M6 | Backup and a tested restore before launch |
| — | Build and Test | after M6 | The end-to-end Playwright journeys (formerly B30), which need every unit |

## Why Parallel Engine Execution Is Not Recommended Now

This is summarized in `bolt-plan.md` ("Parallel Execution: Evaluated, Not Recommended Now"). In short:
- the engine's swarm lands **one squash commit per unit**, while team practice needs **one per Bolt**;
- `org.md` fixes the merge target as `main`;
- preview deployments and independent security reviews are serial bottlenecks anyway.

ADR-012 atomicity would be safe under swarm, but traceability and the trunk-based rules would need `org.md` and `team.md` changes. Michael can choose swarm later, with those changes.

## Risks Tackled Early, and Where

| Risk | Where it is retired | Evidence |
|---|---|---|
| No CI to enforce quality and security | S0 (M1) | Aggregate required check, gitleaks, audit, CodeQL, content-bound security-review check |
| "Verify in preview before merge" holds only on paper | B05a (M2) | Per-pull-request preview deploy with smoke checks |
| The pieces do not connect | S1 to S3 (M1) | `make slice-check`: create, save, preview, publish, allow-list scan |
| The fake identity provider leaks into a deployable | S0 (guard); S1 (tests) | Build-time check that it is absent from every non-local artifact |
| The allow-list leaks a private field | S2, B01, B25 | C2 is strict from the slice onward; PB-02 export scan |
| An authorization gap | S1 (thin), B07 (M3) | Unauthenticated rejection from S1; R-08 registry and spy-handler tests in B07 |
| The Studio user experience or contract is wrong | S3, B27 to B29 (M3) | Real Studio against the real U3, and the C1 contract for the rest |
| SSRF | B15, B16 (M4) | NFR17 criteria; zero-permission identity |
| Untrusted uploads | B11, B12 (M4) | FR4.2 and FR4.4 criteria; isolated processor |
| Unauthorized storage keys | B19, B20 (M5) | C3 tests K1 to K18 and P1; IAM test |
| Publication races and crashes | B22 to B24 (M5) | CS-01 to CS-20 interleaving tests |
| The slice lingers as production code | M1 onward | Only S0 merges. S1 to S3 stay on a demonstration branch and are never deployed; their code reaches `main` only through the owning units' reviewed, preview-verified Bolts. The branch is archived at M5 |
| Cost overrun | All | Fakes for paid services; AI disabled until approved; nothing created without approval |

## Risks That Remain Open

- **E1 (AWS bootstrap) is on the critical path for B04 and B05a (M2).** If it slips, B04 is approved-pending-E1 with local validation, and later units continue.
- **E2 (`preview`) gates every 🧪 merge.** Until it is approved and B05a exists (M2), the U1 and U2 Bolts wait in their unit stacks. The slice never merges, so it never waits. That is one of the plan's two deviations from the one-to-two-day branch rule; the other is the `slice/walking-slice` demonstration branch. Security reviews are bound to content, so rebases do not invalidate them.
- **E10 (merge authorization)** is still Michael's.
- **Throughput.** Independent security review sessions are needed for about 27 🔒 Bolts. They are run by the single records owner, one at a time.

## Assumptions & Open Questions

- The order shown assumes the engine resolves the amended graph as listed. Any difference is reported at M1, and the milestones follow the engine.
