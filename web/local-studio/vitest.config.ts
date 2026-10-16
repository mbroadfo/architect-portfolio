import { mergeConfig } from "vite";
import { defineConfig } from "vitest/config";
import viteConfig from "./vite.config.ts";

// scripts/verify.py sets VERIFY_JUNIT to have Vitest also write a JUnit report.
const junit = process.env.VERIFY_JUNIT;

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      include: ["src/**/*.test.{ts,tsx}"],
      css: false,
      ...(junit ? { reporters: ["default", "junit"], outputFile: { junit } } : {}),
      coverage: {
        provider: "v8",
        include: ["src/**/*.{ts,tsx}"],
        exclude: ["src/**/*.test.{ts,tsx}", "src/main.tsx", "src/vite-env.d.ts", "src/test-*.ts"],
        reporter: ["text", "json-summary"],
        // The 80% line-coverage floor. Never lowered to make a step pass.
        thresholds: { lines: 80 },
      },
    },
  }),
);
