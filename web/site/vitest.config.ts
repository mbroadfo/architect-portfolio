import { defineConfig } from "vitest/config";

// scripts/verify.py sets VERIFY_JUNIT to have Vitest also write a JUnit report, which it
// reads to fail --strict runs on skipped tests (Codex review R2).
const junit = process.env.VERIFY_JUNIT;

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"],
    ...(junit ? { reporters: ["default", "junit"], outputFile: { junit } } : {}),
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      exclude: ["src/**/*.test.ts", "src/main.ts"],
      reporter: ["text", "json-summary"],
      // NFR13.4: the 80% line-coverage floor. Never lowered to make a step pass.
      thresholds: { lines: 80 },
    },
  },
});
