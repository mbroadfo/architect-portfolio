import { escapeHtml } from "./text.ts";

/** Render a small, safe subset of Markdown to HTML. Input is escaped first. */
export function renderMarkdown(source: string): string {
  const escaped = escapeHtml(source.replace(/\r\n/g, "\n"));
  const lines = escaped.split("\n");
  const html: string[] = [];
  let index = 0;

  const inline = (value: string): string =>
    value
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[\s(])_([^_]+)_/g, "$1<em>$2</em>");

  while (index < lines.length) {
    const line = lines[index] ?? "";

    if (line.startsWith("```")) {
      const body: string[] = [];
      index += 1;
      while (index < lines.length && !(lines[index] ?? "").startsWith("```")) {
        body.push(lines[index] ?? "");
        index += 1;
      }
      if (index < lines.length) index += 1;
      html.push(`<pre><code>${body.join("\n")}</code></pre>`);
      continue;
    }

    if (/^\s*\|.+\|\s*$/.test(line) && /^\s*\|?\s*:?-{3,}/.test(lines[index + 1] ?? "")) {
      const header = splitRow(line).map((cell) => `<th>${inline(cell)}</th>`).join("");
      index += 2;
      const rows: string[] = [];
      while (index < lines.length && /^\s*\|.+\|\s*$/.test(lines[index] ?? "")) {
        const cells = splitRow(lines[index] ?? "")
          .map((cell) => `<td>${inline(cell)}</td>`)
          .join("");
        rows.push(`<tr>${cells}</tr>`);
        index += 1;
      }
      html.push(`<table><thead><tr>${header}</tr></thead><tbody>${rows.join("")}</tbody></table>`);
      continue;
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(line);
    if (heading) {
      const level = heading[1]?.length ?? 1;
      html.push(`<h${level}>${inline(heading[2] ?? "")}</h${level}>`);
      index += 1;
      continue;
    }

    if (/^---+$/.test(line.trim()) || /^\*\*\*+$/.test(line.trim())) {
      html.push("<hr />");
      index += 1;
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index] ?? "")) {
        items.push(`<li>${inline((lines[index] ?? "").replace(/^\s*[-*]\s+/, ""))}</li>`);
        index += 1;
      }
      html.push(`<ul>${items.join("")}</ul>`);
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index] ?? "")) {
        items.push(`<li>${inline((lines[index] ?? "").replace(/^\s*\d+\.\s+/, ""))}</li>`);
        index += 1;
      }
      html.push(`<ol>${items.join("")}</ol>`);
      continue;
    }

    if (line.trim() === "") {
      index += 1;
      continue;
    }

    const paragraph: string[] = [line];
    index += 1;
    while (
      index < lines.length &&
      (lines[index] ?? "").trim() !== "" &&
      !/^(#{1,4}\s|```|\s*\||\s*[-*]\s+|\s*\d+\.\s+)/.test(lines[index] ?? "")
    ) {
      paragraph.push(lines[index] ?? "");
      index += 1;
    }
    html.push(`<p>${inline(paragraph.join(" "))}</p>`);
  }

  return html.join("\n");
}

function splitRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

export function firstHeading(markdown: string): string | null {
  for (const line of markdown.split(/\r?\n/)) {
    const match = /^#{1,4}\s+(.+)$/.exec(line.trim());
    if (match?.[1]) return match[1].trim();
  }
  return null;
}
