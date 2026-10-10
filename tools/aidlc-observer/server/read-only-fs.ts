import { existsSync, readFileSync, readdirSync, realpathSync, statSync } from "node:fs";

/**
 * Filesystem access for the observed project.
 * This module only reads. The observer never creates, edits, or deletes
 * anything in the workspace it is watching.
 */

const MAX_TEXT_BYTES = 4_000_000;

export function isNotFound(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error &&
    (error as { code?: string }).code === "ENOENT";
}

export function readText(file: string): string | null {
  const buffer = readBytes(file);
  if (!buffer) return null;
  if (buffer.byteLength > MAX_TEXT_BYTES) return buffer.subarray(0, MAX_TEXT_BYTES).toString("utf8");
  return buffer.toString("utf8");
}

export function readBytes(file: string): Buffer | null {
  try {
    return readFileSync(file);
  } catch (error) {
    if (isNotFound(error)) return null;
    throw error;
  }
}

export function textWasTruncated(file: string): boolean {
  try {
    return statSync(file).size > MAX_TEXT_BYTES;
  } catch {
    return false;
  }
}

export function listDir(dir: string): { name: string; isDirectory: boolean }[] | null {
  try {
    return readdirSync(dir, { withFileTypes: true })
      .filter((entry) => !entry.isSymbolicLink())
      .map((entry) => ({
        name: entry.name,
        isDirectory: entry.isDirectory(),
      }));
  } catch (error) {
    if (isNotFound(error)) return null;
    throw error;
  }
}

export function pathExists(file: string): boolean {
  return existsSync(file);
}

export function isDirectory(file: string): boolean {
  try {
    return statSync(file).isDirectory();
  } catch {
    return false;
  }
}

export function realPath(file: string): string | null {
  try {
    return realpathSync(file);
  } catch {
    return null;
  }
}
