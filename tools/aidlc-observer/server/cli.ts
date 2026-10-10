import { spawn } from "node:child_process";

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

const UNSAFE_PATH = /[\0\r\n&|<>^$`;]/;

export function commandArgs(name: CliName, workspace: string): string[] {
  const base = READONLY_COMMANDS[name];
  if (!base) throw new Error(`Refusing to run AI-DLC command "${String(name)}".`);
  return [...base, "--project-dir", workspace];
}

export function isSafeWorkspaceArg(workspace: string): boolean {
  return workspace.length > 0 && workspace.length < 500 && !UNSAFE_PATH.test(workspace);
}

export function runAidlc(name: CliName, workspace: string, timeoutMs = 8000): Promise<CliOutput> {
  if (!isSafeWorkspaceArg(workspace)) {
    return Promise.resolve({
      ok: false,
      code: null,
      stdout: "",
      stderr: "Skipped the AI-DLC command because the workspace path contains shell metacharacters.",
    });
  }

  const args = commandArgs(name, workspace);
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value: CliOutput): void => {
      if (settled) return;
      settled = true;
      resolve(value);
    };

    let child: ReturnType<typeof spawn>;
    try {
      child = spawn("aidlc", args, {
        cwd: workspace,
        windowsHide: true,
        shell: process.platform === "win32",
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
        spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true, stdio: "ignore" });
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
