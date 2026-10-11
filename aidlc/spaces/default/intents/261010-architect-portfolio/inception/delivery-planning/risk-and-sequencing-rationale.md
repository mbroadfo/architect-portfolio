# Risk and Sequencing Rationale

**Inputs:**
- unit-of-work-dependency (the approved dependency graph);
- unit-of-work;
- components (the scenarios CS and PB);
- contract-summary;
- requirements;
- team-practices;
- the answers in `delivery-planning-questions.md`.

A **Bolt** is one build pass over part of a unit of work, ending in working, tested code merged through one pull request. This document explains why the 30 Bolts in `bolt-plan.md` are in that order.

## The Approach: Dependency First, Then Risk First, With a Light Tie-Breaking Score

1. **The approved dependency graph sets the order.** Construction runs one unit at a time, and the engine walks the units in the graph's order. Units can only start once what they depend on exists. So the order of units follows the graph, and no deviation from topological order is proposed.
2. **Within each set of ready units, risk first.** The design concentrates risk in four boundaries (ADR-001):
   - owner-only access;
   - untrusted uploads;
   - SSRF-safe link checks;
   - the publication boundary, including its concurrency rules (ADR-002, ADR-004, ADR-012).

   Building the contracts first, and putting OwnerAccess at the start of the back end, means a mistake in a boundary is found when it is cheap to fix. This follows Cohn's advice to sequence by risk and by the knowledge gained, and the "risk reduction" term of WSJF (Weighted Shortest Job First, Reinertsen and SAFe).
3. **Within each unit, the thinnest piece that runs end to end comes first.** Team practice names four early proofs, and each lands as early as the graph allows:
   - CI plans with OIDC (B04);
   - the Terraform plan is clean (B04);
   - the API answers a health check (B06);
   - the public page builds and is served (B20).
4. **Ties are broken with a light score:** (value + time criticality + risk reduction) ÷ size, each scored from 1 to 5. Only ties among ready units use it.

## Unit Order and Its Justification

| Position | Unit | Why here |
|---|---|---|
| 1 | U1 contracts | Has no dependencies, and every other unit builds against it. It fixes the publication allow-list (C2) and the R-07 and R-08 tests early: the highest risk reduction for its size |
| 2 | U2 platform | Has no dependencies. Proves OIDC and a clean plan. It is the foundation every service deploys onto, and the first Bolts that depend on Michael's bootstrap (E1) |
| 3 | U3 studio-api | Every back-end module and U11 depend on it. OwnerAccess (B07) is the authorization boundary for everything after it |
| 4 | U4 media-library | Ready after U3. The untrusted-file boundary; U9 and U10 need it |
| 5 | U5 description-assistant | Ready after U3. Small, and built with a fake provider, so it spends nothing (FR5.8). Its real provider waits on E6 anyway |
| 6 | U6 link-checker | Ready after U1 and U2. The SSRF boundary; U9 needs it |
| 7 | U7 site-renderer | Ready after U1. Reproduces the approved design from the snapshot; U8 and U11 need it |
| 8 | U8 site-publisher | Ready after U7. Enforces R-07; U9 needs it. Its last Bolt is the "public page is served" proof |
| 9 | U9 publication | Needs U3, U4, U6 and U8. The largest unit and the publication boundary. Its five Bolts follow ADR-012, then ADR-004, then recovery, then the snapshot |
| 10 | U10 content-backup | Needs U9, U5 and U4. Small, and needed before launch, not before publishing works |
| 11 | U11 studio-web | Needs U3 and U7. Built last, so it integrates against real endpoints for every flow. Its end-to-end journeys (B30) verify the whole loop |

**Tie-break notes** (from the light score):
- **U4, U5, U6 and U7** are ready together once U1 to U3 exist.
  - Scored on risk alone, the order would be U6, then U4, then U7, then U5.
  - The engine walks the graph in its listed order (U4, U5, U6, U7).
  - The difference does not matter: none of the four depends on another; U5 is small, uses only a fake provider, and spends nothing; and U6 and U4 both come before U9, which consumes them.
  - So no change to the approved graph is proposed.
- **U11 last, not earlier.** Building U11 straight after U3 would show something sooner, but every Studio flow beyond sign-in needs U4, U5 and U9. Built last, U11 has nothing to fake and its end-to-end journeys are real.

## Risks Tackled Early, and Where

| Risk | Where it is retired | Evidence |
|---|---|---|
| The allow-list leaks a private field | B01, B25 | C2 is strict; PB-02 export scan |
| An authorization gap in the Studio | B07 | R-08 registry and spy-handler tests; FR1 criteria |
| Unauthorized storage keys reach the public site | B19, B20 | C3 tests K1 to K18 and P1; IAM test |
| Untrusted uploads | B11, B12 | FR4.2 and FR4.4 criteria; isolated processor |
| SSRF | B15, B16 | NFR17 criteria; zero-permission identity |
| Publication races and crashes | B22 to B24 | CS-01 to CS-20, as deterministic interleaving tests |
| Preview and the live site drift apart | B18 | Node and browser parity test |
| Cost overrun | All | Fakes for paid services in CI (team practice); AI disabled until approved (FR5.8); nothing created without approval |

## Risks That Remain Open

- **Preview does not exist yet (E2).** The 🧪 Bolts cannot merge until it does. This is the main schedule risk. Fallback: build and review those Bolts in sequence; merges queue for E2.
- **Merges are not yet authorized (E10).** Construction work accumulates on Bolt branches until Michael authorizes merging under team practice.
- **Owner content and rights for launch (E9).** These do not block Construction; they block publishing real exhibits.

## Assumptions & Open Questions

- The scores are judgments, and they affect only tie-breaks that the graph already leaves open. The full Bolt sequence is in `bolt-plan.md`; the dependencies are in `external-dependency-map.md`.
