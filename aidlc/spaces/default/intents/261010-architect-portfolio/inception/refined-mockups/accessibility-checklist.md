# Accessibility Checklist

## Sources and Status

Inputs:

- wireframes and user-flow — `../../ideation/rough-mockups/`;
- requirements — `../requirements-analysis/requirements.md`: NFR8, FR1–FR10, Amendment A1 to A1.2;
- team-practices — `../practices-discovery/team-practices.md`.

**Status for R5.** The working prototype (`prototype/`) is checked by the repeatable suite `prototype/tests/verify.cjs`. Results are in `verification.md`:

- axe-core 4.10.2 reports no serious or critical violations on 7 public routes and 10 Studio views;
- keyboard skip link, focus visibility, carousel, lightbox, dialogs and the leave guard work;
- reduced motion is honoured;
- every token pair is at least 4.5:1;
- no horizontal overflow at 390, 768, 1024 and 1440 px.

That is design evidence, not a claim of tested application compliance. Screen-reader passes, zoom and text-spacing overrides, hosted-provider sign-in and the real upload and publication flows must still be verified on the built app.

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
| Skip link (R5) | "Skip to content" is the first focusable element on every page | Verified in prototype (K-skip, K-skip-target); repeat on built routes |
| Featured carousel (R5) | Manual only, named previous/next, position text, polite live region, arrow keys, reduced motion | Verified in prototype (C-no-autoplay, C-keyboard, M-reduced-motion); screen-reader pass on built app |
| Category chips and pages (R5) | Links in a labelled nav with `aria-current`, counts as text, own h1 per category | axe in prototype; screen-reader pass on built app |
| Enlarged image view (R5) | Named image buttons, native dialog, arrows step, Escape closes, focus returns | Verified in prototype (D-lightbox) |
| Withheld and private states (R5) | "Source private", "Live link pending approval", PRIVATE spelled out; disabled fields explain why | Verified in prototype (S-risk-url, F-risk-nolink) |
| Third-party requests (R5) | Fonts self-hosted; nothing loaded from another origin | Verified in prototype (P-*); CSP check on the built app (NFR15) |

## Validation Gates

Before implementation approval: axe reports zero serious/critical issues on public and Studio routes; meaningful keyboard, screen-reader and zoom checks complement automated tests. Test latest two Chrome/Edge/Firefox/Safari versions per NFR12, with NVDA/Windows and VoiceOver/Safari manual coverage. Mobile layouts must remain usable at 320 px.

Verify especially: S3 result-count updates; S4 conflict and restored edits; AI source list and disabled reason; S6 full inventory navigation and stale revision; S7 warning and focus return; P2 enlarged image and 404 navigation. Follow team-practices preview verification only after separately authorized infrastructure exists. No preview deployment is authorized by this checklist.

## Assumptions & Open Questions

Real alt text, provider-hosted sign-in accessibility, final component semantics and runtime focus behavior cannot be certified from static mockups. Track these as implementation acceptance checks, not completed tests.
