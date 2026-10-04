import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['acceptance/specs/**/*.spec.ts', 'test/**/*.test.ts'],
    testTimeout: 30_000,
    hookTimeout: 60_000,
  },
});
