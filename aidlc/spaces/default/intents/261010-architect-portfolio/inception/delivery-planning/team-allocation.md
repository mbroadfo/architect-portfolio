# Team Allocation

**Inputs:**
- bolt-plan;
- unit-of-work;
- team-practices;
- requirements.

A **Bolt** is one build pass over part of a unit of work, ending in working, tested code merged through one pull request. A **mob** is the group of roles that works on a Bolt together.

Team Formation was skipped in the approved plan, which is based on `classic`. So there is one team: every Bolt (S0 to S3, B01 to B29 and B05a) is executed by **aidlc-developer-agent (AI)**, in this session, under Claude Code as the single owner of the workflow state (P-05). This is not a Program Board, because only one team exists.

## Roles per Bolt

| Role | Who | Where it applies |
|---|---|---|
| Builds the Bolt | aidlc-developer-agent, one Bolt at a time (unit-major, serial) | S0 to S3, B01 to B29, B05a |
| End-to-end journeys (Build and Test stage) | aidlc-quality-agent with aidlc-developer-agent | After Code Generation (formerly B30) |
| Unit design (Functional, NFR and Infrastructure Design) | aidlc-architect-agent; aidlc-aws-platform-agent for Infrastructure Design | Each unit, before its first Bolt |
| Test strategy, and checking the coverage floor | aidlc-quality-agent | Each unit |
| Security design input | aidlc-devsecops-agent | 🔒 Bolts (see `bolt-plan.md`) |
| **Independent security review** | A separate AI review session that did not write the change (team practice) | Every 🔒 Bolt, before Michael approves it |
| Approves each unit at its engine checkpoint, where every Bolt is listed individually with its evidence. Not accepting a Bolt means Request Changes for the unit (recommended D2-A in `bolt-plan.md`) | Michael Broadfoot | Every unit and its Bolts |
| Authorizes merges, deployments, preview creation and spending | Michael Broadfoot | See `external-dependency-map.md` |

## Parallel Work

Construction stays unit-major and serial. Parallel engine execution (swarm) was evaluated and is not recommended now; the reasons and the changes it would need are in `bolt-plan.md`.

**Branches.** Each Bolt has its own branch and pull request, stacked only within its unit (at most five deep). The stacks merge after the unit checkpoint, once preview verification and merge authorization allow.

**One owner.** Exactly one owner of the workflow state remains: this session (P-05). Independent agents in other harnesses can still be started by Michael on isolated branches, as team practice allows. This plan does not assume any.

## Assumptions & Open Questions

- **Single owner.** There are no external teams. If Michael later assigns a unit to another harness, ownership changes only through a recorded handoff (project rule).
