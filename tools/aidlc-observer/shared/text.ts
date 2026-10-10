export function titleCasePhase(value: string | null | undefined): string {
  if (!value) return "Unknown";
  const cleaned = value.replace(/phase/gi, " ").replace(/\s+/g, " ").trim();
  if (!cleaned) return "Unknown";
  return cleaned
    .split(/[\s/_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

export function humanizeSlug(slug: string): string {
  return slug
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function humanizeAgent(slug: string | null | undefined): string | null {
  if (!slug) return null;
  const trimmed = slug.trim();
  if (!trimmed || trimmed.toLowerCase() === "none") return null;
  if (trimmed.toLowerCase() === "orchestrator") return "Orchestrator";
  const words = trimmed
    .replace(/^aidlc-/, "")
    .replace(/-agent$/, "")
    .split("-")
    .filter(Boolean);
  if (words.length === 0) return trimmed;
  return words.map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

export function looksLikeSlug(value: string): boolean {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/i.test(value.trim());
}

export function truncate(value: string, max: number): string {
  const trimmed = value.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, Math.max(0, max - 1)).trimEnd()}…`;
}

export function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function basename(filePath: string): string {
  const normalized = filePath.replaceAll("\\", "/");
  const parts = normalized.split("/");
  return parts[parts.length - 1] || normalized;
}

export function toPosix(filePath: string): string {
  return filePath.replaceAll("\\", "/");
}

export function safeFileSlug(value: string): boolean {
  return /^[A-Za-z0-9._-]+$/.test(value);
}
