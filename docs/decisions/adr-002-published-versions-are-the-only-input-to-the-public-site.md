# ADR-002: Published versions are the only input to the public site

- **Status:** Accepted — approved by Michael Broadfoot at the Domain Design gate, 2026-10-11.
- **Source of record:** `aidlc/spaces/default/intents/261010-architect-portfolio/inception/domain-design/decisions.md`. Component names refer to `components.md` in the same folder.

- **Context**
  - Nothing private may become public without the owner's approval of that exact content (charter §4, §5; D-22; NFR2).
  - The export may contain only allow-listed fields (FR4.10).
  - Re-exported pages must use the last published state of every exhibit (FR7.4).
  - At the 2026-10-11 Request Changes, the owner rejected a prototype in which unapproved data was loaded and merely hidden. The owner then approved an explicit approved-publication snapshot (Refined Mockups P4; P-06).
- **Decision** — Publication freezes a **PublishedVersion** at each confirmed Publish or Update. It is an immutable projection of one project revision containing only allow-listed public fields:
  - text;
  - images with alt text;
  - included attachments;
  - links;
  - derived badge labels;
  - the live URL, if included and authorized;
  - repositories confirmed public, with their licence;
  - primary category and featured flag.

  The candidate version is projected from the reviewed draft revision when the confirmation is prepared, and it is the version published if the confirmation is accepted (ADR-012).
  - **Public site model.** Publication is its only builder. The model contains:
    - the current PublishedVersion of every live exhibit;
    - the PublishedFeaturedOrder;
    - the categories derived from those versions.

    Each version freezes its primary category with slug, name and position, so the model never reads Projects' reference data. SiteRenderer and PublicSiteExporter receive only this model and have no access to Projects or to any private record.
  - **Repositories.** They reach a PublishedVersion only as repositories confirmed public at preparation, with their licence. A free-form link that points at a repository host blocks Publish (FR4.3).
  - **Confirmation evidence.** The check results, private repository names and attachment metadata the owner was shown are kept in the ConfirmationTicket, never in the PublishedVersion.
- **Consequences**
  - Positive:
    - the boundary is structural, not a filter, so a mistake in rendering cannot leak a draft;
    - the export-scan invariant tests (NFR2) have one, small input type to reason about;
    - the prototype's approved model carries straight into the design.
  - Negative:
    - content is stored twice (draft and published); this is a negligible cost at this scale;
    - renaming a category, a roadmap item, will need a site-wide republish, because names are frozen into versions.
- **Alternatives Rejected**
  - **Filtering the live project record at export time:** unapproved data would reach the export code path, which is exactly the failure the owner rejected.
  - **Copying public fields into the project record:** this mixes approved and draft state in one record with two writers.
