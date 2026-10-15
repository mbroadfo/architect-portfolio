# ADR-011: StudioApi enforces ownership on every request and composes cross-component flows

- **Status:** Accepted — approved by Michael Broadfoot at the Domain Design gate, 2026-10-11.
- **Source of record:** `aidlc/spaces/default/intents/261010-architect-portfolio/inception/domain-design/decisions.md`. Component names refer to `components.md` in the same folder.

- **Context**
  - Every Studio operation must be authorized on the server (FR1.2). Ownership is matched on issuer and subject, never email (FR1.1).
  - Some flows span components. Implemented as direct calls, they would create cycles:
    - Discover joins repositories with their project links (FR2.1, FR2.3);
    - inserting a suggestion records its provenance in Projects (FR5.2, FR7.2).
  - Rate limits apply to several endpoints (NFR16).
- **Decision**
  - **StudioApi** calls OwnerAccess before any operation and applies rate limits before any provider call, upload authorization or link check. It composes:
    - Discover, by listing from RepositoryCatalog and looking up links in Projects;
    - suggestion insertion, by reading provenance from DescriptionAssistant and saving it through Projects;
    - status listing, from Projects and Publication.
  - **Health endpoint.** The single unauthenticated route is `GET /health`. It is rate-limited, reads no domain data, and returns a fixed status body with no version, configuration, project or owner information. Every other route requires the owner.
  - **OwnerAccess** is a small, separately reviewed component that holds no data.
- **Consequences**
  - Positive:
    - the dependency graph stays acyclic;
    - the owner-only invariant test has one place to target;
    - domain components stay free of HTTP and identity concerns.
  - Negative: StudioApi carries some orchestration logic, which must stay thin; business rules belong to the domain components.
- **Alternatives Rejected**
  - **Each component checks authorization itself:** the rule would be duplicated, and an endpoint could miss it.
  - **Direct calls between components:** Projects → DescriptionAssistant and RepositoryCatalog → Projects would form cycles.
