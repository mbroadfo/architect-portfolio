import type { StageState } from "../shared/types.ts";

export interface ParsedCheckbox {
  slug: string;
  state: StageState;
  suffix: string;
  phase: string;
}

export interface ParsedState {
  fields: Record<string, string>;
  phaseStatus: Record<string, string>;
  stages: ParsedCheckbox[];
  warnings: string[];
}

const FIELD_PATTERN = /^(?:-\s+)?\*\*(.+?)\*\*:\s*(.*)$/;
const CHECKBOX_PATTERN =
  /^-\s+\[([ xXSRsr?\-])\]\s+(\S+)(?:\s+(?:—|–|--|-)\s+(.*))?$/;

export function parseState(text: string): ParsedState {
  const fields: Record<string, string> = {};
  const phaseStatus: Record<string, string> = {};
  const stages: ParsedCheckbox[] = [];
  const warnings: string[] = [];

  if (!text.trim()) {
    return { fields, phaseStatus, stages, warnings: ["State file is empty."] };
  }

  let section: "fields" | "phases" | "stages" = "fields";
  let phase = "unknown";
  let recognized = false;
  let ignoredMarker = false;

  for (const line of text.split(/\r?\n/)) {
    if (line.startsWith("## ")) {
      const title = line.slice(3).trim().toLowerCase();
      recognized = true;
      if (title.startsWith("phase progress")) section = "phases";
      else if (title.startsWith("stage progress")) section = "stages";
      else section = "fields";
      continue;
    }

    if (section === "stages" && line.startsWith("### ")) {
      phase = normalizePhase(line.slice(4));
      recognized = true;
      continue;
    }

    const checkbox = parseCheckbox(line);
    if (checkbox === "invalid") {
      ignoredMarker = true;
      continue;
    }
    if (checkbox) {
      stages.push({ ...checkbox, phase: section === "stages" ? phase : "unknown" });
      recognized = true;
      continue;
    }

    const field = parseField(line);
    if (!field) continue;
    recognized = true;
    if (section === "phases") {
      phaseStatus[normalizePhase(field.key)] = field.value.trim();
    } else if (section !== "stages") {
      fields[field.key] = field.value.trim();
    }
  }

  if (!recognized) {
    warnings.push("State file did not match the AI-DLC state format. Showing whatever could be read.");
  }
  if (ignoredMarker) {
    warnings.push("Ignored a stage line with an unrecognized checkbox marker.");
  }
  if (stages.length === 0 && !fields["Current Stage"] && !fields["In Progress"]) {
    warnings.push("State file has no stage plan and no current stage.");
  }

  const seen = new Set<string>();
  for (const stage of stages) {
    if (seen.has(stage.slug)) {
      warnings.push(`Stage "${stage.slug}" appears more than once. The later marker is used.`);
    }
    seen.add(stage.slug);
  }

  return { fields, phaseStatus, stages: dedupeStages(stages), warnings };
}

function dedupeStages(stages: ParsedCheckbox[]): ParsedCheckbox[] {
  const bySlug = new Map<string, ParsedCheckbox>();
  const order: string[] = [];
  for (const stage of stages) {
    if (!bySlug.has(stage.slug)) order.push(stage.slug);
    bySlug.set(stage.slug, stage);
  }
  return order.map((slug) => bySlug.get(slug)!);
}

function parseField(line: string): { key: string; value: string } | null {
  const match = FIELD_PATTERN.exec(line.trim());
  if (!match?.[1]) return null;
  return { key: match[1].trim(), value: match[2] ?? "" };
}

function parseCheckbox(line: string): Omit<ParsedCheckbox, "phase"> | "invalid" | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith("- [")) return null;
  const match = CHECKBOX_PATTERN.exec(trimmed);
  if (!match) return "invalid";
  const state = markerState(match[1] ?? "");
  if (!state) return "invalid";
  return {
    slug: match[2] ?? "",
    state,
    suffix: (match[3] ?? "").trim(),
  };
}

function markerState(marker: string): StageState | null {
  switch (marker.toLowerCase()) {
    case " ":
      return "pending";
    case "-":
      return "in-progress";
    case "?":
      return "awaiting-approval";
    case "r":
      return "revising";
    case "x":
      return "completed";
    case "s":
      return "skipped";
    default:
      return null;
  }
}

export function normalizePhase(value: string): string {
  return value
    .replace(/phase/gi, " ")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function isSkipSuffix(suffix: string | null | undefined): boolean {
  return /^skip\b/i.test((suffix ?? "").trim());
}

export function displayState(stage: Pick<ParsedCheckbox, "state" | "suffix">): StageState {
  if (stage.state === "pending" && isSkipSuffix(stage.suffix)) return "skipped";
  return stage.state;
}
