import type { FormEvent } from "react";
import { renderMarkdown } from "../shared/markdown.ts";
import { humanizeSlug, titleCasePhase, truncate } from "../shared/text.ts";
import type { ArtifactDocument } from "./api.ts";
import type {
  ApprovalCode,
  ArtifactLink,
  DecisionRecord,
  Snapshot,
  StageState,
  TimelineEvent,
} from "../shared/types.ts";

const STATE_LABEL: Record<StageState, string> = {
  completed: "Completed",
  "in-progress": "In progress",
  "awaiting-approval": "Needs you",
  revising: "Revising",
  pending: "Not started",
  skipped: "Skipped",
  unknown: "Unmarked",
};

export interface DashboardProps {
  snapshot: Snapshot | null;
  error: string | null;
  intent: string;
  auto: boolean;
  filter: "milestones" | "decisions" | "all";
  stage: string | null;
  workspaceInput: string;
  workspaceError: string | null;
  artifact: ArtifactLink | null;
  document: ArtifactDocument | null;
  documentError: string | null;
  onIntent: (value: string) => void;
  onAuto: (value: boolean) => void;
  onFilter: (value: "milestones" | "decisions" | "all") => void;
  onStage: (value: string) => void;
  onWorkspaceInput: (value: string) => void;
  onWatch: (event: FormEvent) => void;
  onRefresh: () => void;
  onOpenArtifact: (artifact: ArtifactLink) => void;
  onCloseArtifact: () => void;
}

export function Dashboard(props: DashboardProps) {
  const { snapshot } = props;
  const intent = snapshot?.intent ?? null;
  const events = visibleEvents(intent?.timeline ?? [], props.filter, props.stage);

  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <p className="eyebrow">Local · read only</p>
          <h1>AI-DLC Observer</h1>
          <p className="lede">Workflow, gates, and decisions for the architect supervising the team.</p>
        </div>
        <form className="watch" onSubmit={props.onWatch}>
          <label htmlFor="workspace">Workspace</label>
          <div className="watch-row">
            <input
              id="workspace"
              value={props.workspaceInput}
              onChange={(event) => props.onWorkspaceInput(event.target.value)}
              spellCheck={false}
              aria-describedby="workspace-hint"
            />
            <button type="submit">Watch</button>
          </div>
          <p id="workspace-hint" className="hint">
            {props.workspaceError ?? "Changing the path only changes what this process reads."}
          </p>
        </form>
      </header>

      <div className="toolbar">
        <label>
          Workflow
          <select
            value={props.intent || intent?.dirName || ""}
            onChange={(event) => props.onIntent(event.target.value)}
            disabled={!snapshot || snapshot.intents.length === 0}
          >
            {snapshot && snapshot.intents.length === 0 ? <option value="">No workflow yet</option> : null}
            {snapshot?.intents.map((item) => (
              <option key={item.dirName} value={item.dirName}>
                {item.slug ?? item.dirName}{item.status ? ` · ${item.status}` : ""}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={props.onRefresh}>Refresh</button>
        <label className="check">
          <input
            type="checkbox"
            checked={props.auto}
            onChange={(event) => props.onAuto(event.target.checked)}
          />
          Records every 5 seconds
        </label>
        <p className="updated">
          {snapshot ? `Read ${formatWhen(snapshot.generatedAt)}` : "Waiting for the first read"}
          {intent?.updatedAt ? ` · record ${formatWhen(intent.updatedAt)}` : ""}
        </p>
      </div>
      <p className="hint cadence">File records refresh every 5 seconds. AI-DLC commands run on Refresh and once a minute.</p>

      {props.error ? <p className="banner bad" role="alert">{props.error}</p> : null}
      {snapshot && snapshot.warnings.length > 0 ? (
        <details className="warnings">
          <summary>{snapshot.warnings.length} reading note{snapshot.warnings.length === 1 ? "" : "s"}</summary>
          <ul>
            {snapshot.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </details>
      ) : null}

      {!snapshot ? <p className="empty">Reading the workflow record…</p> : null}
      {snapshot && !intent ? (
        <section className="panel empty-panel">
          <h2>Nothing to show yet</h2>
          <p>No AI-DLC workflow was found in this workspace. The observer will keep reading until one appears.</p>
        </section>
      ) : null}

      {intent ? (
        <>
          <GateBanner intent={intent} />
          <section className="stats" aria-label="Workflow status">
            <Stat label="Phase" value={intent.phaseLabel ?? "Not recorded"} detail={phaseDetail(intent)} />
            <Stat label="Stage" value={intent.currentStageName ?? "Not recorded"} detail={intent.currentStage} />
            <Stat label="Approval" value={intent.approval.label} detail={approvalDetail(intent.approval.code)} tone={intent.approval.code} />
            <Stat
              label="Plan"
              value={intent.plan ?? intent.scope ?? "Not recorded"}
              detail={countLine(intent.counts)}
            />
          </section>

          <section className="panel">
            <div className="panel-head">
              <h2>Stages</h2>
              <p>Completed, active, and not started. Select a stage to filter the timeline.</p>
            </div>
            {intent.phases.length === 0 ? <p className="muted">The state file has no stage list.</p> : null}
            <div className="phases">
              {intent.phases.map((phase) => (
                <article key={phase.id} className="phase">
                  <header>
                    <h3>{phase.label}</h3>
                    {phase.status ? <span className="phase-status">{phase.status}</span> : null}
                  </header>
                  <ol>
                    {phase.stages.map((item) => (
                      <li key={item.slug}>
                        <button
                          type="button"
                          className={`chip state-${item.state}${props.stage === item.slug ? " is-selected" : ""}`}
                          aria-pressed={props.stage === item.slug}
                          onClick={() => props.onStage(item.slug)}
                        >
                          <span className="chip-num">{item.number ?? "·"}</span>
                          <span className="chip-name">{item.name}</span>
                          <span className="chip-state">{STATE_LABEL[item.state]}</span>
                        </button>
                      </li>
                    ))}
                  </ol>
                </article>
              ))}
            </div>
          </section>

          <div className="split">
            <section className="panel">
              <div className="panel-head">
                <h2>Activity</h2>
                <div className="filters" role="group" aria-label="Timeline filter">
                  <FilterButton current={props.filter} value="milestones" onFilter={props.onFilter}>Milestones</FilterButton>
                  <FilterButton current={props.filter} value="decisions" onFilter={props.onFilter}>Decisions</FilterButton>
                  <FilterButton current={props.filter} value="all" onFilter={props.onFilter}>Everything</FilterButton>
                </div>
              </div>
              {props.stage ? (
                <p className="muted">
                  Filtered to {intent.phases.flatMap((phase) => phase.stages).find((item) => item.slug === props.stage)?.name ?? props.stage}.
                  {" "}
                  <button type="button" className="link" onClick={() => props.onStage(props.stage ?? "")}>Show every stage</button>
                </p>
              ) : null}
              {events.length === 0 ? <p className="muted">No matching audit events.</p> : null}
              <ol className="timeline">
                {events.slice(-80).map((event) => (
                  <li key={event.id} className={`event importance-${event.importance}`}>
                    <time dateTime={event.timestamp ?? undefined}>{formatWhen(event.timestamp)}</time>
                    <div>
                      <p className="event-title">{event.summary}</p>
                      <p className="event-meta">{event.event} · {event.source}</p>
                      <EventDetails event={event} />
                    </div>
                  </li>
                ))}
              </ol>
              {events.length > 80 ? <p className="muted">Showing the latest 80 of {events.length} events.</p> : null}
            </section>

            <div className="side">
              <section className="panel">
                <div className="panel-head">
                  <h2>Decisions</h2>
                  <p>Architectural and product decisions recorded for this workflow.</p>
                </div>
                <DecisionList decisions={intent.decisions.filter((item) => item.kind !== "audit")} empty="No decision log was found in this workflow." />
                {intent.decisions.some((item) => item.kind === "audit") ? (
                  <details className="audit-decisions">
                    <summary>{intent.decisions.filter((item) => item.kind === "audit").length} prompts recorded in the audit</summary>
                    <DecisionList decisions={intent.decisions.filter((item) => item.kind === "audit")} empty="" />
                  </details>
                ) : null}
              </section>

              <section className="panel">
                <div className="panel-head">
                  <h2>Artifacts</h2>
                  <p>Markdown written for this workflow. Opening one does not change it.</p>
                </div>
                {intent.artifacts.length === 0 ? <p className="muted">No Markdown artifacts were found.</p> : null}
                <ul className="artifacts">
                  {intent.artifacts.map((item) => (
                    <li key={item.path}>
                      <button type="button" onClick={() => props.onOpenArtifact(item)}>
                        <span>{item.title}</span>
                        <small>{[item.phase ? titleCasePhase(item.phase) : null, item.stage ? humanizeSlug(item.stage) : null].filter(Boolean).join(" · ")}</small>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="panel">
                <div className="panel-head">
                  <h2>Session</h2>
                  <p>Counts from the runtime summary. The stage board is the full plan.</p>
                </div>
                {intent.runtime ? (
                  <dl className="facts">
                    <div><dt>Workflow</dt><dd>{intent.runtime.workflowId ?? "Not recorded"}</dd></div>
                    <div><dt>Duration</dt><dd>{intent.runtime.durationMinutes === null ? "In progress" : `${intent.runtime.durationMinutes} min`}</dd></div>
                    <div><dt>Started stages</dt><dd>{intent.runtime.stages.approved} approved · {intent.runtime.stages.pending} pending · {intent.runtime.stages.failed} failed</dd></div>
                    <div><dt>Sensors</dt><dd>{intent.runtime.sensors.passed} passed · {intent.runtime.sensors.failed} failed</dd></div>
                    <div><dt>Source</dt><dd>{intent.runtime.source === "aidlc-command" ? "aidlc runtime summary" : "runtime-graph.json"}</dd></div>
                  </dl>
                ) : <p className="muted">Session summary is not available yet.</p>}
                <dl className="facts context">
                  {intent.project ? <div><dt>Project</dt><dd>{truncate(intent.project, 280)}</dd></div> : null}
                  {intent.projectType ? <div><dt>Type</dt><dd>{intent.projectType}</dd></div> : null}
                  {intent.scope ? <div><dt>Scope</dt><dd>{intent.scope}</dd></div> : null}
                  {intent.depth ? <div><dt>Depth</dt><dd>{intent.depth}</dd></div> : null}
                  {intent.guardPolicy ? <div><dt>Guard policy</dt><dd>{intent.guardPolicy}</dd></div> : null}
                  {intent.review ? <div><dt>Review</dt><dd>{intent.review}</dd></div> : null}
                  {intent.activeAgent ? <div><dt>Active agent</dt><dd>{intent.activeAgent}</dd></div> : null}
                  {intent.nextStageName ? <div><dt>Next</dt><dd>{intent.nextStageName}</dd></div> : null}
                  {intent.lastCompletedStageName ? <div><dt>Last completed</dt><dd>{intent.lastCompletedStageName}</dd></div> : null}
                </dl>
              </section>
            </div>
          </div>
        </>
      ) : null}

      {snapshot ? (
        <footer className="foot">
          <p>This dashboard only reads AI-DLC records. It cannot approve a stage or change the workflow.</p>
          <details>
            <summary>Sources for this read</summary>
            <ul>
              {snapshot.sources.map((source) => (
                <li key={`${source.role}:${source.path}`}>
                  {source.ok ? "Read" : "Missing"} · {source.role} · {source.path}
                </li>
              ))}
              {snapshot.commands.map((command) => (
                <li key={command.name}>
                  {command.ok ? "Command ok" : "Command failed"} · {command.name}
                  {command.error ? ` · ${command.error}` : ""}
                </li>
              ))}
            </ul>
          </details>
        </footer>
      ) : null}

      {props.artifact ? (
        <div className="drawer-backdrop" onClick={props.onCloseArtifact}>
          <article
            className="drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="artifact-title"
            onClick={(event) => event.stopPropagation()}
          >
            <header>
              <div>
                <p className="eyebrow">Artifact</p>
                <h2 id="artifact-title">{props.document?.title ?? props.artifact.title}</h2>
                <p className="hint">{props.artifact.path}</p>
              </div>
              <button type="button" onClick={props.onCloseArtifact}>Close</button>
            </header>
            {props.documentError ? <p className="banner bad">{props.documentError}</p> : null}
            {!props.document && !props.documentError ? <p className="muted">Opening…</p> : null}
            {props.document?.truncated ? <p className="muted">This file was shortened for display.</p> : null}
            {props.document ? (
              <div
                className="prose"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(props.document.markdown) }}
              />
            ) : null}
          </article>
        </div>
      ) : null}
    </div>
  );
}

function GateBanner({ intent }: { intent: NonNullable<Snapshot["intent"]> }) {
  if (intent.pendingGates.length === 0 && intent.approval.code !== "awaiting-approval" && intent.approval.code !== "revising") {
    return null;
  }
  const gates = intent.pendingGates;
  return (
    <section className={`banner gate gate-${intent.approval.code}`} role="status">
      <p className="eyebrow">{intent.approval.code === "revising" ? "Revision" : "Approval gate"}</p>
      <h2>{intent.approval.label}</h2>
      {gates.length === 0 ? null : (
        <ul>
          {gates.map((gate) => (
            <li key={gate.stage}>
              <strong>{gate.stageName}</strong>
              {" · "}
              {gate.detail}
              {gate.since ? ` Waiting since ${formatWhen(gate.since)}.` : ""}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Stat({ label, value, detail, tone }: { label: string; value: string; detail: string | null; tone?: ApprovalCode }) {
  return (
    <article className={tone ? `stat tone-${tone}` : "stat"}>
      <p className="eyebrow">{label}</p>
      <h2>{value}</h2>
      {detail ? <p>{detail}</p> : null}
    </article>
  );
}

function FilterButton({
  current,
  value,
  onFilter,
  children,
}: {
  current: string;
  value: "milestones" | "decisions" | "all";
  onFilter: (value: "milestones" | "decisions" | "all") => void;
  children: string;
}) {
  return (
    <button type="button" className={current === value ? "is-on" : ""} aria-pressed={current === value} onClick={() => onFilter(value)}>
      {children}
    </button>
  );
}

function DecisionList({ decisions, empty }: { decisions: DecisionRecord[]; empty: string }) {
  if (decisions.length === 0) return empty ? <p className="muted">{empty}</p> : null;
  return (
    <ol className="decisions">
      {decisions.map((decision) => (
        <li key={`${decision.origin}:${decision.id}`}>
          <p className="decision-id">{decision.id}{decision.kind === "process" ? " · process" : ""}</p>
          <p>{decision.text}</p>
          <p className="event-meta">{[decision.madeAt, decision.source].filter(Boolean).join(" · ")}</p>
        </li>
      ))}
    </ol>
  );
}

function EventDetails({ event }: { event: TimelineEvent }) {
  const entries = Object.entries(event.fields).filter(([key]) => !["Stage", "Phase", "Details", "Decision", "Reply", "Picked"].includes(key));
  if (entries.length === 0) return null;
  return (
    <details>
      <summary>Details</summary>
      <dl>
        {entries.map(([key, value]) => (
          <div key={key}><dt>{key}</dt><dd>{value}</dd></div>
        ))}
      </dl>
    </details>
  );
}

function visibleEvents(events: TimelineEvent[], filter: "milestones" | "decisions" | "all", stage: string | null): TimelineEvent[] {
  return events.filter((event) => {
    if (stage && event.stage !== stage) return false;
    if (filter === "all") return true;
    if (filter === "decisions") return event.importance === "decision";
    return event.importance === "milestone";
  });
}

function phaseDetail(intent: NonNullable<Snapshot["intent"]>): string | null {
  const match = intent.phases.find((phase) => phase.label.toLowerCase() === (intent.phaseLabel ?? "").toLowerCase());
  return match?.status ?? intent.workflowStatus;
}

function approvalDetail(code: ApprovalCode): string {
  switch (code) {
    case "awaiting-approval":
      return "The team is blocked until you approve.";
    case "revising":
      return "A gate was rejected and the stage is being revised.";
    case "ready-to-advance":
      return "The current stage is approved.";
    case "in-progress":
      return "The team is still working this stage.";
    case "completed":
      return "The workflow status is completed.";
    case "not-started":
      return "This stage has not started.";
    default:
      return "The record does not say whether a person needs to act.";
  }
}

function countLine(counts: NonNullable<Snapshot["intent"]>["counts"]): string {
  return `${counts.completed} completed · ${counts.active} active · ${counts.pending} not started · ${counts.skipped} skipped`;
}

function formatWhen(value: string | null): string {
  if (!value) return "No timestamp";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
