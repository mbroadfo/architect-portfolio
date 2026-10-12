// Renderer command-line interface: a C2 snapshot as JSON on stdin, a C11 RenderOutput as JSON
// on stdout. The API runs it as a subprocess (NFR Design Q1).
//
//   node dist/cli.cjs --mode public < snapshot.json > output.json
//   node dist/cli.cjs --mode preview --preview-slug <slug> < snapshot.json
//
// Exit codes: 0 rendered; 2 invalid input (RenderInputError); 1 any other failure.
import { render } from "./render";
import {
  RenderInputError,
  type AssetResolver,
  type PublicSiteSnapshot,
  type RenderOptions,
} from "./types";

/** C9 public addresses for images and downloads. */
export const publicResolver: AssetResolver = (ref) =>
  ref.kind === "image"
    ? `/media/${ref.assetRef}/${ref.variant}.${ref.format}`
    : `/files/${ref.assetRef}/${ref.downloadName}`;

export function parseArgs(argv: readonly string[]): Pick<RenderOptions, "mode" | "previewSlug"> {
  let mode: string | undefined;
  let previewSlug: string | undefined;
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--mode") mode = argv[++index];
    else if (arg === "--preview-slug") previewSlug = argv[++index];
    else throw new RenderInputError(`unknown argument '${String(arg)}'`);
  }
  if (mode !== "public" && mode !== "preview") {
    throw new RenderInputError("--mode must be 'public' or 'preview'");
  }
  return previewSlug === undefined ? { mode } : { mode, previewSlug };
}

export function run(argv: readonly string[], input: string): string {
  const options = parseArgs(argv);
  let snapshot: unknown;
  try {
    snapshot = JSON.parse(input);
  } catch {
    throw new RenderInputError("stdin is not valid JSON");
  }
  return JSON.stringify(
    render(snapshot as PublicSiteSnapshot, { ...options, resolveAsset: publicResolver }),
  );
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) chunks.push(chunk as Buffer);
  return Buffer.concat(chunks).toString("utf-8");
}

export async function main(): Promise<number> {
  try {
    process.stdout.write(run(process.argv.slice(2), await readStdin()));
    return 0;
  } catch (error) {
    const isInput = error instanceof RenderInputError;
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`${isInput ? "RenderInputError" : "RenderError"}: ${message}\n`);
    return isInput ? 2 : 1;
  }
}

if (process.env.VITEST === undefined) {
  void main().then((code) => {
    process.exitCode = code;
  });
}
