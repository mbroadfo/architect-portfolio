// Bundles the renderer CLI into one self-contained file, dist/cli.cjs, which the API runs
// as a subprocess (NFR Design Q1). CommonJS output keeps React's Node server build working.
import { build } from "esbuild";

await build({
  entryPoints: ["src/cli.ts"],
  bundle: true,
  platform: "node",
  format: "cjs",
  target: "node22",
  outfile: "dist/cli.cjs",
  // Set here, not only in tsconfig.json, so the bundle is the same wherever it is built.
  jsx: "automatic",
  define: { "process.env.NODE_ENV": '"production"' },
  legalComments: "none",
  logLevel: "info",
});
