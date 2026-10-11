# ADR-007: A provider-independent description assistant; provider chosen later

- **Status:** Accepted — approved by Michael Broadfoot at the Domain Design gate, 2026-10-11.
- **Source of record:** `aidlc/spaces/default/intents/261010-architect-portfolio/inception/domain-design/decisions.md`. Component names refer to `components.md` in the same folder.

- **Context**
  - FR5.4 requires a provider-independent interface with server-side adapters on an open framework.
  - Spending needs the owner's approval and a monthly limit (FR5.8).
  - Private repository content may go only to a provider approved for it (FR5.9).
  - The Publish confirmation must show AI-originated text and the private repositories that informed it (FR7.2).
  - The provider choice depends on its cost per call, which NFR Design establishes before the owner approves spending.
- **Decision** — DescriptionAssistant owns:
  - the provider port and its adapters;
  - AiSpendPolicy, AiProviderApproval and AiUsageMonth;
  - Suggestion records with source files, source repositories and provider.

  When the owner inserts a suggestion, StudioApi passes the suggestion's recorded provenance to Projects, which stores a TextProvenance record with the edited field. The provider and framework are chosen in NFR Design.
- **Consequences**
  - Positive:
    - providers can be swapped by configuration;
    - the approvals are checked in one place before any call;
    - provenance survives editing and reaches the Publish confirmation.
  - Negative: provenance is recorded per field, not per sentence. Text inserted and then rewritten is still reported as AI-originated, which is the conservative direction.
- **Alternatives Rejected**
  - **Choosing a provider now:** this needs cost data and owner spending approval that Domain Design cannot give.
  - **No provenance record:** FR7.2 could not be met.
