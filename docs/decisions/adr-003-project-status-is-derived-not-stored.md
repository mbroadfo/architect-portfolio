# ADR-003: Project status is derived, not stored

- **Status:** Accepted — approved by Michael Broadfoot at the Domain Design gate, 2026-10-11.
- **Source of record:** `aidlc/spaces/default/intents/261010-architect-portfolio/inception/domain-design/decisions.md`. Component names refer to `components.md` in the same folder.

- **Context**
  - FR3.2 defines four statuses and their allowed transitions.
  - FR7.5 and FR7.8 require two things:
    - an edit saved while a publication operation runs is excluded from it and leaves "Changes since last publish";
    - edits to a taken-down exhibit stay private.
  - A stored status would be written by both Projects (on save) and Publication (on publish and take-down).
- **Decision** — Projects keeps a draft revision that increments on every save. Publication keeps a PublicationRecord: state (never published, live, taken down) and the revision of its current PublishedVersion. Publication derives the status:

  | State | Revision | Status |
  |---|---|---|
  | never published | any | Draft |
  | live | draft = published | Published |
  | live | draft > published | Changes since last publish |
  | taken down | any | Taken down |
- **Consequences**
  - Positive:
    - one writer per fact;
    - FR3.2's transitions and FR7.8's concurrency rule hold by construction;
    - status itself needs no cross-component transaction. The atomic acceptance and commit steps (ADR-012, ADR-004) exist for publication, not for status.
  - Negative: listing statuses needs both components, which StudioApi composes.
- **Alternatives Rejected**
  - **A stored status field updated by both components:** two writers, a race between save and publish, and a cross-component transaction.
