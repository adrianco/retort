/**
 * ============================================================================
 * File: src/config.ts
 * Project: Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * Context:
 *   Resolves the location of the bundled Kaggle CSV directory. Defaults to
 *   <packageRoot>/data/kaggle so the server works regardless of the current
 *   working directory, and can be overridden with the SOCCER_DATA_DIR env var.
 * ============================================================================
 */

import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

/** Absolute path to the data/kaggle directory holding the CSV datasets. */
export function resolveDataDir(): string {
  if (process.env.SOCCER_DATA_DIR) {
    return resolve(process.env.SOCCER_DATA_DIR);
  }
  // This file lives at <root>/src (tsx) or <root>/dist (compiled).
  const here = dirname(fileURLToPath(import.meta.url));
  return join(here, "..", "data", "kaggle");
}
