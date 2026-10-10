# Refined Mockups ? Local Verification

## Scope

Static records and visual board only; no application code, Observer changes, infrastructure, provider calls or deployment. The board is not a working application and these checks do not certify WCAG or security implementation.

## Automated Checks

- Existing local Python Playwright and headless Microsoft Edge rendered the local file; no dependency installation.
- HTTP/HTTPS requests blocked and recorded: zero requests. No script tags or external resource links.
- No page horizontal overflow at 320, 375, 767, 768, 900, 1023, 1024 and 1440 CSS px.
- Four gallery/editor captures at 375 and 1440 px are in `screenshots/`.
- Markdown has expected section structure, valid UTF-8 and no replacement/NUL characters. No Mermaid diagrams generated.

## Contrast Calculations

Computed sRGB relative luminance; lowest contrast against canvas/surface/raised is shown. This checks proposed palette pairs, not every implemented component state.

| Foreground | Minimum ratio | Design threshold |
|---|---:|---:|
| text | 12.27:1 | 4.5:1 |
| muted | 7.90:1 | 4.5:1 |
| accent | 8.89:1 | 4.5:1 |
| warning | 8.89:1 | 4.5:1 |
| danger | 8.09:1 | 4.5:1 |
| border | 3.15:1 | 3:1 |

Filled accent buttons use canvas text on accent. Borders are non-text checks. Static specimen spans do not exercise functional keyboard behavior.

## Remaining Implementation Verification

Full axe, keyboard, assistive-technology, zoom/text-spacing and supported-browser tests; issuer/subject+MFA authorization, private recovery, upload validation, metadata stripping, attachment headers, immutable publication approval and serial operation invariants. Follow the accessibility checklist and team practices. Real image crops/alt and final copy require owner content review.

## Visual Inspection

The designer inspected all four saved screenshots. Gallery cards stack in reading order at 375 px; desktop preserves the varied orderly grid. Editor actions wrap, form groups stay readable and the AI panel follows the form on phones. Placeholder imagery and sample copy remain explicitly labelled. No overlapping or page-clipped controls observed in these captures.
