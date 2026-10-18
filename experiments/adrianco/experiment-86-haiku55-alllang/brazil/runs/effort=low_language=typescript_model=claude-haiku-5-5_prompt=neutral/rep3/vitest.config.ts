/*
 * Context: Vitest configuration for the Brazilian Soccer MCP test suite.
 * Tests live in tests/ and exercise the compiled-from-source modules directly.
 */
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    testTimeout: 30_000,
  },
});
