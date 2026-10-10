import type { ApprovalStatus, PendingGate, StageState, TimelineEvent } from "../shared/types.ts";

export interface GateStage {
  slug: string;
  name: string;
  state: StageState;
}

export function deriveApproval(input: {
  workflowStatus: string | null;
  currentStage: string | null;
  stages: GateStage[];
}): ApprovalStatus {
  const current = input.stages.find((stage) => stage.slug === input.currentStage) ?? null;
  const status = (input.workflowStatus ?? "").trim().toLowerCase();
  const stageName = current?.name ?? null;

  if (status === "completed" || status === "complete") {
    return { code: "completed", label: "Workflow complete", stage: input.currentStage, stageName };
  }
  if (current?.state === "awaiting-approval") {
    return { code: "awaiting-approval", label: "Awaiting your approval", stage: input.currentStage, stageName };
  }
  if (current?.state === "revising") {
    return { code: "revising", label: "Revising after a rejected gate", stage: input.currentStage, stageName };
  }
  if (current?.state === "in-progress") {
    return { code: "in-progress", label: "In progress", stage: input.currentStage, stageName };
  }
  if (current?.state === "completed" && (status === "running" || status === "active" || status === "")) {
    return { code: "ready-to-advance", label: "Approved and ready to advance", stage: input.currentStage, stageName };
  }
  if (!input.currentStage && input.stages.length === 0) {
    return { code: "not-started", label: "No workflow stage is recorded", stage: null, stageName: null };
  }
  if (!current || current.state === "unknown") {
    return {
      code: "unknown",
      label: input.currentStage ? "Stage is named, but its marker is missing" : "Approval state unknown",
      stage: input.currentStage,
      stageName,
    };
  }
  if (current.state === "pending") {
    return { code: "not-started", label: "Not started", stage: input.currentStage, stageName };
  }
  if (current.state === "skipped") {
    return { code: "unknown", label: "Current stage is marked skipped", stage: input.currentStage, stageName };
  }
  return { code: "unknown", label: "Approval state unknown", stage: input.currentStage, stageName };
}

export function pendingGates(stages: GateStage[], events: TimelineEvent[]): { gates: PendingGate[]; warnings: string[] } {
  const warnings: string[] = [];
  const fromAudit = new Map<string, { state: "awaiting-approval" | "revising"; since: string | null }>();

  for (const event of events) {
    if (!event.stage) continue;
    if (event.event === "STAGE_AWAITING_APPROVAL") {
      fromAudit.set(event.stage, { state: "awaiting-approval", since: event.timestamp });
    } else if (event.event === "GATE_REJECTED") {
      fromAudit.set(event.stage, { state: "revising", since: event.timestamp });
    } else if (event.event === "GATE_APPROVED" || event.event === "STAGE_COMPLETED") {
      fromAudit.delete(event.stage);
    }
  }

  const gates: PendingGate[] = [];
  const seen = new Set<string>();

  for (const stage of stages) {
    if (stage.state !== "awaiting-approval" && stage.state !== "revising") continue;
    const audit = fromAudit.get(stage.slug);
    gates.push({
      stage: stage.slug,
      stageName: stage.name,
      state: stage.state,
      since: audit?.since ?? null,
      detail: stage.state === "revising"
        ? "You sent this stage back. The team is revising it."
        : "This stage is finished and waiting for your approval.",
    });
    seen.add(stage.slug);
  }

  for (const [slug, audit] of fromAudit) {
    if (seen.has(slug)) continue;
    const recorded = stages.find((stage) => stage.slug === slug);
    if (recorded && (recorded.state === "completed" || recorded.state === "skipped")) continue;
    warnings.push(`The audit shows an open gate on ${slug} that the state file has not marked.`);
    gates.push({
      stage: slug,
      stageName: recorded?.name ?? slug,
      state: audit.state,
      since: audit.since,
      detail: "Found in the audit log. The state file does not mark this gate yet.",
    });
  }

  return { gates, warnings };
}
