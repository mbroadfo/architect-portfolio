/** Snapshot returned by the local observer API. */

export type StageState =
  | "pending"
  | "in-progress"
  | "awaiting-approval"
  | "revising"
  | "completed"
  | "skipped"
  | "unknown";

export type ApprovalCode =
  | "awaiting-approval"
  | "revising"
  | "in-progress"
  | "ready-to-advance"
  | "completed"
  | "not-started"
  | "unknown";

export type TimelineImportance = "milestone" | "decision" | "detail";

export interface StageView {
  slug: string;
  name: string;
  number: string | null;
  phase: string;
  state: StageState;
  /** Plan suffix from the state file, such as EXECUTE or SKIP. */
  suffix: string | null;
  inPlan: boolean;
}

export interface PhaseView {
  id: string;
  label: string;
  /** Phase Progress value from the state file, when present. */
  status: string | null;
  stages: StageView[];
}

export interface TimelineEvent {
  id: string;
  timestamp: string | null;
  event: string;
  title: string;
  summary: string;
  stage: string | null;
  phase: string | null;
  fields: Record<string, string>;
  /** Audit file name, discovered from the record. */
  source: string;
  importance: TimelineImportance;
}

export interface DecisionRecord {
  id: string;
  text: string;
  madeAt: string | null;
  source: string;
  origin: string;
  kind: "product" | "process" | "audit";
}

export interface ArtifactLink {
  /** Path relative to the workspace, using forward slashes. */
  path: string;
  title: string;
  phase: string | null;
  stage: string | null;
}

export interface PendingGate {
  stage: string;
  stageName: string;
  state: "awaiting-approval" | "revising";
  since: string | null;
  detail: string;
}

export interface ApprovalStatus {
  code: ApprovalCode;
  label: string;
  stage: string | null;
  stageName: string | null;
}

export interface StageCounts {
  completed: number;
  active: number;
  pending: number;
  skipped: number;
  total: number;
}

export interface RuntimeSummaryView {
  workflowId: string | null;
  scope: string | null;
  startedAt: string | null;
  durationMinutes: number | null;
  stages: { total: number; approved: number; failed: number; pending: number };
  byPhase: Record<string, { total: number; approved: number; failed: number; pending: number }>;
  sensors: { total: number; passed: number; failed: number };
  source: "aidlc-command" | "runtime-graph";
}

export interface IntentSummary {
  dirName: string;
  slug: string | null;
  uuid: string | null;
  status: string | null;
  scope: string | null;
  active: boolean;
}

export interface SourceNote {
  path: string;
  role: string;
  ok: boolean;
}

export interface CommandNote {
  name: string;
  ok: boolean;
  error?: string;
}

export interface IntentSnapshot {
  dirName: string;
  slug: string | null;
  uuid: string | null;
  recordStatus: string | null;
  project: string | null;
  projectType: string | null;
  scope: string | null;
  plan: string | null;
  depth: string | null;
  guardPolicy: string | null;
  review: string | null;
  phase: string | null;
  phaseLabel: string | null;
  currentStage: string | null;
  currentStageName: string | null;
  nextStage: string | null;
  nextStageName: string | null;
  lastCompletedStage: string | null;
  lastCompletedStageName: string | null;
  workflowStatus: string | null;
  updatedAt: string | null;
  activeAgent: string | null;
  approval: ApprovalStatus;
  phases: PhaseView[];
  pendingGates: PendingGate[];
  counts: StageCounts;
  timeline: TimelineEvent[];
  decisions: DecisionRecord[];
  artifacts: ArtifactLink[];
  runtime: RuntimeSummaryView | null;
  stateFound: boolean;
  auditFiles: string[];
}

export interface Snapshot {
  ok: boolean;
  generatedAt: string;
  workspace: string;
  readOnly: true;
  warnings: string[];
  commands: CommandNote[];
  sources: SourceNote[];
  space: string | null;
  spaces: string[];
  intents: IntentSummary[];
  intent: IntentSnapshot | null;
}
