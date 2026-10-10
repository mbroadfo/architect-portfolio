import type { RuntimeSummaryView } from "../shared/types.ts";

interface CountSet {
  total: number;
  approved: number;
  failed: number;
  pending: number;
}

interface GraphStage {
  stage_slug?: string;
  outcome?: string;
  completed_at?: string | null;
  memory_entries?: number | null;
  memory_breakdown?: {
    interpretations?: number;
    deviations?: number;
    tradeoffs?: number;
    open_questions?: number;
  } | null;
  sensor_firings?: { result?: string }[];
  instances?: {
    outcome?: string;
    completed_at?: string | null;
    memory_entries?: number | null;
    memory_breakdown?: GraphStage["memory_breakdown"];
    sensor_firings?: { result?: string }[];
  }[];
}

export function summaryFromCommand(value: unknown): RuntimeSummaryView | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  const stages = countSet(record.stages);
  if (!stages) return null;
  return {
    workflowId: stringOrNull(record.workflow_id),
    scope: stringOrNull(record.scope),
    startedAt: stringOrNull(record.started_at),
    durationMinutes: numberOrNull(record.duration_minutes),
    stages,
    byPhase: phaseMap(record.by_phase),
    sensors: sensorCounts(record.sensors),
    source: "aidlc-command",
  };
}

export function summaryFromGraph(
  value: unknown,
  phaseOf: (slug: string) => string,
): RuntimeSummaryView | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  if (!Array.isArray(record.stages)) return null;

  const stages = emptyCounts();
  const byPhase: Record<string, CountSet> = {};
  const sensors = { total: 0, passed: 0, failed: 0 };
  let latest: string | null = null;

  for (const raw of record.stages) {
    if (!raw || typeof raw !== "object") continue;
    const stage = raw as GraphStage;
    const phase = phaseOf(typeof stage.stage_slug === "string" ? stage.stage_slug : "");
    const units = stage.instances && stage.instances.length > 0 ? stage.instances : [stage];
    for (const unit of units) {
      const outcome = normalizeOutcome(unit.outcome);
      addOutcome(stages, outcome);
      if (!byPhase[phase]) byPhase[phase] = emptyCounts();
      addOutcome(byPhase[phase]!, outcome);
      for (const firing of unit.sensor_firings ?? []) {
        sensors.total += 1;
        if (firing.result === "passed") sensors.passed += 1;
        else if (firing.result === "failed") sensors.failed += 1;
      }
      if (unit.completed_at && (latest === null || unit.completed_at > latest)) {
        latest = unit.completed_at;
      }
    }
  }

  const startedAt = stringOrNull(record.started_at);
  return {
    workflowId: stringOrNull(record.workflow_id),
    scope: stringOrNull(record.scope),
    startedAt,
    durationMinutes: durationMinutes(startedAt, latest),
    stages,
    byPhase,
    sensors,
    source: "runtime-graph",
  };
}

function durationMinutes(start: string | null, end: string | null): number | null {
  if (!start || !end) return null;
  const ms = Date.parse(end) - Date.parse(start);
  if (Number.isNaN(ms) || ms < 0) return null;
  return Math.round(ms / 60000);
}

function normalizeOutcome(value: string | undefined): "approved" | "failed" | "pending" {
  if (value === "approved" || value === "failed" || value === "pending") return value;
  return "pending";
}

function emptyCounts(): CountSet {
  return { total: 0, approved: 0, failed: 0, pending: 0 };
}

function addOutcome(target: CountSet, outcome: "approved" | "failed" | "pending"): void {
  target.total += 1;
  target[outcome] += 1;
}

function countSet(value: unknown): CountSet | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  if (typeof record.total !== "number") return null;
  return {
    total: record.total,
    approved: typeof record.approved === "number" ? record.approved : 0,
    failed: typeof record.failed === "number" ? record.failed : 0,
    pending: typeof record.pending === "number" ? record.pending : 0,
  };
}

function phaseMap(value: unknown): Record<string, CountSet> {
  if (!value || typeof value !== "object") return {};
  const result: Record<string, CountSet> = {};
  for (const [phase, counts] of Object.entries(value as Record<string, unknown>)) {
    const parsed = countSet(counts);
    if (parsed) result[phase] = parsed;
  }
  return result;
}

function sensorCounts(value: unknown): { total: number; passed: number; failed: number } {
  if (!value || typeof value !== "object") return { total: 0, passed: 0, failed: 0 };
  const record = value as Record<string, unknown>;
  return {
    total: typeof record.total === "number" ? record.total : 0,
    passed: typeof record.passed === "number" ? record.passed : 0,
    failed: typeof record.failed === "number" ? record.failed : 0,
  };
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
