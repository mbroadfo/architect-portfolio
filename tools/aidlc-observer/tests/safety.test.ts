import { mkdtempSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";
import { READONLY_COMMANDS, commandArgs, planAidlcLaunch, type CliName, type LaunchLookup } from "../server/cli.ts";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const forbidden = [
  "writeFileSync",
  "appendFileSync",
  "createWriteStream",
  "rmSync",
  "unlinkSync",
  "mkdirSync",
  "renameSync",
  "copyFileSync",
  "truncateSync",
];

describe("read-only boundary", () => {
  it("limits AI-DLC commands to the read-only allowlist", () => {
    expect(Object.keys(READONLY_COMMANDS).sort()).toEqual([
      "intent-list",
      "runtime-summary",
      "space-list",
    ]);
    for (const name of Object.keys(READONLY_COMMANDS) as CliName[]) {
      const joined = commandArgs(name, "C:\\safe\\project").join(" ");
      expect(joined.startsWith("engine ")).toBe(true);
      expect(joined).toContain("--json");
      expect(joined).toContain("--project-dir");
      expect(joined).not.toMatch(/\b(compile|next|report|park|approve|fragment-fork|fragment-merge)\b/);
    }
    expect(() => commandArgs("compile" as CliName, "C:\\safe\\project")).toThrow(/Refusing/);
  });

  it("spawns aidlc.exe with an argument vector and never a shell", () => {
    const source = readFileSync(path.join(root, "server", "cli.ts"), "utf8");
    const shells = source.match(/shell:\s*[A-Za-z]+/g) ?? [];
    expect(shells.length).toBeGreaterThan(0);
    expect(shells.every((item) => item === "shell: false")).toBe(true);
    expect(source).not.toContain("spawn(\"cmd.exe\"");
    expect(source).not.toContain("spawn('cmd.exe'");

    const dir = mkdtempSync(path.join(tmpdir(), "aidlc-observer-launch-"));
    temps.push(dir);
    const shim = path.join(dir, "aidlc-shim.ps1");
    const executable = path.join(dir, "versions", "aidlc.exe");
    const command = path.join(dir, "bin", "aidlc.cmd");
    touch(shim);
    touch(executable);
    touch(command);
    touch(path.join(dir, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"));
    writeFileSync(path.join(dir, "active-executable"), `${executable}\n`);
    writeFileSync(command, [
      "@echo off",
      `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "${shim}" %*`,
      "exit /b %ERRORLEVEL%",
      "",
    ].join("\r\n"));

    const workspace = "C:\\safe\\my project";
    const plan = planAidlcLaunch("intent-list", workspace, lookup(dir));
    expect("error" in plan).toBe(false);
    if ("error" in plan) return;
    expect(plan.shell).toBe(false);
    expect(plan.command).toBe(executable);
    expect(plan.args.at(-1)).toBe(workspace);
    expect(plan.args.includes("--project-dir")).toBe(true);
    expect(plan.args.some((arg) => arg.includes("--project-dir "))).toBe(false);
    expect(plan.command.toLowerCase().endsWith("cmd.exe")).toBe(false);

    writeFileSync(path.join(dir, "active-executable"), "not-an-exe\n");
    const fallback = planAidlcLaunch("space-list", workspace, lookup(dir));
    expect("error" in fallback).toBe(false);
    if ("error" in fallback) return;
    expect(fallback.command.endsWith("powershell.exe")).toBe(true);
    expect(fallback.args).toContain("-File");
    expect(fallback.args).toContain(shim);
    expect(fallback.args.at(-1)).toBe(workspace);
    expect(fallback.shell).toBe(false);

    writeFileSync(command, `@echo off\r\npowershell.exe -File "${shim}" %* & calc.exe\r\n`);
    const refused = planAidlcLaunch("runtime-summary", workspace, lookup(dir));
    expect(refused).toMatchObject({ error: expect.stringMatching(/cmd\.exe/) });

    const direct = planAidlcLaunch("intent-list", workspace, lookup(dir, executable));
    expect(direct).toMatchObject({ command: executable, shell: false });

    const unsafe = planAidlcLaunch("intent-list", "C:\\safe&bad", lookup(dir, executable));
    expect(unsafe).toMatchObject({ error: expect.stringMatching(/metacharacters/) });
  });

  it("does not call filesystem write APIs from the observer server", () => {
    const files = walk(path.join(root, "server")).concat(walk(path.join(root, "shared")));
    expect(files.length).toBeGreaterThan(0);
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      for (const name of forbidden) {
        expect(source, `${path.relative(root, file)} contains ${name}`).not.toContain(name);
      }
    }
  });
});

const temps: string[] = [];

afterEach(() => {
  for (const dir of temps.splice(0)) rmSync(dir, { recursive: true, force: true });
});

function lookup(root: string, cliBin = ""): LaunchLookup {
  return {
    platform: "win32",
    pathEnv: path.join(root, "bin"),
    cliBin,
    systemRoot: root,
  };
}

function touch(file: string): void {
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, "");
}

function walk(dir: string): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) found.push(...walk(full));
    else if (entry.name.endsWith(".ts")) found.push(full);
  }
  return found;
}
