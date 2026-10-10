import path from "node:path";
import { deriveApproval, pendingGates } from "./approval.ts";
import { commandArgs, parseJson, runAidlc, type CliName, type CliOutput } from "./cli.ts";
import { parseAudit, sortEvents } from "./parse-audit.ts";
import { parseDecisionTables } from "./parse-decisions.ts";
import { displayState, isSkipSuffix, normalizePhase, parseState } from "./parse-state.ts";
import { isDirectory, listDir, pathExists, readText, textWasTruncated } from "./read-only-fs.ts";
import { summaryFromCommand, summaryFromGraph } from "./runtime-summary.ts";
import { firstHeading } from "../shared/markdown.ts";
import { humanizeAgent, humanizeSlug, safeFileSlug, titleCasePhase, toPosix, truncate } from "../shared/text.ts";
import type {
  ArtifactLink,
  CommandNote,
  DecisionRecord,
  IntentSnapshot,
  IntentSummary,
  Snapshot,
  SourceNote,
  StageView,
  TimelineEvent,
} from "../shared/types.ts";

const PHASE_ORDER = ["initialization", "ideation", "inception", "construction", "operation"];
const GRAPH_CANDIDATES = [
  ".claude/tools/data/stage-graph.json",
  ".kiro/tools/data/stage-graph.json",
  ".codex/tools/data/stage-graph.json",
  ".cursor/tools/data/stage-graph.json",
  ".aidlc/tools/data/stage-graph.json",
];

export interface CollectOptions {
  intent?: string | null;
  space?: string | null;
  /** Pass null to skip AI-DLC commands. Omit to run the read-only commands. */
  runCli?: ((name: CliName, workspace: string) => Promise<CliOutput>) | null;
}

interface StageMeta {
  name: string;
  number: string | null;
  phase: string | null;
}

interface IntentRow {
  dirName: string;
  slug: string | null;
  uuid: string | null;
  status: string | null;
  scope: string | null;
  active: boolean;
}

export async function collectSnapshot(workspaceInput: string, options: CollectOptions = {}): Promise<Snapshot> {
  const workspace = path.resolve(workspaceInput);
  const generatedAt = new Date().toISOString();
  const warnings: string[] = [];
  const sources: SourceNote[] = [];
  const commands: CommandNote[] = [];

  const blank = (extra?: string): Snapshot => ({
    ok: pathExists(workspace) && isDirectory(workspace),
    generatedAt,
    workspace,
    readOnly: true,
    warnings: extra ? [extra, ...warnings] : warnings,
    commands,
    sources,
    space: null,
    spaces: [],
    intents: [],
    intent: null,
  });

  if (!pathExists(workspace) || !isDirectory(workspace)) {
    return blank("Workspace path is not a directory.");
  }

  try {
    return await readWorkspace(workspace, options, warnings, sources, commands, generatedAt);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    warnings.push(`The observer could not finish reading this workspace: ${truncate(message, 240)}`);
    return blank();
  }
}

async function readWorkspace(
  workspace: string,
  options: CollectOptions,
  warnings: string[],
  sources: SourceNote[],
  commands: CommandNote[],
  generatedAt: string,
): Promise<Snapshot> {
  const aidlcRoot = path.join(workspace, "aidlc");
  if (!isDirectory(aidlcRoot)) {
    warnings.push("No aidlc directory was found. Point the observer at an AI-DLC project.");
    return {
      ok: true,
      generatedAt,
      workspace,
      readOnly: true,
      warnings,
      commands,
      sources,
      space: null,
      spaces: [],
      intents: [],
      intent: null,
    };
  }

  const cli = await readCommands(workspace, options, commands, warnings);
  const discoveredSpaces = listChildDirs(path.join(aidlcRoot, "spaces"));
  const cursorSpace = readCursor(path.join(aidlcRoot, "active-space"));
  if (cursorSpace !== null) {
    sources.push({ path: "aidlc/active-space", role: "Active space cursor", ok: true });
  }

  const spaces = unique([
    ...cli.spaces,
    ...discoveredSpaces,
    ...(cursorSpace ? [cursorSpace] : []),
  ]).filter((name) => safeFileSlug(name));

  let space = chooseSpace(options.space, cli.space, cursorSpace, discoveredSpaces);
  if (options.space && options.space !== space) {
    warnings.push(`Space "${options.space}" was not found. Showing ${space ?? "no space"}.`);
  }
  if (!space) {
    warnings.push("No AI-DLC space was found.");
    return {
      ok: true,
      generatedAt,
      workspace,
      readOnly: true,
      warnings,
      commands,
      sources,
      space: null,
      spaces,
      intents: [],
      intent: null,
    };
  }

  const spaceDir = path.join(aidlcRoot, "spaces", space);
  const intentsDir = path.join(spaceDir, "intents");
  const intentCursor = readCursor(path.join(intentsDir, "active-intent"));
  if (intentCursor !== null) {
    sources.push({
      path: `aidlc/spaces/${space}/intents/active-intent`,
      role: "Active workflow cursor",
      ok: true,
    });
  }

  const fileIntents = readIntentFile(path.join(intentsDir, "intents.json"), space, warnings, sources);
  const dirIntents = listChildDirs(intentsDir).filter((name) => safeFileSlug(name));
  const intents = mergeIntents(cli.intents, fileIntents, dirIntents, cli.space === space ? cli.activeIntent : null, intentCursor);

  const requested = options.intent ?? null;
  const matches = requested
    ? intents.filter((item) => item.dirName === requested || item.slug === requested)
    : [];
  if (requested && matches.length === 0) {
    warnings.push(`Workflow "${requested}" was not found. Showing the active workflow instead.`);
  } else if (requested && matches.length > 1) {
    warnings.push(`"${requested}" matches more than one workflow. Showing ${matches[0]?.dirName}.`);
  }
  const selected = matches[0] ?? selectIntent(intents, null);

  const stageMeta = readStageGraph(workspace, warnings, sources);
  const activeName = cli.activeIntent ?? intentCursor;
  const summaryJson = selected && selected.dirName === activeName ? cli.summary : null;
  const intent = selected
    ? readIntent(workspace, space, selected, stageMeta, summaryJson, warnings, sources)
    : null;

  if (!selected) warnings.push("No workflow record was found in this space.");

  return {
    ok: true,
    generatedAt,
    workspace,
    readOnly: true,
    warnings,
    commands,
    sources,
    space,
    spaces,
    intents: intents.map((item) => ({
      dirName: item.dirName,
      slug: item.slug,
      uuid: item.uuid,
      status: item.status,
      scope: item.scope,
      active: selected ? item.dirName === selected.dirName : item.active,
    })),
    intent,
  };
}

async function readCommands(
  workspace: string,
  options: CollectOptions,
  commands: CommandNote[],
  warnings: string[],
): Promise<{
  space: string | null;
  spaces: string[];
  activeIntent: string | null;
  intents: IntentRow[];
  summary: unknown;
}> {
  const empty = { space: null, spaces: [], activeIntent: null, intents: [], summary: null };
  if (options.runCli === null) return empty;
  const run = options.runCli ?? runAidlc;

  const [intentOut, spaceOut, summaryOut] = await Promise.all([
    run("intent-list", workspace),
    run("space-list", workspace),
    run("runtime-summary", workspace),
  ]);

  commands.push(note("intent-list", intentOut));
  commands.push(note("space-list", spaceOut));
  commands.push(note("runtime-summary", summaryOut));

  const failed = commands.filter((item) => !item.ok && !/no runtime-graph/i.test(item.error ?? ""));
  if (failed.length > 0 && failed.length === commands.length) {
    warnings.push("AI-DLC commands were not available. The observer is using the record files only.");
  } else {
    for (const item of failed) {
      warnings.push(`Read-only command ${item.name} failed: ${item.error ?? "unknown error"}`);
    }
  }

  const spaceJson = spaceOut.ok ? asRecord(parseJson(spaceOut.stdout)) : null;
  const intentJson = intentOut.ok ? asRecord(parseJson(intentOut.stdout)) : null;
  const spaces = Array.isArray(spaceJson?.spaces)
    ? spaceJson.spaces
        .map((item) => (asRecord(item)?.name))
        .filter((name): name is string => typeof name === "string")
    : [];

  const intents = Array.isArray(intentJson?.intents)
    ? intentJson.intents.flatMap((item) => {
        const record = asRecord(item);
        if (!record || typeof record.dirName !== "string" || !safeFileSlug(record.dirName)) return [];
        return [{
          dirName: record.dirName,
          slug: typeof record.slug === "string" ? record.slug : null,
          uuid: typeof record.uuid === "string" ? record.uuid : null,
          status: typeof record.status === "string" ? record.status : null,
          scope: null,
          active: record.active === true,
        } satisfies IntentRow];
      })
    : [];

  return {
    space: typeof spaceJson?.active === "string" ? spaceJson.active : null,
    spaces,
    activeIntent: typeof intentJson?.active === "string" ? intentJson.active : null,
    intents,
    summary: summaryOut.ok ? parseJson(summaryOut.stdout) : null,
  };
}

function readIntent(
  workspace: string,
  space: string,
  selected: IntentRow,
  stageMeta: Map<string, StageMeta>,
  summaryJson: unknown,
  warnings: string[],
  sources: SourceNote[],
): IntentSnapshot {
  const recordRel = `aidlc/spaces/${space}/intents/${selected.dirName}`;
  const recordDir = path.join(workspace, "aidlc", "spaces", space, "intents", selected.dirName);
  const statePath = path.join(recordDir, "aidlc-state.md");
  const stateText = safeRead(statePath, warnings, `${recordRel}/aidlc-state.md`);
  const stateFound = stateText !== null;
  if (stateFound && textWasTruncated(statePath)) {
    warnings.push("The state file was longer than the observer reads, so the view may be partial.");
  }
  sources.push({
    path: `${recordRel}/aidlc-state.md`,
    role: "Workflow state",
    ok: stateFound,
  });

  const parsed = parseState(stateText ?? "");
  if (stateFound) warnings.push(...parsed.warnings.filter((warning) => warning !== "State file is empty."));
  if (stateText === "") warnings.push("State file is empty.");

  const description = readProjectDescription(path.join(recordDir, "project-description.json"), recordRel, warnings, sources);
  const fields = parsed.fields;
  const currentStage = stageField(fields["Current Stage"]) ?? stageField(fields["In Progress"]);
  const nextStage = stageField(fields["Next Stage"]);
  const lastCompleted = stageField(fields["Last Completed Stage"]);
  let stages = buildStages(parsed.stages, stageMeta);
  if (stages.length === 0 && currentStage) {
    const meta = stageMeta.get(currentStage);
    stages = [{
      slug: currentStage,
      name: meta?.name ?? humanizeSlug(currentStage),
      number: meta?.number ?? null,
      phase: normalizePhase(fields["Lifecycle Phase"] ?? "") || meta?.phase || "unknown",
      state: "unknown",
      suffix: null,
      inPlan: true,
    }];
  }
  const phaseStatus = parsed.phaseStatus;
  const phases = groupPhases(stages, phaseStatus);
  const nameOf = (slug: string | null): string | null => {
    if (!slug) return null;
    return stages.find((stage) => stage.slug === slug)?.name ?? stageMeta.get(slug)?.name ?? humanizeSlug(slug);
  };

  const gateStages = stages.map((stage) => ({ slug: stage.slug, name: stage.name, state: stage.state }));
  if (currentStage && !gateStages.some((stage) => stage.slug === currentStage)) {
    gateStages.push({
      slug: currentStage,
      name: nameOf(currentStage) ?? currentStage,
      state: "unknown",
    });
  }

  const audit = readAudit(recordDir, recordRel, warnings, sources);
  const gateResult = pendingGates(gateStages, audit.events);
  warnings.push(...gateResult.warnings);

  const decisions = readDecisions(recordDir, workspace, audit.events, warnings);
  const artifacts = readArtifacts(recordDir, workspace);

  const graphPath = path.join(recordDir, "runtime-graph.json");
  const graphText = safeRead(graphPath, warnings, `${recordRel}/runtime-graph.json`);
  let graphValue: unknown = null;
  if (graphText !== null) {
    sources.push({ path: `${recordRel}/runtime-graph.json`, role: "Runtime graph", ok: true });
    try {
      graphValue = JSON.parse(graphText) as unknown;
    } catch {
      warnings.push("runtime-graph.json could not be parsed. Session counts fall back to the summary command.");
      sources[sources.length - 1] = { path: `${recordRel}/runtime-graph.json`, role: "Runtime graph", ok: false };
    }
  }

  const phaseOf = (slug: string): string => stages.find((stage) => stage.slug === slug)?.phase ?? stageMeta.get(slug)?.phase ?? "unknown";
  const runtime = summaryFromCommand(summaryJson) ?? summaryFromGraph(graphValue, phaseOf);
  if (!runtime && stateFound) {
    warnings.push("Session summary is unavailable until a runtime graph exists.");
  }

  const approval = deriveApproval({
    workflowStatus: emptyToNull(fields["Status"]),
    currentStage,
    stages: gateStages,
  });

  if (artifacts.length >= 200) warnings.push("Artifact list stopped at 200 files.");

  return {
    dirName: selected.dirName,
    slug: selected.slug,
    uuid: selected.uuid,
    recordStatus: selected.status,
    project: emptyToNull(fields["Project"]) ?? description,
    projectType: emptyToNull(fields["Project Type"]),
    scope: emptyToNull(fields["Scope"]) ?? selected.scope,
    plan: emptyToNull(fields["Plan"]),
    depth: emptyToNull(fields["Depth"]),
    guardPolicy: emptyToNull(fields["Guard Policy"]),
    review: emptyToNull(fields["Review Override"]),
    phase: emptyToNull(fields["Lifecycle Phase"]),
    phaseLabel: emptyToNull(fields["Lifecycle Phase"]) ? titleCasePhase(fields["Lifecycle Phase"]) : null,
    currentStage,
    currentStageName: nameOf(currentStage),
    nextStage,
    nextStageName: nameOf(nextStage),
    lastCompletedStage: lastCompleted,
    lastCompletedStageName: nameOf(lastCompleted),
    workflowStatus: emptyToNull(fields["Status"]),
    updatedAt: emptyToNull(fields["Last Updated"]),
    activeAgent: humanizeAgent(fields["Active Agent"]),
    approval,
    phases,
    pendingGates: gateResult.gates,
    counts: countStages(stages),
    timeline: audit.events,
    decisions,
    artifacts,
    runtime,
    stateFound,
    auditFiles: audit.files,
  };
}

function buildStages(
  parsed: { slug: string; state: import("../shared/types.ts").StageState; suffix: string; phase: string }[],
  stageMeta: Map<string, StageMeta>,
): StageView[] {
  return parsed.map((stage) => {
    const meta = stageMeta.get(stage.slug);
    const phase = stage.phase !== "unknown" ? stage.phase : meta?.phase ?? "unknown";
    return {
      slug: stage.slug,
      name: meta?.name ?? humanizeSlug(stage.slug),
      number: meta?.number ?? null,
      phase,
      state: displayState(stage),
      suffix: stage.suffix || null,
      inPlan: !isSkipSuffix(stage.suffix),
    };
  });
}

function groupPhases(stages: StageView[], phaseStatus: Record<string, string>) {
  const ids: string[] = [];
  for (const stage of stages) {
    if (!ids.includes(stage.phase)) ids.push(stage.phase);
  }
  ids.sort((a, b) => {
    const ai = PHASE_ORDER.indexOf(a);
    const bi = PHASE_ORDER.indexOf(b);
    if (ai === -1 && bi === -1) return a.localeCompare(b);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
  return ids.map((id) => ({
    id,
    label: titleCasePhase(id),
    status: phaseStatus[id] ?? null,
    stages: stages.filter((stage) => stage.phase === id),
  }));
}

function countStages(stages: StageView[]) {
  const counts = { completed: 0, active: 0, pending: 0, skipped: 0, total: stages.length };
  for (const stage of stages) {
    if (stage.state === "completed") counts.completed += 1;
    else if (stage.state === "in-progress" || stage.state === "awaiting-approval" || stage.state === "revising") counts.active += 1;
    else if (stage.state === "skipped") counts.skipped += 1;
    else counts.pending += 1;
  }
  return counts;
}

function readAudit(
  recordDir: string,
  recordRel: string,
  warnings: string[],
  sources: SourceNote[],
): { events: TimelineEvent[]; files: string[] } {
  const auditDir = path.join(recordDir, "audit");
  const entries = listDir(auditDir);
  if (!entries) {
    warnings.push("No audit directory was found for this workflow.");
    return { events: [], files: [] };
  }
  const files = entries
    .filter((entry) => !entry.isDirectory && /\.markdown?$/i.test(entry.name) && safeFileSlug(entry.name))
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b));
  if (files.length === 0) {
    warnings.push("The audit directory has no Markdown logs yet.");
    return { events: [], files: [] };
  }

  const events: TimelineEvent[] = [];
  for (const name of files) {
    const full = path.join(auditDir, name);
    const text = safeRead(full, warnings, `${recordRel}/audit/${name}`);
    sources.push({ path: `${recordRel}/audit/${name}`, role: "Audit log", ok: text !== null });
    if (text === null) continue;
    if (textWasTruncated(full)) warnings.push(`Audit file ${name} was truncated while reading.`);
    const parsed = parseAudit(text, name);
    warnings.push(...parsed.warnings);
    events.push(...parsed.events);
  }
  return { events: sortEvents(events), files };
}

function readDecisions(recordDir: string, workspace: string, events: TimelineEvent[], warnings: string[]): DecisionRecord[] {
  const files = walkMarkdown(recordDir, workspace).filter((file) => /decision/i.test(path.basename(file)));
  const decisions: DecisionRecord[] = [];
  for (const file of files) {
    const text = safeRead(file, warnings, toPosix(path.relative(workspace, file)));
    if (!text) continue;
    const parsed = parseDecisionTables(text, toPosix(path.relative(workspace, file)));
    warnings.push(...parsed.warnings);
    decisions.push(...parsed.decisions);
  }
  for (const event of events) {
    if (event.event !== "DECISION_RECORDED") continue;
    decisions.push({
      id: event.id,
      text: event.summary,
      madeAt: event.timestamp,
      source: event.stage ?? event.source,
      origin: event.source,
      kind: "audit",
    });
  }
  return decisions;
}

function readArtifacts(recordDir: string, workspace: string): ArtifactLink[] {
  return walkMarkdown(recordDir, workspace)
    .filter((file) => path.basename(file) !== "aidlc-state.md")
    .slice(0, 200)
    .map((file) => {
      const rel = toPosix(path.relative(workspace, file));
      const intentRel = toPosix(path.relative(recordDir, file));
      const parts = intentRel.split("/");
      const text = readText(file);
      const title = (text && firstHeading(text)) || humanizeSlug(path.basename(file, path.extname(file)));
      return {
        path: rel,
        title,
        phase: parts.length >= 2 ? parts[0] ?? null : null,
        stage: parts.length >= 3 ? parts[1] ?? null : null,
      };
    });
}

function walkMarkdown(dir: string, workspace: string): string[] {
  const found: string[] = [];
  const visit = (current: string): void => {
    if (found.length > 400) return;
    const entries = listDir(current);
    if (!entries) return;
    for (const entry of [...entries].sort((a, b) => a.name.localeCompare(b.name))) {
      if (entry.name.startsWith(".")) continue;
      const full = path.join(current, entry.name);
      if (entry.isDirectory) {
        if (entry.name === "audit" || entry.name === "node_modules") continue;
        visit(full);
      } else if (/\.markdown?$/i.test(entry.name)) {
        const rel = path.relative(workspace, full);
        if (!rel.startsWith("..") && !path.isAbsolute(rel)) found.push(full);
      }
    }
  };
  if (isDirectory(dir)) visit(dir);
  return found;
}

function readStageGraph(workspace: string, warnings: string[], sources: SourceNote[]): Map<string, StageMeta> {
  const meta = new Map<string, StageMeta>();
  for (const relative of GRAPH_CANDIDATES) {
    const full = path.join(workspace, relative);
    if (!pathExists(full)) continue;
    const text = safeRead(full, warnings, relative);
    sources.push({ path: relative, role: "Stage names", ok: text !== null });
    if (!text) return meta;
    try {
      const parsed = JSON.parse(text) as unknown;
      if (!Array.isArray(parsed)) {
        warnings.push("Stage graph was not a list. Stage names fall back to their identifiers.");
        return meta;
      }
      for (const item of parsed) {
        const record = asRecord(item);
        if (!record || typeof record.slug !== "string") continue;
        meta.set(record.slug, {
          name: typeof record.name === "string" && record.name.trim() ? record.name : humanizeSlug(record.slug),
          number: typeof record.number === "string" ? record.number : null,
          phase: typeof record.phase === "string" ? normalizePhase(record.phase) : null,
        });
      }
    } catch {
      warnings.push("Stage graph could not be parsed. Stage names fall back to their identifiers.");
    }
    return meta;
  }
  return meta;
}

function readProjectDescription(
  file: string,
  recordRel: string,
  warnings: string[],
  sources: SourceNote[],
): string | null {
  const text = safeRead(file, warnings, `${recordRel}/project-description.json`);
  if (text === null) return null;
  sources.push({ path: `${recordRel}/project-description.json`, role: "Project description", ok: true });
  try {
    const value = JSON.parse(text) as unknown;
    if (typeof value === "string") return value;
    const record = asRecord(value);
    if (typeof record?.description === "string") return record.description;
    if (typeof record?.project === "string") return record.project;
  } catch {
    warnings.push("project-description.json could not be parsed.");
  }
  return null;
}

function readIntentFile(file: string, space: string, warnings: string[], sources: SourceNote[]): IntentRow[] {
  const relative = `aidlc/spaces/${space}/intents/intents.json`;
  const text = safeRead(file, warnings, relative);
  if (text === null) return [];
  sources.push({ path: relative, role: "Workflow registry", ok: true });
  try {
    const parsed = JSON.parse(text) as unknown;
    if (!Array.isArray(parsed)) {
      warnings.push("intents.json was not a list. Workflows are discovered from directories.");
      return [];
    }
    return parsed.flatMap((item) => {
      const record = asRecord(item);
      if (!record || typeof record.dirName !== "string" || !safeFileSlug(record.dirName)) return [];
      return [{
        dirName: record.dirName,
        slug: typeof record.slug === "string" ? record.slug : null,
        uuid: typeof record.uuid === "string" ? record.uuid : null,
        status: typeof record.status === "string" ? record.status : null,
        scope: typeof record.scope === "string" ? record.scope : null,
        active: false,
      } satisfies IntentRow];
    });
  } catch {
    warnings.push("intents.json could not be parsed. Workflows are discovered from directories.");
    return [];
  }
}

function mergeIntents(
  fromCli: IntentRow[],
  fromFile: IntentRow[],
  directories: string[],
  cliActive: string | null,
  cursor: string | null,
): IntentRow[] {
  const byDir = new Map<string, IntentRow>();
  for (const name of directories) {
    byDir.set(name, { dirName: name, slug: null, uuid: null, status: null, scope: null, active: false });
  }
  for (const row of fromFile) {
    const existing = byDir.get(row.dirName);
    byDir.set(row.dirName, { ...(existing ?? row), ...row, active: false });
  }
  for (const row of fromCli) {
    const existing = byDir.get(row.dirName);
    byDir.set(row.dirName, {
      dirName: row.dirName,
      slug: row.slug ?? existing?.slug ?? null,
      uuid: row.uuid ?? existing?.uuid ?? null,
      status: row.status ?? existing?.status ?? null,
      scope: existing?.scope ?? row.scope,
      active: row.active,
    });
  }
  const rows = [...byDir.values()].sort((a, b) => a.dirName.localeCompare(b.dirName));
  const activeName = rows.some((row) => row.dirName === cliActive)
    ? cliActive
    : rows.some((row) => row.dirName === cursor)
      ? cursor
      : null;
  if (activeName) {
    for (const row of rows) row.active = row.dirName === activeName;
  }
  return rows;
}

function selectIntent(intents: IntentRow[], requested: string | null): IntentRow | null {
  if (requested) {
    const matches = intents.filter((item) => item.dirName === requested || item.slug === requested);
    if (matches.length === 1) return matches[0] ?? null;
  }
  return intents.find((item) => item.active)
    ?? intents.find((item) => item.status === "in-flight")
    ?? intents[0]
    ?? null;
}

function chooseSpace(
  requested: string | null | undefined,
  cliSpace: string | null,
  cursor: string | null,
  discovered: string[],
): string | null {
  const known = new Set(discovered);
  if (requested && known.has(requested)) return requested;
  if (cliSpace && (known.size === 0 || known.has(cliSpace))) return cliSpace;
  if (cursor && (known.size === 0 || known.has(cursor))) return cursor;
  if (known.has("default")) return "default";
  return discovered[0] ?? cliSpace ?? cursor;
}

function listChildDirs(dir: string): string[] {
  const entries = listDir(dir);
  if (!entries) return [];
  return entries
    .filter((entry) => entry.isDirectory && !entry.name.startsWith(".") && safeFileSlug(entry.name))
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b));
}

function readCursor(file: string): string | null {
  const text = readText(file);
  if (text === null) return null;
  const value = text.trim();
  return safeFileSlug(value) ? value : null;
}

function safeRead(file: string, warnings: string[], label: string): string | null {
  try {
    return readText(file);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    warnings.push(`Could not read ${label}: ${truncate(message, 160)}`);
    return null;
  }
}

function note(name: CliName, output: CliOutput): CommandNote {
  return {
    name: commandArgs(name, ".").slice(0, 4).join(" "),
    ok: output.ok,
    error: output.ok ? undefined : truncate(output.stderr || `Exited with code ${output.code ?? "unknown"}`, 240),
  };
}

function stageField(value: string | undefined): string | null {
  const trimmed = (value ?? "").trim();
  if (!trimmed) return null;
  if (/^(none|unknown|n\/a)$/i.test(trimmed)) return null;
  return trimmed;
}

function emptyToNull(value: string | undefined): string | null {
  const trimmed = (value ?? "").trim();
  return trimmed ? trimmed : null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}
