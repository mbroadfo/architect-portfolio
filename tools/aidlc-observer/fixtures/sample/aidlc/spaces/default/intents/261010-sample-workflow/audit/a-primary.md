# AI-DLC Audit Log

## Workflow Start
**Timestamp**: 2026-10-10T12:00:00Z
**Event**: WORKFLOW_STARTED
**Scope**: classic

---

## Stage Start
**Timestamp**: 2026-10-10T12:01:00Z
**Event**: STAGE_STARTED
**Stage**: intent-capture
**Agent**: aidlc-product-agent

---

## Stage Completion
**Timestamp**: 2026-10-10T12:05:00Z
**Event**: STAGE_COMPLETED
**Stage**: intent-capture
**Details**: Stage approved by gate

---

## Decision Recorded
**Timestamp**: 2026-10-10T12:06:00Z
**Event**: DECISION_RECORDED
**Stage**: intent-capture
**Decision**: Publish three exhibits before adding analytics

---

## Stage Start
**Timestamp**: 2026-10-10T12:10:00Z
**Event**: STAGE_STARTED
**Stage**: refined-mockups

---

## Sensor Passed
**Timestamp**: 2026-10-10T12:11:00Z
**Event**: SENSOR_PASSED
**Sensor ID**: required-sections
**Stage slug**: refined-mockups

---

## Not an event
This block has a heading and no event name, so the reader skips it.

---

## Stage Awaiting Approval
**Timestamp**: 2026-10-10T12:12:00Z
**Event**: STAGE_AWAITING_APPROVAL
**Stage**: refined-mockups
