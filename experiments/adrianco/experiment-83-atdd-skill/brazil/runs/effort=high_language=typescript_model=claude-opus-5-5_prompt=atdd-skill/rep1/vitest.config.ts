import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/**/*.spec.ts', 'tests/**/*.test.ts'],
    testTimeout: 30_000,
    hookTimeout: 60_000,
  },
});
