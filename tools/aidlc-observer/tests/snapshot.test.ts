import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import type { CliName, CliOutput } from "../server/cli.ts";
import { collectSnapshot } from "../server/snapshot.ts";

const fixtures = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "fixtures");

describe("collectSnapshot", () => {
  it("reads the sample workflow without writing", async () => {
    const workspace = path.join(fixtures, "sample");
    const before = fingerprint(workspace);
    const snapshot = await collectSnapshot(workspace, { runCli: null });
    expect(fingerprint(workspace)).toBe(before);

    const intent = snapshot.intent;
    expect(snapshot.ok).toBe(true);
    expect(snapshot.readOnly).toBe(true);
    expect(snapshot.space).toBe("default");
    expect(intent?.dirName).toBe("261010-sample-workflow");
    expect(intent?.currentStage).toBe("refined-mockups");
    expect(intent?.currentStageName).toBe("Refined Mockups");
    expect(intent?.phaseLabel).toBe("Inception");
    expect(intent?.approval).toMatchObject({
      code: "awaiting-approval",
      label: "Awaiting your approval",
      stage: "refined-mockups",
    });
    expect(intent?.pendingGates.map((gate) => gate.stage)).toEqual(["refined-mockups"]);
    expect(intent?.pendingGates[0]?.since).toBe("2026-10-10T12:12:00Z");
    expect(intent?.counts).toEqual({
      completed: 4,
      active: 1,
      pending: 2,
      skipped: 1,
      total: 8,
    });
    expect(intent?.decisions.find((decision) => decision.id === "D-01")?.text).toMatch(/three exhibits/);
    expect(intent?.decisions.find((decision) => decision.id === "P-01")?.kind).toBe("process");
    expect(intent?.artifacts.some((artifact) => artifact.path.endsWith("intent-statement.md"))).toBe(true);
    expect(intent?.artifacts.every((artifact) => !artifact.path.includes("/audit/"))).toBe(true);
    expect(intent?.runtime).toMatchObject({
      source: "runtime-graph",
      workflowId: "2026-10-10T12:00:00Z",
      stages: { approved: 1, pending: 1, failed: 0 },
    });

    const stamps = (intent?.timeline ?? []).map((event) => event.timestamp);
    const dated = stamps.filter((stamp): stamp is string => stamp !== null);
    expect(dated).toEqual([...dated].sort());
    expect(stamps.at(-1)).toBeNull();
    const timeline = intent?.timeline ?? [];
    const started = timeline.find((event) => event.event === "STAGE_STARTED" && event.stage === "refined-mockups");
    const human = timeline.find((event) => event.event === "HUMAN_TURN");
    if (!started || !human) throw new Error("timeline events were missing");
    expect(timeline.indexOf(human)).toBeLessThan(timeline.indexOf(started));
  });

  it("can switch to another workflow in the same space", async () => {
    const snapshot = await collectSnapshot(path.join(fixtures, "sample"), {
      runCli: null,
      intent: "261009-older-note",
    });
    expect(snapshot.intent?.dirName).toBe("261009-older-note");
    expect(snapshot.intent?.approval.code).toBe("completed");
    expect(snapshot.intent?.currentStage).toBe("state-init");
  });

  it("prefers the read-only runtime summary command when it succeeds", async () => {
    const snapshot = await collectSnapshot(path.join(fixtures, "sample"), {
      runCli: fakeCli,
    });
    expect(snapshot.intent?.runtime).toMatchObject({
      source: "aidlc-command",
      workflowId: "from-command",
      durationMinutes: 12,
    });
    expect(snapshot.commands.every((command) => command.ok)).toBe(true);
  });

  it("keeps the file view when AI-DLC commands fail", async () => {
    const snapshot = await collectSnapshot(path.join(fixtures, "sample"), {
      runCli: async () => ({ ok: false, code: 1, stdout: "", stderr: "aidlc is not on PATH" }),
    });
    expect(snapshot.intent?.currentStage).toBe("refined-mockups");
    expect(snapshot.intent?.runtime?.source).toBe("runtime-graph");
    expect(snapshot.warnings.some((warning) => warning.includes("AI-DLC commands were not available"))).toBe(true);
  });

  it("survives an empty workspace", async () => {
    const workspace = path.join(fixtures, "empty");
    const before = fingerprint(workspace);
    const snapshot = await collectSnapshot(workspace, { runCli: null });
    expect(fingerprint(workspace)).toBe(before);
    expect(snapshot.ok).toBe(true);
    expect(snapshot.intent).toBeNull();
    expect(snapshot.warnings.some((warning) => warning.includes("No aidlc directory"))).toBe(true);
  });

  it("survives a partial record", async () => {
    const workspace = path.join(fixtures, "partial");
    const before = fingerprint(workspace);
    const snapshot = await collectSnapshot(workspace, { runCli: null });
    expect(fingerprint(workspace)).toBe(before);
    expect(snapshot.intent?.currentStage).toBe("mystery-stage");
    expect(snapshot.intent?.approval).toMatchObject({
      code: "unknown",
      label: "Stage is named, but its marker is missing",
    });
    expect(snapshot.intent?.timeline).toEqual([]);
    expect(snapshot.warnings.some((warning) => /audit/i.test(warning))).toBe(true);
  });

  it("survives malformed records", async () => {
    const workspace = path.join(fixtures, "malformed");
    const before = fingerprint(workspace);
    const snapshot = await collectSnapshot(workspace, { runCli: null });
    expect(fingerprint(workspace)).toBe(before);
    expect(snapshot.ok).toBe(true);
    expect(snapshot.intent?.dirName).toBe("bad-record");
    expect(snapshot.warnings.length).toBeGreaterThan(0);
    expect(snapshot.intent?.timeline).toEqual([]);
  });
});

async function fakeCli(name: CliName): Promise<CliOutput> {
  if (name === "runtime-summary") {
    return {
      ok: true,
      code: 0,
      stdout: JSON.stringify({
        workflow_id: "from-command",
        scope: "classic",
        started_at: "2026-10-10T12:00:00Z",
        duration_minutes: 12,
        stages: { total: 2, approved: 1, failed: 0, pending: 1 },
        by_phase: {},
        sensors: { total: 1, passed: 1, failed: 0 },
      }),
      stderr: "",
    };
  }
  if (name === "space-list") {
    return {
      ok: true,
      code: 0,
      stdout: JSON.stringify({ active: "default", spaces: [{ name: "default", active: true }] }),
      stderr: "",
    };
  }
  return {
    ok: true,
    code: 0,
    stdout: JSON.stringify({
      active: "261010-sample-workflow",
      space: "default",
      intents: [{
        dirName: "261010-sample-workflow",
        slug: "sample-workflow",
        status: "in-flight",
        uuid: "abc",
        active: true,
      }],
    }),
    stderr: "",
  };
}

function fingerprint(dir: string): string {
  const hash = createHash("sha256");
  const visit = (current: string): void => {
    for (const name of readdirSync(current).sort()) {
      const full = path.join(current, name);
      const stat = statSync(full);
      hash.update(name);
      hash.update(stat.isDirectory() ? "d" : "f");
      if (stat.isDirectory()) visit(full);
      else hash.update(readFileSync(full));
    }
  };
  visit(dir);
  return hash.digest("hex");
}
