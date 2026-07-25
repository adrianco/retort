import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    // The full dataset (~24k matches, ~18k players) is parsed once per worker.
    // A single fork keeps that cost to one load for the whole suite.
    pool: 'forks',
    maxWorkers: 1,
    minWorkers: 1,
    isolate: false,
    testTimeout: 30_000,
    hookTimeout: 60_000,
  },
});
