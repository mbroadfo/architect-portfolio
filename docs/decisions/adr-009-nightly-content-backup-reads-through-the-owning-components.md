# ADR-009: Nightly content backup reads through the owning components

- **Status:** Accepted — approved by Michael Broadfoot at the Domain Design gate, 2026-10-11.
- **Source of record:** `aidlc/spaces/default/intents/261010-architect-portfolio/inception/domain-design/decisions.md`. Component names refer to `components.md` in the same folder.

- **Context**
  - NFR10 requires a nightly export of Studio content to private, versioned, encrypted storage, with a tested restore.
  - The free database tier has no automated backups.
  - Uploaded files are already in versioned storage.
- **Decision** — ContentBackup asks Projects, MediaLibrary, DescriptionAssistant and Publication for their records and writes one export. The scheduling and tooling are chosen in NFR Design and Infrastructure Design.
- **Consequences**
  - Positive: entity ownership is preserved, and the export format does not depend on the storage layout.
  - Negative: each owner exposes an export function.
- **Alternatives Rejected**
  - **A database-level dump job outside the component model:** simpler, but it bypasses ownership and ties restore to the storage layout. NFR Design may still choose it as the mechanism, provided restore is tested; this ADR would then be revised.
