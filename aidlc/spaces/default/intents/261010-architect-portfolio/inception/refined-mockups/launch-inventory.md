# Launch Candidate Inventory

Status: **evidence for owner review.** This inventory records what was checked and what was found. It does not declare any candidate ready to publish. That is Michael's decision (CR-01, CR-03).

Checked 2026-10-10 by Claude (lead AI-DLC owner). Methods:

- the GitHub REST API through `gh`: repository visibility, licence, Pages, deploy workflows and their last runs, repository variables;
- `curl` against each configured domain;
- headless Chromium (Playwright 1.64) at 1600×1000 and 390×844, with console errors and every network host recorded.

## Summary

| Candidate | Source repository | Licence | Live app | Sign-in | Desktop | Phone (390 px) | Hosting |
|---|---|---|---|---|---|---|---|
| STARS | Public (`mbroadfo/stars`) | **None** | https://stars.xaminisalamini.com — 200 | None found | Renders, no console errors, same-origin requests only | Renders, no overflow | S3 + CloudFront, Cloudflare DNS |
| Monopoly | Public (`mbroadfo/monopoly-arena`) | **None** | https://arena.xaminisalamini.com — 200 | None found | Renders, no console errors, same-origin only | **25 px horizontal overflow** | S3 + CloudFront, Cloudflare DNS |
| Baduk | Public (`mbroadfo/baduk`) | MIT | https://baduk.xaminisalamini.com — 200 | None found | Renders, no console errors, same-origin only | Renders, no overflow | S3 + CloudFront, Cloudflare DNS |
| Risk | **Private** (name withheld) | None | Live deployment found — **URL withheld** | None found | Renders, no console errors; loads Google Fonts | **Desktop-only layout (980 px wide)** | S3 (per server header); not inspected further |

All four deploy from GitHub Actions ("DevOps: Frontend" and "DevOps: Infrastructure"), and their last frontend runs succeeded: STARS and Monopoly on 2026-08-17, Baduk on 2026-08-25, Risk on 2026-09-23. Terraform for the three public apps provisions only static hosting: S3, CloudFront, ACM and Cloudflare records. They have no API or database, so any AI play runs in the visitor's browser.

## What this means

- **"Browser-ready" is not yet established for any candidate.** All four load without sign-in on desktop. Being ready to present also depends on the owner's judgement, on phone behaviour (Monopoly overflows, Risk is desktop-only) and on the IP questions below.
- **Public source does not mean open source.** STARS and Monopoly are public repositories with no licence, so visitors may read the code but have no right to reuse it. Only Baduk is open source (MIT). Exhibit badges must say "Source available" or "Open source · MIT" accordingly. If Michael wants these to be open source, adding a licence is the owner's decision.
- **Risk: live but private.** The app is publicly reachable without sign-in, while its repository is private. Under D-15 and D-22 the exhibit may link the live app only once Michael approves that link. It never links the source, and its description and imagery may be drawn from the private repository only with Michael's approval. For the same reason, this public record holds neither the repository name nor the live URL.
- **Names and artwork (owner decision before publishing).** "Monopoly" and "Risk" are third-party trademarks, and the Monopoly app's board artwork resembles the trademark owner's trade dress. The charter forbids publishing copyrighted material without rights. So the prototype shows concept art instead of a capture of the Monopoly board. The exhibit titles, any disclaimer and the screenshot policy need Michael's decision.
- **Domain.** The apps live on `xaminisalamini.com`, not `broadfoot.consulting`. Linking to them needs no change. Moving them would be new DNS and infrastructure work, needing approval.

## Not checked

- Accessibility (axe) and performance (Lighthouse) of the apps themselves.
- Behaviour in Safari and Firefox.
- Whether any app calls a paid service at runtime. Network logs during the initial load showed same-origin requests only, but longer sessions were not exercised.
