# ADR-012: A confirmation is bound to the exact reviewed revision and inventory

- **Status:** Accepted — approved by Michael Broadfoot at the Domain Design gate, 2026-10-11.
- **Source of record:** `aidlc/spaces/default/intents/261010-architect-portfolio/inception/domain-design/decisions.md`. Component names refer to `components.md` in the same folder.

- **Context**
  - Nothing may become public except through the owner's explicit confirmation of exactly what the confirmation listed (FR7.1, FR7.2, D-22).
  - Preparation and confirmation happen at different moments, and the owner may have the editor open in another tab (FR3.4).
  - The architecture review (R-01) found the first draft did not tie the confirmation to what was reviewed. The owner required three things (Request Changes, 2026-10-11):
    - the confirmation is bound to the exact reviewed revision and inventory;
    - a stale confirmation is rejected and the owner reviews again;
    - the revision check is atomic with accepting the operation.
- **Decision**
  - **Preparation.** Preparing Publish or Update reads draft revision N and freezes, at that moment, two things:
    - the candidate PublishedVersion projected from revision N;
    - the complete inventory shown to the owner, including check results, visibility and attachment entries.

    Both go into a single-use ConfirmationTicket with an expiry and a digest of the inventory. Every ticket records its basis, the public state it was prepared against:
    - the exhibit's last accepted operation, counting operations accepted but not yet run;
    - for featured changes, the published featured order version and the set of live featured exhibits.

    A featured-order ticket also freezes the exact candidate order shown and binds to the draft line-up revision. Every line-up change increments that revision, including a slot released by take-down.
  - **Acceptance.** The confirmation sends the ticket id, the inventory digest that was displayed, and a confirmation id generated once per confirmation. A repeat of the same confirmation returns the accepted operation, while a different confirmation presenting a used ticket is refused. In one atomic step, Publication:
    1. checks that the ticket is unused, unexpired and of the right kind, that the digest matches, and that the exhibit's last accepted operation still equals the ticket's basis;
    2. calls the Projects revision guard. The guard succeeds only if the draft revision is still N. It records the accepted operation by a conditional write to the project record, without changing the revision, so a concurrent save conflicts with it. Publishing then shows "Published", and a later save shows "Changes since last publish". Every saved draft change, including images, attachments, category, featured flag and rights flags, increments the revision;
    3. for a featured-order ticket, calls the Projects line-up guard in place of the revision guard. The guard succeeds only if the line-up revision is unchanged, and records the acceptance in the line-up's `publicationGuard` by a conditional write that does not change the revision;
    4. marks the ticket used;
    5. takes the next sequence number and records the PublicationOperation.

    If any check fails, nothing is accepted. The owner sees that the exhibit changed since review and prepares again.
  - **What is published.** The operation publishes the ticket's frozen candidate version (its `sourceRevision` always equals N), or for a featured-order ticket its frozen candidate order. Preconditions that depend on public state are re-checked when the operation runs (ADR-004).
  - **Mechanism.** NFR Design chooses it, for example one database transaction spanning the guard and the operation insert, with each component writing only its own records.
- **Consequences**
  - Positive:
    - a stale confirmation is always refused;
    - because the candidate is frozen at preparation, even a mechanism failure could not publish content the owner did not see;
    - an edit that lands just after acceptance stays private, and the status correctly becomes "Changes since last publish" (ADR-003);
    - repeated confirmations of one ticket are idempotent (ADR-004).
  - Negative:
    - the owner must re-prepare after any edit, which is intended;
    - tickets and frozen candidates add stored records;
    - the atomic step spans two components' records, so their persistence must support it.
- **Alternatives Rejected**
  - **Re-project the draft at confirmation time:** content edited after review could be published.
  - **Check the revision only, without freezing the candidate:** this relies wholly on the atomic check, with no second line of defence.
  - **Lock the project against edits while a confirmation is open:** the owner could be locked out by an abandoned tab. Optimistic refusal with re-review is simpler and never blocks editing.
