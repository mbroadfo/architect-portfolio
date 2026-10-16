import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

// The Studio previews with the same renderer source Publish uses (BR4.1). React, Ajv and its
// formats are deduplicated so the renderer and the page share one copy.
const rendererSource = fileURLToPath(new URL("../slice-renderer/src", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@slice-renderer": rendererSource },
    dedupe: ["react", "react-dom", "ajv", "ajv-formats"],
  },
  server: {
    host: "localhost",
    port: 5173,
    strictPort: true,
  },
  build: { outDir: "dist", emptyOutDir: true },
});
