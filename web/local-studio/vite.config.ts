import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The local Studio page. `python -m portfolio_studio serve` serves the built dist/ from the
// same loopback origin as its API; the bundle goes under /ui/ so it never collides with the
// renderer's /assets/ (used by the preview pages) or /media/ (image derivatives).
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    assetsDir: "ui",
    // No inline data: URLs: the Studio's CSP allows only 'self'.
    assetsInlineLimit: 0,
  },
});
