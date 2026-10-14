// Renderer CLI tests (Step 16): the subprocess boundary the API calls.
import { Readable } from "node:stream";
import { afterEach, describe, expect, it, vi } from "vitest";
import { main, parseArgs, publicResolver, run } from "./cli";
import { snapshot } from "./test-fixtures";
import { RenderInputError } from "./types";

const realStdin = Object.getOwnPropertyDescriptor(process, "stdin");

function useStdin(text: string): void {
  Object.defineProperty(process, "stdin", {
    value: Readable.from([Buffer.from(text)]),
    configurable: true,
  });
}

afterEach(() => {
  if (realStdin) Object.defineProperty(process, "stdin", realStdin);
  vi.restoreAllMocks();
});

describe("renderer CLI", () => {
  it("parses public and preview arguments", () => {
    expect(parseArgs(["--mode", "public"])).toEqual({ mode: "public" });
    expect(parseArgs(["--mode", "preview", "--preview-slug", "x"])).toEqual({
      mode: "preview",
      previewSlug: "x",
    });
    expect(() => parseArgs(["--mode", "draft"])).toThrow(RenderInputError);
    expect(() => parseArgs(["--verbose"])).toThrow(/unknown argument/);
  });

  it("renders a snapshot from JSON to RenderOutput JSON", () => {
    const output = JSON.parse(run(["--mode", "public"], JSON.stringify(snapshot())));
    expect(output.contractVersion).toBe("1.0");
    expect(output.pages[2].path).toBe("/work/placeholder-project");
  });

  it("refuses invalid JSON as an input error", () => {
    expect(() => run(["--mode", "public"], "{not json")).toThrow(RenderInputError);
  });

  it("resolves C9 public addresses", () => {
    expect(
      publicResolver({ kind: "image", assetRef: "ast_a", variant: "w960", format: "webp" }),
    ).toBe("/media/ast_a/w960.webp");
    expect(publicResolver({ kind: "download", assetRef: "ast_a", downloadName: "x.pdf" })).toBe(
      "/files/ast_a/x.pdf",
    );
  });

  it("main writes the output and exits 0, or 2 for invalid input", async () => {
    const stdout = vi.spyOn(process.stdout, "write").mockImplementation(() => true);
    const stderr = vi.spyOn(process.stderr, "write").mockImplementation(() => true);
    const argv = process.argv;
    process.argv = ["node", "cli", "--mode", "public"];
    try {
      useStdin(JSON.stringify(snapshot()));
      expect(await main()).toBe(0);
      expect(String(stdout.mock.calls[0]?.[0])).toContain('"contractVersion":"1.0"');
      useStdin("{}");
      expect(await main()).toBe(2);
      expect(String(stderr.mock.calls[0]?.[0])).toMatch(/^RenderInputError: invalid snapshot/);
    } finally {
      process.argv = argv;
    }
  });

  it("main exits 1 for an unexpected failure", async () => {
    const stderr = vi.spyOn(process.stderr, "write").mockImplementation(() => true);
    vi.spyOn(process.stdout, "write").mockImplementation(() => {
      throw new Error("pipe closed");
    });
    const argv = process.argv;
    process.argv = ["node", "cli", "--mode", "public"];
    try {
      useStdin(JSON.stringify(snapshot()));
      expect(await main()).toBe(1);
      expect(String(stderr.mock.calls[0]?.[0])).toBe("RenderError: pipe closed\n");
    } finally {
      process.argv = argv;
    }
  });
});
