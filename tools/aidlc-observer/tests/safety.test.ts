import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { READONLY_COMMANDS, commandArgs, type CliName } from "../server/cli.ts";

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

function walk(dir: string): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) found.push(...walk(full));
    else if (entry.name.endsWith(".ts")) found.push(full);
  }
  return found;
}
