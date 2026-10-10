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
