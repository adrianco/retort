import { defineConfig } from "vitest/config";
export default defineConfig({ test: { include: ["acceptance/**/*.spec.ts"], testTimeout: 20000, hookTimeout: 60000 } });
