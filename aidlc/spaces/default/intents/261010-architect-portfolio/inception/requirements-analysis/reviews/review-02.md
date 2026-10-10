## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-10-10T18:50:25Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/261010-architect-portfolio/inception/requirements-analysis/requirements.md > FR1.1 | "The single configured owner identity" does not say how the owner is identified. Matching on an email address, or leaving self-signup open on the Auth0 tenant, could let someone else claim the owner identity. This is the main gate for the whole Studio. | State that the owner is matched on the identity provider's immutable subject ID (or a verified email), that self-signup is disabled on the tenant, and add a Given/When/Then for an unverified or look-alike identity being refused. | Resolved (reviewer) |
| R-02 | Major | aidlc/spaces/default/intents/261010-architect-portfolio/inception/requirements-analysis/requirements.md > FR4.2, FR4.4 | Owner-uploaded workshop and CAD photos become public as-is. No requirement strips EXIF metadata (GPS location, device, timestamps), which contradicts the "nothing private becomes public unintentionally" principle (charter §4, §5; D-22). The publish confirmation (FR7.2) lists images but not their hidden metadata. Public downloads (ZIP, STL, SKP) also have no content-type or no-execute rule. | Add a requirement that published image derivatives have EXIF and location metadata removed, with a testable check (a published image contains no GPS tags). Add that uploaded files are validated by actual content type, not file extension alone, and served as downloads with a fixed content type. | Resolved (reviewer) |
| R-03 | Minor | aidlc/spaces/default/intents/261010-architect-portfolio/inception/requirements-analysis/requirements.md > NFR3, FR2.2 | The GitHub credential that can read private repositories is the most sensitive secret in the system, but NFR3 does not list it and FR2.2 does not say what kind of credential it is. | Add the GitHub credential to the NFR3 secret list (SSM SecureString, least privilege). Say it is read-only and repository-scoped (for example a fine-grained token or GitHub App). Leave the choice between them to design. | Resolved (reviewer) |
| R-04 | Minor | aidlc/spaces/default/intents/261010-architect-portfolio/inception/requirements-analysis/requirements.md > FR4.2, FR4.4 | The 10 MB and 50 MB upload limits sit above typical API gateway and Lambda payload limits. A requirement that cannot be met through the API path is a design risk that will surface late. | Add a note that uploads go directly to storage (for example pre-signed URLs), with the same server-side owner check and type and size validation, or flag it as a design question. | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/261010-architect-portfolio/inception/requirements-analysis/requirements.md > FR5.1, FR5.4 | Private repository text is sent to a third-party AI provider. The requirements cover prompt injection (FR5.6) but not the provider's data handling. Q2 originally raised this and it was not carried forward. | Add that the chosen provider must not train on submitted content, and that the owner is told at approval time which provider receives repository text. | Resolved (reviewer) |
| R-06 | Minor | aidlc/spaces/default/intents/261010-architect-portfolio/inception/requirements-analysis/requirements.md > FR3.2, FR7.6, FR8 | Status transitions are not fully defined. For example, can "Taken down" go to "Published" directly? What happens if a publish and a take-down race, or if an edit is saved during a publish? | Add a short transition list and one criterion for concurrent publish and take-down (the last confirmed owner action wins, and the result is consistent). | Resolved (reviewer) |
| R-07 | Minor | aidlc/spaces/default/intents/261010-architect-portfolio/inception/requirements-analysis/requirements.md > NFR10 | The nightly export holds drafts and text drawn from private repositories, but the requirement does not say the storage is private and encrypted. | State that the export bucket is private, encrypted and never served by the public distribution, and add it to the NFR2 invariant tests. | Resolved (reviewer) |
| R-08 | Minor | aidlc/spaces/default/intents/261010-architect-portfolio/inception/requirements-analysis/requirements.md > NFR1, FR4.5 | There is no requirement for security response headers (a content security policy) on the public site and the Studio. There is also no brute-force or rate protection on Studio endpoints and AI requests, which cost money. | Add a measurable header baseline and a per-owner rate limit on AI and upload endpoints. A design-level decision on the specifics is enough. | Resolved (reviewer) |

> R-01 Reviewer note: FR1.1 now matches the owner on the Auth0 issuer plus immutable subject ID and says email never establishes ownership. Public self-registration is disabled. Given/When/Then covers a look-alike email with a different subject (403), a wrong issuer, an unverified, expired or malformed token, and the sign-up page.

> R-02 Reviewer note: FR4.2 validates uploads by file signature and requires re-encoded derivatives with EXIF, GPS and other metadata removed, with a testable criterion. FR4.4 validates files against an allow-list and serves downloads with a fixed content type, `Content-Disposition: attachment` and `nosniff`, each with a criterion.

> R-03 Reviewer note: FR2.2 requires a read-only, repository-scoped credential (fine-grained token or GitHub App, chosen in design) and has a write-refused criterion. NFR3 lists the GitHub credential under runtime secrets in SSM SecureString with least-privilege IAM.

> R-04 Reviewer note: New FR4.8 sends uploads directly to private storage through short-lived, single-use authorizations that bind the size and type limits, are issued only to the owner, and are re-checked server-side. It has an expiry, oversize and non-owner criterion.

> R-05 Reviewer note: FR5.9 requires owner approval of a provider for private content based on its data-use terms (no training, stated retention). The Studio names the receiving provider before each request and records it. Two criteria cover an unapproved provider and the named-provider panel.

> R-06 Reviewer note: The FR3.2 transition table and FR7.8 serialize publication operations so the last owner action determines public state. FR7.8 has a publish-then-take-down criterion and a partial-failure criterion. FR8.4 states that take-down cannot withdraw copies already downloaded or cached elsewhere, with a confirmation criterion.

> R-07 Reviewer note: NFR10 makes the export and upload storage private, public-access-blocked and encrypted, and never a distribution origin. NFR2 includes the export in the invariant tests, with a 403/404 check on original uploads and export objects.

> R-08 Reviewer note: NFR15 sets a measurable header baseline (CSP, HSTS of at least one year, nosniff, Referrer-Policy) verified in smoke tests and preview. NFR16 requires 429 rate limits on the AI, upload-authorization and sign-in endpoints, with the rates left to NFR Design, and has a criterion.

### Summary

All eight prior findings are fixed. Each now has a stated requirement and a testable Given/When/Then or measurable criterion, and the revision stays inside the settled release scope. The revision introduced no substantive new gaps. Engineering can start from this document without coming back with questions.
