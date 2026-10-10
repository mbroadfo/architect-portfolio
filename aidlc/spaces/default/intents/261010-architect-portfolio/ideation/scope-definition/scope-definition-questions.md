# Scope Definition — Questions

Already decided and not asked again: the first vertical slice's capabilities (charter section 8: Studio sign-in, discovering a GitHub repository, creating or linking a project, editing its public presentation, an AI description suggestion, preview, saving, explicit publication); the seed examples (AI Arcade, STARS, Mom's Recipe Box); the exhibit narrative (inspiration, design challenges, architectural decisions, implementation, outcomes, lessons learned, charter section 3); and the first-version exclusions confirmed in Intent Capture (no Drive/SketchUp connectors, no non-public access, no visitor appearance settings). These questions cover only what remains open about the boundary and order of the first release.

## Q1. What must the first release include on the public, visitor-facing side?

The charter's first slice is described from the Studio side and ends at "explicitly authorize publication". This settles what a visitor actually sees once something is published.

A. Exhibit pages for published projects, plus a simple index page listing them
B. Exhibit pages only, reached by direct link
C. A full exhibition-style home (featured work, grouping by discipline, filtering)
D. No public site in the first release — Studio and preview only
E. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Beyond the required narrative sections, what else should a first-release exhibit carry? (select all that apply)

Makers and engineers are part of the first-release audience, so exhibits may need more than the written narrative.

A. An image gallery (screenshots, CAD renders, workshop photos)
B. Links out to the GitHub repositories, live application or demo
C. Build-it-yourself material (downloadable design files, cut lists, instructions)
D. Nothing beyond the narrative sections and one lead image
E. Not yet defined
X. Other (please specify)

[Answer]: A, B, C

## Q3. Where should exhibit images come from in the first release?

The portfolio is image-rich; this decides whether the Studio needs its own image handling in the first release.

A. Uploaded by me in the Studio
B. Pulled from the GitHub repository (for example, images referenced in the README)
C. Both
D. Not yet defined
X. Other (please specify)

[Answer]: D

## Q4. What order should the first release be built in?

This sets the sequencing of the backlog.

A. Value-first — get a public site with the three seed exhibits live early (authored by hand if needed), then build the Studio workflow behind it
B. Risk-first — build Studio sign-in and the publish boundary (private material never leaks) first; the public site follows
C. One thin end-to-end pass — Studio, then publication, then the public page, in the charter's order, all together
D. Not yet defined
X. Other (please specify)

[Answer]: D

## Q5. Is the first release tied to a deadline?

A. Yes, a specific date (please state it under Other)
B. A soft target, not a hard date
C. No deadline
D. Not yet defined
X. Other (please specify)

[Answer]: D (chosen by the agent on the owner's instruction to handle routine decisions; no deadline was given, so none is assumed)

## Q6. Should this first release end with the site live on its real address?

The plan includes deployment stages, each of which waits for your approval. This sets what "done" means for the first release.

A. Yes — live at michael.broadfoot.consulting, with mike.broadfoot.consulting redirecting to it
B. Live at michael.broadfoot.consulting; the redirect comes later
C. Not public yet — a private test environment only
D. Not yet defined
X. Other (please specify)

[Answer]: A (chosen by the agent on the owner's instruction to handle routine decisions; the charter names the canonical site and the 301 redirect, and every deployment and DNS step still waits for the owner's approval)
