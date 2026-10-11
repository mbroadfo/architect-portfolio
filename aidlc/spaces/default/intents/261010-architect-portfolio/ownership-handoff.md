# Workflow Ownership — Claude Code to Codex

## Authority and Starting Point

Michael explicitly assigned Codex sole active ownership while Claude Code is unavailable. This is an owner-directed takeover, not a claim that Claude performed an outgoing handoff. The supported `aidlc engine audit append-raw` operation recorded a Recovery note at 2026-10-10T19:58:43Z in the intent audit shard. No new workflow was created and no completed stage was repeated.

- Intent: `261010-architect-portfolio`, default space.
- Committed baseline: `fe3dbc0` (Codex setup), following `8247163` (Requirements Analysis approved).
- Branch: `records/inception-refined-mockups`.
- Requirements Analysis approved: 2026-10-10T19:02:36Z.
- Refined Mockups automatically started at the same time; no stage design files existed at takeover.
- Recovery breadcrumb at 18:52:36Z predates approval. The later audit and current state agree; no reconstruction was needed.

## Owner and Constraints

Codex is the sole writer of shared workflow state and intent records. Independent reviewers only write their assigned review output; they neither own nor advance the workflow. Claude Code must not resume writes concurrently; a future transition must be explicitly recorded.

Current user restrictions: do not change the Observer, deploy infrastructure, incur costs, merge PRs or approve PRs on Michael's behalf. This supersedes the ordinary team practice permitting an owner agent to merge approved records. Existing stage/content/deployment/security approval boundaries remain intact; no settings were changed.

Existing settings are preserved: Standard depth/test strategy; sensors and plan approval on; summary confirmation, learnings and collaborators off; Guard Policy off from the existing scope. Scope remains classic with the portfolio-inception-slice plan. The returned Refined Mockups review mode is advisory, one normal-flow pass. A reviewer verdict is not Michael's approval.

## Portable Record

Read `docs/CHARTER.md`, `docs/PROJECT_BRIEF.md`, the requirements, affirmed team-practices and memory, decision log D-01–D-22, current state and audit before resuming. Stage files are under `inception/refined-mockups/`; open the HTML board locally. Real imagery and final content remain owner inputs. This records PR is for independent review before Michael's stage decision; it must remain unmerged until Michael acts separately.

Known carried items: issue #2 tracks the stale spa-on-aws charter claim; provider/framework, infrastructure authorization, explicit AI spending permission/limit and distinct agent GitHub identity remain later-stage decisions. No such permission is implied by this handoff.

---

# Transition — Lead Ownership to Claude Code (2026-10-10)

The record above remains true for the period it covers. This section records the next transition. It supersedes that record's "Owner" paragraph from the time below onward.

## Authority and starting point

- **Authority.** Michael explicitly instructed Claude Code to "resume lead AI-DLC ownership of architect-portfolio from the current Refined Mockups checkpoint". Grok (the OpenCode harness, #7) and Codex are inactive as workflow writers. This is an owner-directed takeover. Neither earlier session performed an outgoing handoff, and none is claimed.
- **Recorded:** 2026-10-10T23:15:09Z.
- **Intent:** `261010-architect-portfolio`, default space.
- **Branch:** `records/inception-refined-mockups` (PR #8, unmerged).
- **Takeover baseline:** `337b835`.
- **First checkpoint as owner:** `f448884`. It contains:
  - homepage prototype R5;
  - `launch-inventory.md`;
  - `requirements-change-proposal.md`, holding CR-01 to CR-05 as proposed owner decisions awaiting final sign-off;
  - genuine Playwright screenshots.
- **Stage:** Refined Mockups is **not approved**. Michael has not approved the current public design. This transition neither rewrites nor approves the stage, and does not advance its gate.
- **Approved requirements:** `requirements.md` is unchanged.

## Workflow state left exactly as found

The owner's working tree (clone `shop-pc2`) holds **uncommitted** changes from the previous session. This transition left them untouched and did not commit them:

- `aidlc-state.md`: Refined Mockups `[-]` → `[?]` (awaiting approval), and `Last Updated` 19:02:36Z → 20:56:51Z;
- `audit/shop-pc2-cdbaebd09a31.md`: about 430 appended lines of engine events. These include a REVIEW_REQUESTED/REVIEW_COMPLETED pair for the Product Lead review, and an ERROR_LOGGED event about a pending review iteration;
- deletion of the four superseded `screenshots/*.png.txt` placeholders.

Michael decides whether to commit those changes as the previous session's record, or to discard them. Until he does, Claude Code makes **no engine write** on this clone, because any engine command would append to the same audit shard and mix the two sessions' records. For the same reason, this transition is not yet recorded in the audit trail. Once the shard is resolved, Claude Code records it with `aidlc engine audit append-raw`, the supported path the Codex takeover also used.

## Owner and constraints

- **Claude Code** is the sole writer of shared workflow state and intent records.
- **Codex and Grok** must not write workflow state. They may act only as independent reviewers when Michael assigns them, and write only their assigned review output. Any further transition must be recorded the same way.
- **Standing instructions** from Michael for this period:
  - do not merge PRs, deploy, approve the stage or advance the gate;
  - do not regenerate requirements;
  - do not launch additional agents unless asked;
  - record scope changes as proposals for Michael's sign-off; never change approved requirements silently.
- **Settings** are unchanged from the record above.

## Next steps (after Michael acts)

1. Michael signs off CR-01 to CR-05, in whole or in part. Claude Code then amends `requirements.md`, re-runs the requirements review on the changed sections, records D-23 onward and updates `docs/PROJECT_BRIEF.md`.
2. Continue Refined Mockups in the R5 direction: exhibit detail page, category page, Studio changes (title-only project, access metadata, featured/category controls). Then return the stage to Michael for his decision.
3. Open items that need Michael:
   - trademark and artwork review for Monopoly and Risk;
   - licensing for STARS and Monopoly;
   - authorizing Risk's live URL after its privacy and security review.

## Portable record

To resume, read the files listed in "Portable Record" above, plus:

- `inception/refined-mockups/requirements-change-proposal.md`;
- `inception/refined-mockups/launch-inventory.md`;
- `inception/refined-mockups/prototype/README.md` — open `prototype/index.html` locally and add `?notes` for the scope overlay.

Risk's private repository name and live URL are deliberately absent from all records, because this repository is public (D-15, D-22).
