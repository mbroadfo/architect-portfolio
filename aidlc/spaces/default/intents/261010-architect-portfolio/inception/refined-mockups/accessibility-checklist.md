# Accessibility Checklist

## Sources and Status

Inputs: wireframes and user-flow from `../../ideation/rough-mockups/`, requirements NFR8 and FR1–FR9 from `../requirements-analysis/requirements.md`, and team-practices from `../practices-discovery/team-practices.md`. User stories are skipped. Target: WCAG 2.1 AA for both public site and Studio.

This is a design checklist and implementation verification plan, not a claim of tested application compliance. Static board controls illustrate states; functional keyboard/focus behavior must be verified on the built application.

## Design Checks and Required Evidence

| Check | Design treatment | Implementation verification |
|---|---|---|
| Page semantics | One h1 per product screen, ordered h2, landmarks, English language | DOM/axe plus screen-reader heading navigation |
| Skip navigation | First focusable Skip to content | Keyboard test at each route |
| Text contrast | Opaque surfaces and tested token pairs, at least 4.5:1 | Token calculation plus rendered-state checks including hover/error/disabled explanations |
| Non-text contrast | Visible borders/focus at least 3:1 | Inspect every control boundary and focus ring |
| Keyboard | Native links/buttons/fields; no mouse-only upload or image view | Complete visitor and owner journeys without pointer |
| Focus | Visible ring, logical DOM order; no CSS grid reorder | Tab/Shift+Tab at all breakpoints, 200% and 400% zoom. "Jump to AI suggestions" link (name, visibility below 1024px, focus to panel, return after action) verified at tablet breakpoint. |
| Modal behavior | Label, focus containment, Cancel initial, Escape/return | Publish/update/take-down/image dialog tests; no nested traps |
| Inputs | Visible labels, hints before input; grouped lead radios | Screen-reader name/description and error associations |
| Validation | Error summary and field links; data retained | Empty title/no lead/missing alt/bad upload/conflict tests |
| Status messages | Polite save/search/progress completion; errors described in text | Check announcements occur once and focus is preserved |
| Images | Alt for each published image; lead/alt publication gate | axe plus editorial review of meaningful alt; image failure fallback |
| Reflow | 320 CSS px, wrapping paths/titles, single-column phones | No two-axis scrolling or clipped actions at zoom/breakpoints |
| Text spacing | Flexible height, no ellipsis for essential content | Override line/paragraph/letter/word spacing |
| Touch | Design minimum 44×44 px, 8 px separation | Measure targets; explicitly a project usability convention (not WCAG 2.1 AA requirement) |
| Motion | No autoplay/parallax; reduced motion disables transitions | Emulate reduced motion; no flashing or unavoidable animation |
| Color independence | PRIVATE/public and all four statuses spelled out | Grayscale check; errors never border-only |
| Timing | Session recovery preserves edits; AI timeout preserves text | Reauthenticate as same owner; timeout and retry tests |
| Public links | Descriptive names, private code links absent | Inspect DOM/export as well as visual output |
| Downloads | File type/size in link text | Screen-reader and safe-response-header checks |
| Authentication | Provider sign-in/MFA and non-owner message | Include hosted provider flow in keyboard and assistive-tech testing |
| Consistency | Save never publishes; safe Cancel; explicit final action | Repeated-state wording and sequence tests |

## Validation Gates

Before implementation approval: axe reports zero serious/critical issues on public and Studio routes; meaningful keyboard, screen-reader and zoom checks complement automated tests. Test latest two Chrome/Edge/Firefox/Safari versions per NFR12, with NVDA/Windows and VoiceOver/Safari manual coverage. Mobile layouts must remain usable at 320 px.

Verify especially: S3 result-count updates; S4 conflict and restored edits; AI source list and disabled reason; S6 full inventory navigation and stale revision; S7 warning and focus return; P2 enlarged image and 404 navigation. Follow team-practices preview verification only after separately authorized infrastructure exists. No preview deployment is authorized by this checklist.

## Assumptions & Open Questions

Real alt text, provider-hosted sign-in accessibility, final component semantics and runtime focus behavior cannot be certified from static mockups. Track these as implementation acceptance checks, not completed tests.
