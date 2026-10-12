# Reliability Design — U0 walking-slice

**Inputs:**
- U0 NFR requirements: `../nfr-requirements/`;
- functional design: `../functional-design/`;
- contract-summary (C2, C9, C11);
- components;
- team-practices;
- `nfr-design-questions.md`.

U0 is the delivery-only walking slice. S0 merges to `main`; S1 to S3 run only on the local stack.

## Design

| ID | Design |
|---|---|
| REL-0.1 | **Database.** MongoDB runs as a single-node replica set (`mongod --replSet rs0`), initiated by a one-shot container with a health check. `SliceProject` carries `currentVersionId`, which makes concrete the functional design's "current published version" relationship. The database is the source of truth.<br>**Publish sequence.**<br>(1) Publishes are serialized in the single API process by one asynchronous lock.<br>(2) Take the timestamp T. Render the snapshot, with `publishedAt` = T, into `releases/<versionId>/`.<br>(3) In one `with_transaction`, make a compare-and-set update `update_one({_id, revision: N, currentVersionId: prev}, {$set: {currentVersionId: versionId}})`, where a matched count other than 1 aborts with 409 `STALE_REVISION`, and insert the version with `publishedAt` = T. T is the timestamp recorded with the committed version, which is what the functional design calls "the commit time".<br>(4) After the commit, if the stored `currentVersionId` is still this version, swap the `public` symbolic link atomically (create a temporary link, then rename it over `public`). The link target is **relative** (`releases/<versionId>`), because the API and nginx mount the volume at different paths. `public` is always a link, never a real directory, from the initial state onward.<br>(5) If the swap fails, a conditional compensation (`{_id, currentVersionId: versionId}` set back to `prev`) restores the database and removes the version and its release. If the compensation itself fails, it is logged, and reconciliation repairs the state.<br>**Reconciliation.** At API start-up and before every Publish, the API compares the `public` target with the database's `currentVersionId`. On any difference it re-points `public` to the release of `currentVersionId`, re-rendering from the stored snapshot if the release is missing. A crash at any point therefore converges on the database state.<br>**Initial state.** `public` points to `releases/empty/`, a placeholder page "New work is being installed." Old releases are pruned to the last three |
| REL-0.2 | `make slice-check` starts from an empty database volume and the fixture, so nothing durable is kept |
| NFR11.2 | The health route `GET /health` answers `{"status":"ok"}` with no dependency checks, so it cannot leak state |

## Assumptions & Open Questions

- The production designs for these concerns belong to the owning units' NFR Design.
