# ADR-005: The link checker is stateless and isolated; Publication keeps its results

- **Status:** Accepted — approved by Michael Broadfoot at the Domain Design gate, 2026-10-11.
- **Source of record:** `aidlc/spaces/default/intents/261010-architect-portfolio/inception/domain-design/decisions.md`. Component names refer to `components.md` in the same folder.

- **Context** — NFR17 requires the check to run where a bypass reaches no private network, AWS-internal endpoint, secret or database, "under an execution identity with no other permissions". FR10.5 requires the result to be recorded with its time and shown in the Publish confirmation.
- **Decision** — LinkChecker has no dependencies, no storage and no secrets: a URL goes in and one labelled result comes out. Publication calls it while preparing a confirmation, one live URL per exhibit, and stores the result as a LinkCheckRecord. The record is never exported (FR4.10 allow-list).
- **Consequences**
  - Positive: the component can be deployed on a zero-permission identity with public-only egress, and a successful SSRF bypass finds nothing of value.
  - Negative: the result has to travel back to Publication instead of being written in place.
- **Alternatives Rejected**
  - **The checker stores its own results:** it would need database credentials, contrary to NFR17.
  - **Running the check inside Publication:** Publication's identity has database access.
