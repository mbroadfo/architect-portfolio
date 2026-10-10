# User Flows — Architect's Portfolio, First Release

Inputs: `intent-statement` (audiences), `scope-document` (value stream, publish boundary), `intent-backlog` (IB references below), and `wireframes.md` (screen IDs P1-P2, S1-S6).

## Flow 1 — Owner turns a repository into a published exhibit

Persona: Michael (curator). Trigger: a project worth exhibiting exists on GitHub.

```
[S1 Sign in] --> [S2 Projects] --> [S3 Discover repo]
                                         |
                       +-----------------+-----------------+
                       |                                   |
                 create project                     link to existing
                       |                                   |
                       +-----------------+-----------------+
                                         v
                               [S4 Exhibit editor]
                                 |      ^      |
                     suggest ----+      |      +---- write / add images,
                     (AI panel)  insert/edit         links, build files
                                         |
                                         v
                                   [S5 Preview]
                                    |       |
                         back to editor     looks right
                                            |
                                            v
                                 [S6 Publish confirmation]
                                    |               |
                                 Cancel          Publish
                                    |               |
                         back to editor        exhibit live
                                               (P1 card + P2 page)
```

<!-- Text fallback: Sign in, go to Projects, Discover a repository, then either create a project or link to an existing one. Both lead to the Exhibit editor, where the owner writes content, adds images, links and build files, and can ask for an AI suggestion to insert and edit. From the editor, Preview; from Preview, go back to edit or continue to the Publish confirmation. Cancel returns to the editor; Publish makes the exhibit live as a gallery card and an exhibit page. -->

| Step | Screen | Owner action | System response | Backlog |
|------|--------|--------------|-----------------|---------|
| 1 | S1 | Sign in | Studio opens; anyone else is refused | IB-1 |
| 2 | S2 | Discover repo | Repository list, private ones labelled | IB-3 |
| 3 | S3 | Use a repository | New draft project, or link added to an existing one | IB-4 |
| 4 | S4 | Write sections, add images, links, build files; Save | Saved status shown | IB-5 to IB-8 |
| 5 | S4 | Suggest description | Suggestion with its source files; nothing overwritten | IB-9 |
| 6 | S5 | Preview | Exhibit and gallery card exactly as visitors will see them, marked "not public" | IB-10 |
| 7 | S6 | Publish | Summary of what becomes public, private-repo warning, explicit confirm | IB-2, IB-11 |
| 8 | P1/P2 | — | Exhibit appears in the gallery and on its own page | IB-12, IB-13 |

**Error paths**

- GitHub unreachable at step 2: says so, offers retry; existing projects untouched.
- AI suggestion fails at step 5: says so; text unchanged; retry offered.
- Session expires during step 4: sign in again and return to the editor with work kept.
- Publish blocked at step 7 (empty title, missing alt text): the button stays disabled and the reason is shown.

Success outcome: the exhibit is live, and S2 shows it as "Published".

## Flow 2 — Owner updates or withdraws a published exhibit

Persona: Michael. Trigger: a published exhibit needs a change, or should come down.

```
[S2 Projects] --> [S4 Exhibit editor] --> [S5 Preview] --> [S6 Update public exhibit]
       |
       +--> [Take down] --> confirm naming the exhibit --> P2 shows "not on display"
```

<!-- Text fallback: From Projects, open the exhibit editor, change it, preview, then confirm "Update the public exhibit". Alternatively choose Take down from the project, confirm by name, and the public page then shows that the exhibit is not on display. -->

- Edits to a published exhibit stay private until the owner confirms the update; S2 shows "Changes since last publish" meanwhile. [scope-document: nothing becomes public without an explicit act]
- Take down is a Should Have pending Requirements Analysis. [intent-backlog IB-16]

## Flow 3 — Visitor explores the work

Personas: a prospective client or employer, a fellow engineer, a maker. Trigger: arrives at michael.broadfoot.consulting, or at mike.broadfoot.consulting and is redirected.

```
[P1 Gallery] --> pick a card --> [P2 Exhibit page]
                                   |      |       |
                          summary  |  narrative   |  build it yourself
                          + links  |  sections    |  downloads
                                   v
                           < All work --> [P1 Gallery]
```

<!-- Text fallback: The visitor lands on the gallery, picks an image card, and reads the exhibit page: the summary and links, the narrative sections, or the build-it-yourself downloads, depending on their interest. A back link returns to the gallery. -->

| Visitor | Reads first | Then | Source |
|---------|-------------|------|--------|
| Client or employer | Lead image, summary, outcomes | Links to live work | intent-statement |
| Fellow engineer | Architectural decisions, implementation | View code | intent-statement |
| Maker | Gallery images | Build it yourself downloads | intent-statement |

- Error path: an unknown or withdrawn exhibit address shows "This exhibit isn't on display" with a link to all work.
- No account, sign-in, cookie banner or tracking appears anywhere in this flow. [scope-document]

## Assumptions & Open Questions

- The visitor flow assumes no search or filtering in the first release, per the approved scope (richer gallery features are on the roadmap). [assumption]
- Flow 2's take-down step depends on Requirements Analysis confirming IB-16. [assumption]
