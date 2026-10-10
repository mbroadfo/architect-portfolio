import type { TimelineEvent, TimelineImportance } from "../shared/types.ts";
import { basename, truncate } from "../shared/text.ts";

export interface ParsedAudit {
  events: TimelineEvent[];
  warnings: string[];
}

const DROP_FIELDS = new Set([
  "Validation Basis",
  "Review Finding Dispositions",
  "By Model",
  "Source Baseline",
  "Cache Read",
  "Cache Write",
  "Tokens In",
  "Tokens Out",
]);

const MILESTONES = new Set([
  "WORKFLOW_STARTED",
  "WORKFLOW_COMPLETED",
  "PHASE_STARTED",
  "PHASE_COMPLETED",
  "PHASE_VERIFIED",
  "STAGE_STARTED",
  "STAGE_COMPLETED",
  "STAGE_AWAITING_APPROVAL",
  "GATE_APPROVED",
  "GATE_REJECTED",
  "REVIEW_REQUESTED",
  "REVIEW_COMPLETED",
  "ERROR_LOGGED",
  "WORKSPACE_SCAFFOLDED",
  "WORKSPACE_SCANNED",
  "WORKSPACE_INITIALISED",
  "SCOPE_SAVED",
]);

const DECISIONS = new Set([
  "DECISION_RECORDED",
  "HUMAN_TURN",
  "QUESTION_REPLIED",
  "QUESTION_ANSWERED",
  "RULE_LEARNED",
]);

export function parseAudit(text: string, source: string): ParsedAudit {
  const warnings: string[] = [];
  if (!text.trim()) {
    return { events: [], warnings: [`Audit file ${source} is empty.`] };
  }

  const blocks = splitBlocks(text);
  const events: TimelineEvent[] = [];
  let order = 0;
  let malformed = 0;

  for (const block of blocks) {
    const parsed = parseBlock(block);
    if (!parsed.event && !parsed.title && Object.keys(parsed.fields).length === 0) {
      continue;
    }
    if (!parsed.event) {
      malformed += 1;
      continue;
    }
    const timestamp = normalizeTimestamp(parsed.fields["Timestamp"]);
    if (parsed.fields["Timestamp"] && !timestamp) {
      warnings.push(`Audit file ${source} has an event with an unreadable timestamp.`);
    }
    const summary = describeEvent(parsed.event, parsed.fields, parsed.title);
    events.push({
      id: `${source}:${order}`,
      timestamp,
      event: parsed.event,
      title: parsed.title || humanEvent(parsed.event),
      summary: summary.summary,
      stage: stageOf(parsed.fields),
      phase: parsed.fields["Phase"] ?? parsed.fields["From phase"] ?? null,
      fields: displayFields(parsed.fields),
      source,
      importance: summary.importance,
    });
    order += 1;
  }

  if (events.length === 0) {
    warnings.push(`Audit file ${source} has no readable events.`);
  } else if (malformed > 0) {
    warnings.push(`Audit file ${source} skipped ${malformed} block${malformed === 1 ? "" : "s"} without an event name.`);
  }

  return { events, warnings };
}

export function sortEvents(events: TimelineEvent[]): TimelineEvent[] {
  return events
    .map((event, index) => ({ event, index }))
    .sort((a, b) => {
      if (a.event.timestamp && b.event.timestamp) {
        const compared = a.event.timestamp.localeCompare(b.event.timestamp);
        if (compared !== 0) return compared;
      } else if (a.event.timestamp) {
        return -1;
      } else if (b.event.timestamp) {
        return 1;
      }
      return a.index - b.index;
    })
    .map((item, index) => ({ ...item.event, id: `${item.event.source}#${index}` }));
}

function splitBlocks(text: string): string[] {
  const chunks: string[][] = [];
  let current: string[] = [];
  const flush = (): void => {
    if (current.some((line) => line.trim())) chunks.push(current);
    current = [];
  };
  for (const line of text.split(/\r?\n/)) {
    if (/^---\s*$/.test(line)) {
      flush();
      continue;
    }
    if (/^##\s+/.test(line) && current.some((item) => /^##\s+/.test(item) || /^\*\*Event\*\*:/.test(item))) {
      flush();
    }
    current.push(line);
  }
  flush();
  return chunks.map((chunk) => chunk.join("\n"));
}

function parseBlock(block: string): { title: string; event: string | null; fields: Record<string, string> } {
  let title = "";
  let event: string | null = null;
  const fields: Record<string, string> = {};
  for (const line of block.split(/\r?\n/)) {
    const heading = /^##\s+(.+)$/.exec(line.trim());
    if (heading?.[1] && !title) {
      title = heading[1].trim();
      continue;
    }
    const field = /^\*\*(.+?)\*\*:\s*(.*)$/.exec(line.trim());
    if (!field?.[1]) continue;
    const key = field[1].trim();
    const value = (field[2] ?? "").trim();
    if (key === "Event" && value) event = value;
    else fields[key] = value;
  }
  return { title, event, fields };
}

function normalizeTimestamp(value: string | undefined): string | null {
  if (!value) return null;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return null;
  return new Date(parsed).toISOString().replace(".000Z", "Z");
}

function stageOf(fields: Record<string, string>): string | null {
  return fields["Stage"] || fields["Stage slug"] || null;
}

function displayFields(fields: Record<string, string>): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(fields)) {
    if (key === "Timestamp" || DROP_FIELDS.has(key) || !value) continue;
    if (key === "File" || key === "Output path") {
      result[key] = truncate(value.replaceAll("<project-dir>/", ""), 240);
      continue;
    }
    result[key] = truncate(value, 320);
  }
  return result;
}

function describeEvent(
  event: string,
  fields: Record<string, string>,
  title: string,
): { summary: string; importance: TimelineImportance } {
  const stage = stageOf(fields);
  const stageName = stage ? stage : "a stage";
  const importance: TimelineImportance = MILESTONES.has(event)
    ? "milestone"
    : DECISIONS.has(event)
      ? "decision"
      : "detail";

  switch (event) {
    case "WORKFLOW_STARTED":
      return { summary: fields["Scope"] ? `Workflow started on the ${fields["Scope"]} scope` : "Workflow started", importance };
    case "PHASE_STARTED":
      return { summary: `Phase started: ${label(fields["Phase"])}`, importance };
    case "PHASE_COMPLETED":
      return {
        summary: `Phase completed: ${label(fields["From phase"])} to ${label(fields["To phase"])}`,
        importance,
      };
    case "PHASE_VERIFIED":
      return { summary: `Phase verified${fields["Phase boundary"] ? `: ${fields["Phase boundary"]}` : ""}`, importance };
    case "STAGE_STARTED":
      return { summary: `Started ${stageName}${fields["Agent"] ? ` (${fields["Agent"]})` : ""}`, importance };
    case "STAGE_COMPLETED":
      return { summary: `Completed ${stageName}${fields["Details"] ? `. ${truncate(fields["Details"], 160)}` : ""}`, importance };
    case "STAGE_AWAITING_APPROVAL":
      return { summary: `Waiting for approval on ${stageName}`, importance };
    case "GATE_APPROVED":
      return { summary: `Approved ${stageName}${fields["User Input"] ? `: ${truncate(fields["User Input"], 120)}` : ""}`, importance };
    case "GATE_REJECTED":
      return { summary: `Rejected ${stageName}. The stage goes back for revision.`, importance };
    case "REVIEW_REQUESTED":
      return { summary: `Review requested${stage ? ` for ${stage}` : ""}`, importance };
    case "REVIEW_COMPLETED":
      return { summary: `Review completed${stage ? ` for ${stage}` : ""}`, importance };
    case "ERROR_LOGGED":
      return { summary: truncate(fields["Details"] || fields["Error"] || title || "An error was recorded", 200), importance };
    case "DECISION_RECORDED":
      return { summary: truncate(fields["Decision"] || title || "Decision recorded", 200), importance };
    case "HUMAN_TURN":
      return { summary: `You chose ${humanChoice(fields["Picked"]) ?? "a response"}`, importance };
    case "QUESTION_REPLIED":
      return { summary: `Reply recorded: ${truncate(fields["Reply"] || "response", 180)}`, importance };
    case "QUESTION_ANSWERED":
      return { summary: truncate(fields["Details"] || fields["Answer"] || "Question answered", 180), importance };
    case "ARTIFACT_CREATED":
    case "ARTIFACT_UPDATED": {
      const file = fields["File"] || fields["Output path"];
      const verb = event === "ARTIFACT_CREATED" ? "Created" : "Updated";
      return { summary: file ? `${verb} ${basename(file)}` : `${verb} an artifact`, importance: "detail" };
    }
    case "SENSOR_PASSED":
    case "SENSOR_FAILED":
    case "SENSOR_FIRED":
      return {
        summary: `${humanEvent(event)}${fields["Sensor ID"] ? `: ${fields["Sensor ID"]}` : ""}${stage ? ` on ${stage}` : ""}`,
        importance: "detail",
      };
    default:
      return { summary: truncate(fields["Details"] || title || humanEvent(event), 180), importance };
  }
}

function humanChoice(raw: string | undefined): string | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (Array.isArray(parsed)) {
      const parts = parsed.map((item) => String(item)).filter(Boolean);
      if (parts.length > 0) return parts.join(", ");
    }
  } catch {
    // The field is already plain text.
  }
  return raw;
}

function label(value: string | undefined): string {
  return value && value.trim() ? value.trim() : "unknown";
}

function humanEvent(event: string): string {
  return event
    .toLowerCase()
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
