# Entities — U0 walking-slice

**Inputs:**
- unit-of-work (U0);
- components;
- contract-summary (C2);
- requirements;
- `functional-design-questions.md`.

These are **thin, local-only subsets** of entities that other units own: Project (Projects, U3) and PublishedVersion (Publication, U9). The slice keeps only the attributes its path needs. The owning units define the full entities in their own Functional Design, and take over the slice's code through their own Bolts.

## Entity Model

```yaml
entities:
  - name: SliceProject
    description: Thin subset of Project (owned by Projects, U3) for the local slice.
    attributes:
      - { name: projectId, type: identifier, required: true, unique: true }
      - { name: title, type: text, required: true, constraints: "1 to 120 characters" }
      - { name: summary, type: text, required: false, constraints: "up to 1200 characters" }
      - { name: slug, type: text, required: true, unique: true, constraints: "lowercase words joined by hyphens, up to 60 characters; proposed from title" }
      - { name: revision, type: integer, required: true, default: 1, constraints: "increments by 1 on every save" }
      - { name: status, type: enum, required: true, allowed: [Draft, Published, "Changes since last publish"], constraints: "derived, never stored (ADR-003)" }
      - { name: updatedAt, type: timestamp, required: true }
    relationships:
      - { to: SlicePublishedVersion, cardinality: "0..1", direction: "a project has at most one current published version in the slice" }
  - name: SlicePublishedVersion
    description: Thin subset of PublishedVersion (owned by Publication, U9). A frozen, C2-valid projection of one project revision.
    attributes:
      - { name: versionId, type: identifier, required: true, unique: true }
      - { name: projectId, type: reference, required: true, references: SliceProject }
      - { name: sourceRevision, type: integer, required: true, constraints: "equals the project revision reviewed at Publish" }
      - { name: snapshot, type: document, required: true, constraints: "valid against the approved C2 PublicSiteSnapshot 1.0 schema" }
      - { name: publishedAt, type: timestamp, required: true }
  - name: OwnerIdentity
    description: Configuration, not stored data. The single owner's identity-provider issuer and subject; local configuration for the slice.
    attributes:
      - { name: issuer, type: text, required: true }
      - { name: subject, type: text, required: true }
```

**Summary.** There are three entities:
- **SliceProject** carries the draft and its revision.
- **SlicePublishedVersion** is the frozen output of a Publish.
- **OwnerIdentity** is configuration, not stored data.

Status is derived from the revisions, never stored, following ADR-003. The slice has no images beyond one bundled fixture, which is referenced inside the snapshot, and no attachments, links or categories.

## Assumptions & Open Questions

- The fixture image's metadata-free derivative files are committed as test fixtures under the C8 variant rule, so the C2 `Image` fields (`assetRef`, `width`, `height`, `altText`) are real.
