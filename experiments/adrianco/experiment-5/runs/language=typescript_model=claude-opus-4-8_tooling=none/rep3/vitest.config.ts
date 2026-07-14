import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    globals: false,
    // Loading & parsing the CSV corpus once can take a moment on cold start.
    testTimeout: 30_000,
    hookTimeout: 30_000,
  },
});
