import { spawn } from "node:child_process";
import path from "node:path";
import { isDirectory, pathExists, readText } from "./read-only-fs.ts";

/**
 * Read-only AI-DLC commands. Anything outside this map is refused.
 * `compile`, workflow routing, and audit writes are not represented here.
 */
export const READONLY_COMMANDS = {
  "intent-list": ["engine", "intent", "list", "--json", "--all"],
  "space-list": ["engine", "space", "list", "--json"],
  "runtime-summary": ["engine", "runtime", "summary", "--json"],
} as const;

export type CliName = keyof typeof READONLY_COMMANDS;

export interface CliOutput {
  ok: boolean;
  code: number | null;
  stdout: string;
  stderr: string;
}

export interface LaunchPlan {
  command: string;
  args: string[];
  shell: false;
}

export interface LaunchLookup {
  platform: NodeJS.Platform;
  pathEnv: string;
  cliBin: string;
  systemRoot: string;
}

const UNSAFE_PATH = /[\0\r\n&|<>^$`;]/;
const POWERSHELL_FORWARD = /^powershell(?:\.exe)?\s+-NoProfile\s+-NonInteractive\s+-ExecutionPolicy\s+Bypass\s+-File\s+"([^"\r\n]+\.ps1)"\s+%\*\s*$/i;

export function commandArgs(name: CliName, workspace: string): string[] {
  const base = READONLY_COMMANDS[name];
  if (!base) throw new Error(`Refusing to run AI-DLC command "${String(name)}".`);
  return [...base, "--project-dir", workspace];
}

export function isSafeWorkspaceArg(workspace: string): boolean {
  return workspace.length > 0 && workspace.length < 500 && !UNSAFE_PATH.test(workspace);
}

export function currentLookup(): LaunchLookup {
  return {
    platform: process.platform,
    pathEnv: process.env.PATH ?? process.env.Path ?? "",
    cliBin: process.env.AIDLC_OBSERVER_CLI_BIN?.trim() ?? "",
    systemRoot: process.env.SystemRoot ?? process.env.windir ?? "",
  };
}

/**
 * Resolve aidlc to an executable and an argument vector.
 * The workspace path is one argument. Nothing is joined into a shell command.
 */
export function planAidlcLaunch(name: CliName, workspace: string, lookup: LaunchLookup = currentLookup()): LaunchPlan | { error: string } {
  const args = commandArgs(name, workspace);
  if (!isSafeWorkspaceArg(workspace)) {
    return { error: "Skipped the AI-DLC command because the workspace path contains shell metacharacters." };
  }

  const resolved = lookup.cliBin
    ? resolveExplicit(lookup.cliBin)
    : resolveOnPath(lookup);
  if ("error" in resolved) return resolved;
  if (resolved.kind === "exe") {
    return { command: resolved.file, args, shell: false };
  }
  const powershell = powershellExe(lookup);
  if ("error" in powershell) return powershell;
  return {
    command: powershell.file,
    args: ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", resolved.file, ...args],
    shell: false,
  };
}

export function runAidlc(name: CliName, workspace: string, timeoutMs = 8000): Promise<CliOutput> {
  const plan = planAidlcLaunch(name, workspace);
  if ("error" in plan) {
    return Promise.resolve({ ok: false, code: null, stdout: "", stderr: plan.error });
  }

  return new Promise((resolve) => {
    let settled = false;
    const finish = (value: CliOutput): void => {
      if (settled) return;
      settled = true;
      resolve(value);
    };

    let child: ReturnType<typeof spawn>;
    try {
      child = spawn(plan.command, plan.args, {
        cwd: workspace,
        windowsHide: true,
        shell: false,
        stdio: ["ignore", "pipe", "pipe"],
      });
    } catch (error) {
      finish({
        ok: false,
        code: null,
        stdout: "",
        stderr: error instanceof Error ? error.message : String(error),
      });
      return;
    }

    const stdout: Buffer[] = [];
    const stderr: Buffer[] = [];
    let overflow = false;
    const take = (target: Buffer[], chunk: Buffer): void => {
      target.push(chunk);
      const size = target.reduce((sum, part) => sum + part.length, 0);
      if (size > 1_000_000) overflow = true;
    };
    child.stdout?.on("data", (chunk: Buffer) => take(stdout, chunk));
    child.stderr?.on("data", (chunk: Buffer) => take(stderr, chunk));
    child.on("error", (error) => {
      finish({ ok: false, code: null, stdout: "", stderr: error.message });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      const out = Buffer.concat(stdout).toString("utf8");
      const err = Buffer.concat(stderr).toString("utf8");
      if (overflow) {
        finish({ ok: false, code, stdout: "", stderr: "AI-DLC command output was larger than 1 MB and was discarded." });
        return;
      }
      finish({ ok: code === 0, code, stdout: out, stderr: err.trim() });
    });

    const timer = setTimeout(() => {
      if (process.platform === "win32" && child.pid) {
        spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true, shell: false, stdio: "ignore" });
      } else {
        child.kill();
      }
      finish({
        ok: false,
        code: null,
        stdout: "",
        stderr: `AI-DLC command timed out after ${timeoutMs} ms.`,
      });
    }, timeoutMs);
  });
}

export function parseJson(stdout: string): unknown {
  const trimmed = stdout.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(trimmed.slice(start, end + 1)) as unknown;
      } catch {
        return null;
      }
    }
    return null;
  }
}

type Resolved = { kind: "exe" | "script"; file: string } | { error: string };

function resolveExplicit(file: string): Resolved {
  if (!pathExists(file) || isDirectory(file)) {
    return { error: `AIDLC_OBSERVER_CLI_BIN does not point at a file: ${file}` };
  }
  return resolveLauncher(file);
}

function resolveOnPath(lookup: LaunchLookup): Resolved {
  const names = lookup.platform === "win32"
    ? ["aidlc.exe", "aidlc.ps1", "aidlc.cmd"]
    : ["aidlc"];
  for (const dir of lookup.pathEnv.split(path.delimiter)) {
    const trimmed = dir.trim().replace(/^"|"$/g, "");
    if (!trimmed) continue;
    for (const name of names) {
      const candidate = path.join(trimmed, name);
      if (!pathExists(candidate) || isDirectory(candidate)) continue;
      return resolveLauncher(candidate);
    }
  }
  return { error: "The aidlc command was not found on PATH. Record files are still read." };
}

function resolveLauncher(file: string): Resolved {
  const extension = path.extname(file).toLowerCase();
  if (extension === ".exe" || extension === "") return { kind: "exe", file };
  if (extension === ".ps1") return { kind: "script", file };
  if (extension === ".cmd" || extension === ".bat") {
    const script = scriptFromCmd(file);
    if (!script) {
      return { error: "Refusing to run aidlc through cmd.exe. Set AIDLC_OBSERVER_CLI_BIN to aidlc.exe." };
    }
    const executable = exeBesideShim(script);
    if (executable) return { kind: "exe", file: executable };
    return { kind: "script", file: script };
  }
  return { error: `Refusing to launch ${path.basename(file)} because it is not aidlc.exe or a PowerShell script.` };
}

function scriptFromCmd(file: string): string | null {
  const text = readText(file);
  if (text === null) return null;
  let script: string | null = null;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    if (/^@?echo\s+off$/i.test(line)) continue;
    if (/^rem\b/i.test(line)) continue;
    if (/^exit\s+\/b\s+%errorlevel%$/i.test(line)) continue;
    const match = POWERSHELL_FORWARD.exec(line);
    if (!match || script) return null;
    script = match[1] ?? null;
  }
  if (!script || !path.isAbsolute(script) || !script.toLowerCase().endsWith(".ps1")) return null;
  if (!pathExists(script) || isDirectory(script)) return null;
  return script;
}

function exeBesideShim(script: string): string | null {
  const pointer = path.join(path.dirname(script), "active-executable");
  const text = readText(pointer);
  if (text === null) return null;
  const target = text.trim();
  if (!target || /[\0\r\n]/.test(target)) return null;
  if (!path.isAbsolute(target) || path.basename(target).toLowerCase() !== "aidlc.exe") return null;
  if (!pathExists(target) || isDirectory(target)) return null;
  return target;
}

function powershellExe(lookup: LaunchLookup): { file: string } | { error: string } {
  if (!lookup.systemRoot) return { error: "PowerShell could not be located. Set AIDLC_OBSERVER_CLI_BIN to aidlc.exe." };
  const file = path.join(lookup.systemRoot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
  if (!pathExists(file)) return { error: "PowerShell could not be located. Set AIDLC_OBSERVER_CLI_BIN to aidlc.exe." };
  return { file };
}
