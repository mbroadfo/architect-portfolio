# Rough Wireframes — Architect's Portfolio, First Release

Low-fidelity structure only: layout, hierarchy and states, not visual design. The look is the charter's "Engineering Studio" direction (dark navy, precise typography, strong imagery, restrained effects); Refined Mockups turns these into visual designs.

Inputs: `intent-statement` (audiences: clients and employers, engineers, makers), `scope-document` (in and out of scope, image-led gallery refinement), `intent-backlog` (IB-1 to IB-16, IB-18), and `rough-mockups-questions.md`.

## Information Architecture

```
Public site (anyone)                 Studio (owner only, signed in)
+---------------------------+        +---------------------------+
| Gallery home  (/)         |        | Sign in                   |
|   +-- Exhibit page        |        |   +-- Projects            |
|        (/work/<project>)  |        |        +-- Discover repo  |
+---------------------------+        |        +-- Exhibit editor |
                                     |             +-- Preview   |
                                     |             +-- Publish   |
                                     +---------------------------+
```

<!-- Text fallback: The public site has two levels, the gallery home and one exhibit page per published project. The Studio has sign-in, then a projects list, from which the owner discovers a repository or opens an exhibit editor; the editor leads to preview and publish. -->

Every public page is reachable in one click from the gallery. The two sides share no navigation: the Studio is never linked from the public site. [scope-document: public and administrative boundaries kept separate]

## Public Site

### P1. Gallery home — two concepts to choose between

Both concepts satisfy the approved refinement: image-led exhibit cards, creations encountered immediately, minimal for the first release with three seed cards. [scope-document] [intent-backlog IB-13]

**Concept A — "Exhibition wall"** (large, varied tiles; the work dominates)

```
+--------------------------------------------------------------+
| MICHAEL BROADFOOT                                            |
| Systems Architect . Engineer . Maker                         |
+--------------------------------------------------------------+
|                                                              |
|  +--------------------------------+  +---------------------+ |
|  |                                |  |                     | |
|  |        [ lead image ]          |  |   [ lead image ]    | |
|  |                                |  |                     | |
|  |                                |  +---------------------+ |
|  +--------------------------------+  | STARS               | |
|  | AI Arcade                      |  | one-line summary    | |
|  | one-line summary               |  +---------------------+ |
|  +--------------------------------+                          |
|  +---------------------------------------------------------+ |
|  |              [ lead image, wide crop ]                  | |
|  +---------------------------------------------------------+ |
|  | Mom's Recipe Box          one-line summary              | |
|  +---------------------------------------------------------+ |
|                                                              |
+--------------------------------------------------------------+
| footer: GitHub link . contact link . (c) Michael Broadfoot   |
+--------------------------------------------------------------+
```

**Concept B — "Workbench grid"** (uniform cards; calm and easy to extend)

```
+--------------------------------------------------------------+
| MICHAEL BROADFOOT     Systems Architect . Engineer . Maker   |
+--------------------------------------------------------------+
| One sentence on what this site is: things I design and build |
+--------------------------------------------------------------+
|  +------------------+  +------------------+  +------------+  |
|  |                  |  |                  |  |            |  |
|  |  [ lead image ]  |  |  [ lead image ]  |  | [ image ]  |  |
|  |                  |  |                  |  |            |  |
|  +------------------+  +------------------+  +------------+  |
|  | AI Arcade        |  | STARS            |  | Mom's      |  |
|  | summary line     |  | summary line     |  | Recipe Box |  |
|  | tags: AI, games  |  | tags: science    |  | tags: app  |  |
|  +------------------+  +------------------+  +------------+  |
|                                                              |
+--------------------------------------------------------------+
| footer: GitHub link . contact link . (c) Michael Broadfoot   |
+--------------------------------------------------------------+
```

| | Concept A — Exhibition wall | Concept B — Workbench grid |
|---|---|---|
| First impression | Immersive; the work is the page | Orderly; reads as a curated catalogue |
| With three exhibits | Looks deliberate and full | Looks tidy; one row |
| Growing to many exhibits | Needs layout rules for tile sizes | Extends naturally; filtering slots in later |
| Effort | Higher (varied crops per image) | Lower |

**States**

- *Empty (no exhibit published yet):* the header plus "New work is being installed." No broken grid. [corner: empty collection]
- *Loading:* card-shaped placeholders in the final layout, so nothing jumps when images arrive.
- *Image fails to load:* the card keeps its title and summary over a neutral panel; the card still opens.
- *One exhibit:* a single large card, not a lonely grid cell.

**Accessibility note:** h1 = site name; `header`, `main`, `footer` landmarks; skip link first; each card is a single link whose accessible name is the project title; every lead image has alt text written in the Studio; Tab order follows reading order.

### P2. Exhibit page

Serves all three first-release audiences: the summary for clients and employers, the narrative for engineers, the build material for makers. [intent-statement: Target Customer]

```
+--------------------------------------------------------------+
| < All work                                MICHAEL BROADFOOT  |
+--------------------------------------------------------------+
|                    [ lead image, full width ]                |
+--------------------------------------------------------------+
| AI Arcade                                                    |
| one-paragraph summary (what it is, why it matters)           |
| [ View code ]  [ Live demo ]          tags: AI, games        |
+--------------------------------------------------------------+
| Inspiration              . paragraph                         |
| Design challenges        . paragraph                         |
| Architectural decisions  . paragraph                         |
| Implementation           . paragraph                         |
| Outcomes                 . paragraph                         |
| Lessons learned          . paragraph                         |
+--------------------------------------------------------------+
| Gallery   [img] [img] [img] [img]   (opens larger view)      |
+--------------------------------------------------------------+
| Build it yourself                                            |
|   - cut-list.pdf            (download)                       |
|   - enclosure.skp           (download)                       |
|   - assembly instructions   (section)                        |
+--------------------------------------------------------------+
| < All work                                                   |
+--------------------------------------------------------------+
```

**States and edge cases**

- *Section left empty in the Studio:* the heading is not shown at all (no empty headings).
- *No build material:* the "Build it yourself" block is omitted. [intent-backlog IB-8]
- *No live demo:* only the links that exist are shown. [intent-backlog IB-7]
- *Withdrawn or unknown exhibit:* a plain "This exhibit isn't on display" page with a link back to all work; never an error code. [intent-backlog IB-16]
- *Very long title or summary:* wraps; never truncated in the heading.

**Accessibility note:** h1 = project title, h2 per narrative section; `header`, `nav` (back link), `main`, `footer`; the larger image view is a dialog that traps focus, closes on Escape, and returns focus to the thumbnail; downloads state the file type and size in their link text.

## Studio (owner only)

### S1. Sign in

```
+--------------------------------------------------------------+
|                         STUDIO                               |
|                                                              |
|                  [ Sign in to continue ]                     |
|                                                              |
|   Private workspace. Nothing here is public until you        |
|   publish it.                                                |
+--------------------------------------------------------------+
```

- *Not the owner:* "This workspace is private." No hint of what is inside. [intent-backlog IB-1]
- *Session expired mid-edit:* sign in again and return to the same editor with unsaved work kept. [corner: session expiry]

**Accessibility note:** h1 = Studio; `main` only; focus starts on the sign-in button.

### S2. Projects

```
+--------------------------------------------------------------+
| STUDIO   Projects                         [ Discover repo ]  |
+--------------------------------------------------------------+
| Project            Repos   Status          Updated           |
| ----------------   -----   -------------   ----------        |
| AI Arcade          2       Published       2026-10-12        |
| STARS              1       Draft           2026-10-11        |
| Mom's Recipe Box   1       Changes since   2026-10-11        |
|                            last publish                      |
+--------------------------------------------------------------+
```

- *Empty (first run):* "No projects yet. Discover a GitHub repository to start your first exhibit." with the Discover button.
- *Status is shown in words, not colour alone:* Draft, Published, Changes since last publish.

**Accessibility note:** h1 = Projects; `header`, `main`; a real table with column headers; the primary action is the first focusable control after the heading.

### S3. Discover a repository

```
+--------------------------------------------------------------+
| STUDIO   Discover a repository                    [ Close ]  |
+--------------------------------------------------------------+
| Search your repositories: [______________________]           |
|                                                              |
| ai-arcade          PRIVATE   updated 3 days ago  [ Use ]     |
| stars              public    updated 1 week ago  [ Use ]     |
| MomsRecipeBox      public    linked to: Mom's R. [ Open ]    |
|                                                              |
| Use -> "Create a new project" or "Link to: [ project v ]"    |
+--------------------------------------------------------------+
```

- *Private repository:* clearly labelled PRIVATE. Choosing it never publishes anything; its exhibit starts as a draft like any other. [scope-document: discovering private material never makes it public]
- *Already linked:* shows which project it belongs to and opens it instead of creating a duplicate.
- *GitHub unreachable or rate-limited:* "Can't reach GitHub right now. Your projects are unaffected. Try again." with a retry.
- *No match for the search:* says so and keeps the search text.

**Accessibility note:** h1 = Discover a repository; the result count is announced politely as the list updates; the visibility label is text, not just an icon.

### S4. Exhibit editor (with AI suggestion)

```
+--------------------------------------------------------------+
| STUDIO  < Projects   AI Arcade      Saved 2 min ago          |
|                                    [ Preview ]  [ Publish ]  |
+--------------------------------------+-----------------------+
| Title       [AI Arcade____________]  | AI suggestion         |
| Summary     [_____________________]  | [ Suggest description]|
| Lead image  [ choose ]  alt [_____]  |                       |
|                                      | Suggested summary:    |
| Inspiration           [ text ]       | "..."                 |
| Design challenges     [ text ]       |                       |
| Architectural dec.    [ text ]       | Drawn from:           |
| Implementation        [ text ]       |  - README.md          |
| Outcomes              [ text ]       |  - docs/design.md     |
| Lessons learned       [ text ]       |                       |
|                                      | [ Insert ] [ Edit ]   |
| Gallery     [img][img][ + add ]      | [ Discard ]           |
| Links       [ View code ][ + add ]   |                       |
| Build files [cut-list.pdf][ + add ]  |                       |
| Repos       ai-arcade (PRIVATE)      |                       |
+--------------------------------------+-----------------------+
```

- *The suggestion never overwrites:* Insert places it into the field for editing; nothing changes until the owner acts. [intent-backlog IB-9]
- *Sources shown:* every suggestion lists the files it was drawn from. [scope-document: suggestions show their source evidence]
- *Suggestion fails or times out:* "No suggestion this time. Your text is unchanged." with a retry.
- *Unsaved changes:* the status reads "Unsaved changes"; leaving the page asks first. [corner: unsaved input on navigation]
- *Image without alt text:* flagged in place ("Add a description for screen readers") before publishing.

**Accessibility note:** h1 = project title; `header`, `main`, `aside` (AI suggestion); every field has a visible label; save status is an `aria-live` polite region; the suggestion panel is reachable by keyboard right after the form.

### S5. Preview

```
+--------------------------------------------------------------+
| PREVIEW - not public                  [ Back to editor ]     |
+--------------------------------------------------------------+
|                                                              |
|       (the exhibit page P2, exactly as visitors see it)      |
|                                                              |
+--------------------------------------------------------------+
```

- The banner is always visible, so a preview is never mistaken for the live page. [intent-backlog IB-10]
- Includes the gallery card (P1) as it will appear.

**Accessibility note:** the banner is the first element and a `region` labelled "Preview"; the rest follows P2's structure.

### S6. Publish confirmation

```
+--------------------------------------------------------------+
| Publish "AI Arcade"?                                         |
|                                                              |
| This makes the following public at                           |
| michael.broadfoot.consulting/work/ai-arcade:                 |
|   - title, summary, 6 narrative sections                     |
|   - 4 images, 2 links, 2 downloadable files                  |
|                                                              |
| ! Linked repository "ai-arcade" is PRIVATE. Only the         |
|   content above is published; the repository stays private   |
|   and the "View code" link will not work for visitors.       |
|                                                              |
|                         [ Cancel ]   [ Publish ]             |
+--------------------------------------------------------------+
```

- Nothing becomes public without this explicit step. [intent-backlog IB-11] [scope-document]
- *Already published:* the same dialog says "Update the public exhibit" and lists what changed.
- *Withdraw:* a separate "Take down" action with its own confirmation naming the exhibit. [intent-backlog IB-16]
- *Missing alt text or empty title:* Publish stays disabled, with the reason shown in text.

**Accessibility note:** a modal dialog; focus starts on Cancel (the safe choice); Escape cancels; the warning uses an icon plus text, not colour alone.

## Assumptions & Open Questions

- **Gallery concept (decision at the approval gate).** Concept A "Exhibition wall" or Concept B "Workbench grid". Refined Mockups develops the one chosen.
- **Image source.** Wireframes show images chosen in the Studio ("choose" / "+ add"); whether they are uploaded, pulled from GitHub, or both is still settled in Requirements Analysis, as recorded in the scope document. [assumption]
- **Exhibit address.** Pages are sketched at `/work/<project>`; the final address pattern is decided in Requirements Analysis. [assumption]
- **Contact link.** The footer shows a contact link because the intent includes consulting enquiries; its form (email link or other) is settled in Requirements Analysis, and it must not collect visitor data. [assumption]
