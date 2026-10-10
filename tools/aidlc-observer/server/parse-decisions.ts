import type { DecisionRecord } from "../shared/types.ts";

export interface ParsedDecisions {
  decisions: DecisionRecord[];
  warnings: string[];
}

export function parseDecisionTables(markdown: string, source: string): ParsedDecisions {
  const decisions: DecisionRecord[] = [];
  const warnings: string[] = [];
  const lines = markdown.split(/\r?\n/);
  let heading = "";
  let index = 0;
  let tables = 0;

  while (index < lines.length) {
    const line = lines[index] ?? "";
    const headingMatch = /^#{1,4}\s+(.+)$/.exec(line.trim());
    if (headingMatch?.[1]) {
      heading = headingMatch[1].trim();
      index += 1;
      continue;
    }

    if (isTableRow(line) && isSeparator(lines[index + 1] ?? "")) {
      tables += 1;
      const header = splitRow(line).map((cell) => cell.toLowerCase());
      const decisionIndex = header.findIndex((cell) => cell === "decision" || cell.startsWith("decision"));
      if (decisionIndex < 0) {
        index += 1;
        continue;
      }
      const idIndex = header.findIndex((cell) => cell === "id" || cell === "#");
      const whenIndex = header.findIndex((cell) => /made|date|when/.test(cell));
      const sourceIndex = header.findIndex((cell) => cell === "source");
      const kind = /process/i.test(heading) ? "process" : "product";
      index += 2;
      while (index < lines.length && isTableRow(lines[index] ?? "")) {
        const cells = splitRow(lines[index] ?? "");
        const text = (cells[decisionIndex] ?? "").trim();
        if (text && !/^[-:\s]+$/.test(text)) {
          const id = idIndex >= 0 ? (cells[idIndex] ?? "").trim() : "";
          decisions.push({
            id: id || `${kind}-${decisions.length + 1}`,
            text,
            madeAt: whenIndex >= 0 ? (cells[whenIndex] ?? "").trim() || null : null,
            source: sourceIndex >= 0 ? (cells[sourceIndex] ?? "").trim() : heading,
            origin: source,
            kind,
          });
        }
        index += 1;
      }
      continue;
    }

    index += 1;
  }

  if (tables === 0) {
    warnings.push(`No decision table found in ${source}.`);
  }
  return { decisions, warnings };
}

function isTableRow(line: string): boolean {
  return /^\s*\|.+\|\s*$/.test(line);
}

function isSeparator(line: string): boolean {
  const stripped = line.replace(/[|\-:\s]/g, "");
  return /^\s*\|?\s*:?-{3,}/.test(line) && stripped.length === 0;
}

function splitRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}
