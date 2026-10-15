# ADR-004: One site-wide, fenced sequence for every operation that changes public pages

- **Status:** Accepted — approved by Michael Broadfoot at the Domain Design gate, 2026-10-11.
- **Source of record:** `aidlc/spaces/default/intents/261010-architect-portfolio/inception/domain-design/decisions.md`. Component names refer to `components.md` in the same folder.

- **Context**
  - Publish, update and take-down of any exhibit, and "Update featured order", all rewrite shared public pages: the home page, carousel, category pages and counts (FR7.4, FR8.2, FR9.7).
  - Operations for one exhibit must run in confirmation order, and the public state must always equal the last successful action (FR7.8).
  - Operations must be safe to repeat (FR7.6) and complete on the public site within 5 minutes (FR7.4, FR8.2).
  - The first draft serialized operations per exhibit only. The architecture review (R-02) showed that two exhibits' operations could then build shared pages from stale views, so a taken-down exhibit could reappear on the home page. The owner required every shared-page operation to be serialized across projects (Request Changes, 2026-10-11).
- **Decision**
  - **One sequence.** Every accepted publication operation gets the next number in one site-wide sequence. Operations run one at a time in that order, whatever exhibit they concern. This also keeps each exhibit's operations in confirmation order.
  - **Fresh start for each run.** Each run starts from the last committed public state (its base generation), applies its own change, builds the complete public site model, and exports the exhibit's objects and every shared page the change affects.
  - **Run-time basis check.** When an operation starts, every operation accepted before it has committed or failed. It re-checks its state-dependent preconditions against that committed state, and if any no longer holds it fails as "basis changed — review again", with no public change:
    - the action is legal for the exhibit's publication state;
    - the carousel limit holds;
    - for "Update featured order", the published order version and the set of live featured exhibits equal its basis.

    The acceptance check of the ticket's basis (ADR-012) refuses early; this check is the guarantee.
  - **Attempts, leases and fencing.** Every attempt (first run, automatic retry or manual retry) takes a lease on the sequence and a new token from a strictly increasing site-wide counter.
    - The lease outlasts the attempt's maximum execution time, and an attempt starts only after the previous lease has expired or been released, so two attempts never run at once.
    - PublicSiteExporter records the highest accepted token in a site-wide fence that is never deleted, and refuses any write with a lower token, so a stalled attempt cannot overwrite newer state or recreate a withdrawn object. The fence and the exporter's other records live in a private store, never in public storage.
    - Because each manual retry gets a fresh token, tokens used by later operations never block it.
  - **Commit.** After a successful export, one transaction commits, only if the attempt's token still holds the lease and the site generation still equals its base generation:
    - the new publication records and featured order;
    - the next site generation;
    - the ActivityEntry;
    - for a take-down, the release of the draft featured slot through Projects.
  - **Idempotency.** A repeated confirmation of the same ticket returns the operation already accepted. A retry re-runs that same operation, and only when no later operation for the same exhibit has succeeded; otherwise it is marked superseded.
  - **Failure.** A failed operation restores public storage to the last committed generation and is shown with a retry.
  - **Abandoned attempts.** An attempt can stop without reporting (a crash, or a timeout past its lease). When its lease expires without a commit or a completed restore, a recovery attempt runs before anything else. Lease expiry triggers it, backed by a periodic check, so it never waits for a later operation. The recovery attempt takes a new lease and a higher token, marks the abandoned attempt failed, and restores public storage to the last committed model. An abandoned attempt counts as one of its operation's attempts, including against a take-down's automatic-attempt budget.
  - **Retry window.** A manual retry of a Publish, Update or featured-order operation is allowed only while its ticket is unexpired; after that the owner prepares again. A take-down retry is always allowed. A failed take-down that a later Publish or Update supersedes is marked superseded. That confirmation warns that the exhibit stays public. A failed take-down is retried automatically, ahead of later operations, a bounded number of times. Once those attempts are exhausted it is marked failed, releases the lease and the sequence moves on, so the queue is never blocked. The Studio then shows a persistent "Take-down failed — still public" alert with a manual retry (FR8.1).
  - **Five minutes.** NFR Design sets the per-attempt time budget and the number of automatic take-down attempts so that an operation, the work queued ahead of it and its automatic attempts finish within 5 minutes. With a single owner the queue stays short. An operation that still fails is restored and reported as failed, never as complete.
  - **Mechanism.** The queue, lease and fencing implementation are chosen in NFR Design. The properties above are fixed here.
- **Consequences**
  - Positive:
    - no shared page can be built from a stale view;
    - no stale run can overwrite newer state;
    - every completed state equals the last successful operation;
    - preconditions that depend on public state are re-checked against the state the operation actually runs on;
    - retries and double clicks are harmless;
    - the activity log and the site generation come from the same commit.
  - Negative:
    - unrelated exhibits wait for each other, which is acceptable for one owner;
    - each operation re-exports shared pages, a few small static files.
- **Alternatives Rejected**
  - **Per-exhibit queues (the first draft):** shared pages could be written from stale views (review R-02).
  - **The sequence number as the fencing token (the second draft):** a retry could not be told apart from the stalled attempt it replaced, and a retry after later operations would have been blocked. Tokens are therefore per attempt.
  - **Concurrent operations with last-writer-wins:** violates FR7.8.
  - **Per-exhibit queues plus a lock only around shared-page writes:** this also works, but it needs two coordination mechanisms. The order in which shared pages are written would then differ from the order in which operations were accepted. One sequence is simpler and gives a single, auditable order.
