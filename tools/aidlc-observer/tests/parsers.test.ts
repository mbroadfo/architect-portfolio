import { describe, expect, it } from "vitest";
import { pendingGates } from "../server/approval.ts";
import { parseAudit, sortEvents } from "../server/parse-audit.ts";
import { parseDecisionTables } from "../server/parse-decisions.ts";
import { parseState } from "../server/parse-state.ts";
import { renderMarkdown } from "../shared/markdown.ts";
import type { TimelineEvent } from "../shared/types.ts";

describe("parseState", () => {
  it("reads checkbox markers, including CRLF lines", () => {
    const parsed = parseState(
      [
        "# State",
        "## Stage Progress",
        "### INCEPTION PHASE",
        "- [?] refined-mockups \u2014 EXECUTE",
        "- [R] domain-design \u2014 EXECUTE",
        "- [S] market-research \u2014 SKIP",
        "- [x] intent-capture \u2014 EXECUTE",
        "- [-] code-generation \u2014 EXECUTE",
        "- [ ] later \u2014 EXECUTE",
        "- [ ] planned-skip \u2014 SKIP",
      ].join("\r\n"),
    );
    const bySlug = Object.fromEntries(parsed.stages.map((stage) => [stage.slug, stage.state]));
    expect(bySlug["refined-mockups"]).toBe("awaiting-approval");
    expect(bySlug["domain-design"]).toBe("revising");
    expect(bySlug["market-research"]).toBe("skipped");
    expect(bySlug["intent-capture"]).toBe("completed");
    expect(bySlug["code-generation"]).toBe("in-progress");
    expect(bySlug.later).toBe("pending");
    expect(bySlug["planned-skip"]).toBe("pending");
    expect(parsed.stages.find((stage) => stage.slug === "later")?.phase).toBe("inception");
  });

  it("warns on an empty or unrecognized state file", () => {
    expect(parseState("").warnings).toContain("State file is empty.");
    const garbage = parseState("this is not a state file\n- [z] nope \u2014 BAD\n");
    expect(garbage.stages).toEqual([]);
    expect(garbage.warnings.length).toBeGreaterThan(0);
  });
});

describe("parseAudit", () => {
  it("sorts events by timestamp and keeps unreadable times", () => {
    const parsed = parseAudit(
      [
        "## Later",
        "**Timestamp**: 2026-10-10T12:05:00Z",
        "**Event**: STAGE_COMPLETED",
        "**Stage**: intent-capture",
        "---",
        "## Earlier in the file but later on the clock",
        "**Timestamp**: 2026-10-10T12:01:00Z",
        "**Event**: STAGE_STARTED",
        "**Stage**: intent-capture",
        "---",
        "## Broken",
        "**Timestamp**: not-a-date",
        "**Event**: ERROR_LOGGED",
        "**Details**: Clock was unreadable",
      ].join("\n"),
      "shard.md",
    );
    const sorted = sortEvents(parsed.events);
    expect(sorted.map((event) => event.event)).toEqual([
      "STAGE_STARTED",
      "STAGE_COMPLETED",
      "ERROR_LOGGED",
    ]);
    expect(sorted[2]?.timestamp).toBeNull();
    expect(parsed.warnings.some((warning) => warning.includes("unreadable timestamp"))).toBe(true);
  });

  it("does not throw on empty or prose-only logs", () => {
    expect(parseAudit("", "empty.md").events).toEqual([]);
    expect(parseAudit("just prose\nwithout fields\n", "notes.md").events).toEqual([]);
  });
});

describe("parseDecisionTables", () => {
  it("separates product and process tables", () => {
    const parsed = parseDecisionTables(
      [
        "## Decisions",
        "| ID | Decision | Made at | Source |",
        "|----|----------|---------|--------|",
        "| D-01 | Publish three exhibits | Intent capture | intent-statement |",
        "",
        "## Process Decisions",
        "| ID | Decision | Source |",
        "|----|----------|--------|",
        "| P-01 | Keep supervision read only | owner |",
      ].join("\n"),
      "decision-log.md",
    );
    expect(parsed.decisions.map((decision) => [decision.id, decision.kind])).toEqual([
      ["D-01", "product"],
      ["P-01", "process"],
    ]);
  });

  it("warns when a decision file has no table", () => {
    const parsed = parseDecisionTables("No table lives here.", "decision-log.md");
    expect(parsed.decisions).toEqual([]);
    expect(parsed.warnings[0]).toMatch(/No decision table/);
  });
});

describe("pendingGates", () => {
  it("drops a gate after approval and keeps a rejection", () => {
    const stages = [
      { slug: "refined-mockups", name: "Refined Mockups", state: "awaiting-approval" as const },
      { slug: "domain-design", name: "Domain Design", state: "revising" as const },
    ];
    const events = [
      event("STAGE_AWAITING_APPROVAL", "intent-capture", "2026-10-10T12:00:00Z"),
      event("GATE_APPROVED", "intent-capture", "2026-10-10T12:05:00Z"),
      event("STAGE_AWAITING_APPROVAL", "refined-mockups", "2026-10-10T12:12:00Z"),
      event("GATE_REJECTED", "domain-design", "2026-10-10T12:20:00Z"),
    ];
    const result = pendingGates(stages, events);
    expect(result.gates.map((gate) => gate.stage)).toEqual(["refined-mockups", "domain-design"]);
    expect(result.gates[0]?.since).toBe("2026-10-10T12:12:00Z");
    expect(result.gates[1]?.state).toBe("revising");
  });
});

describe("renderMarkdown", () => {
  it("escapes raw HTML before adding tags", () => {
    const html = renderMarkdown("<script>alert(1)</script>\n\n# Title");
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
    expect(html).toContain("<h1>Title</h1>");
  });
});

function event(name: string, stage: string, timestamp: string): TimelineEvent {
  return {
    id: `${name}:${stage}`,
    timestamp,
    event: name,
    title: name,
    summary: name,
    stage,
    phase: null,
    fields: {},
    source: "shard.md",
    importance: "milestone",
  };
}
