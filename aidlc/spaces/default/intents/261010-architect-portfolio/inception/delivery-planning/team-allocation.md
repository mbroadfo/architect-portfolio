# Team Allocation

**Inputs:**
- bolt-plan;
- unit-of-work;
- team-practices;
- requirements.

A **Bolt** is one build pass over part of a unit of work, ending in working, tested code merged through one pull request. A **mob** is the group of roles that works on a Bolt together.

Team Formation was skipped in the approved plan, which is based on `classic`. So there is one team: every Bolt (B01 to B30) is executed by **aidlc-developer-agent (AI)**, in this session, under Claude Code as the single owner of the workflow state (P-05). This is not a Program Board, because only one team exists.

## Roles per Bolt

| Role | Who | Where it applies |
|---|---|---|
| Builds the Bolt | aidlc-developer-agent | B01 to B30 |
| Unit design (Functional, NFR and Infrastructure Design) | aidlc-architect-agent; aidlc-aws-platform-agent for Infrastructure Design | Each unit, before its first Bolt |
| Test strategy, and checking the coverage floor | aidlc-quality-agent | Each unit |
| Security design input | aidlc-devsecops-agent | 🔒 Bolts (see `bolt-plan.md`) |
| **Independent security review** | A separate AI review session that did not write the change (team practice) | Every 🔒 Bolt, before Michael approves it |
| Approves each Bolt at its checkpoint | Michael Broadfoot | Every Bolt |
| Authorizes merges, deployments, preview creation and spending | Michael Broadfoot | See `external-dependency-map.md` |

## Parallel Work

Construction runs serially, one unit at a time (the recorded settings). Team practice allows independent coding agents in other harnesses to work in parallel on isolated branches, but only when Michael starts them. The workflow state still keeps one owner. No parallel agent is assumed in this plan.

## Assumptions & Open Questions

- **Single owner.** There are no external teams. If Michael later assigns a unit to another harness, ownership changes only through a recorded handoff (project rule).
