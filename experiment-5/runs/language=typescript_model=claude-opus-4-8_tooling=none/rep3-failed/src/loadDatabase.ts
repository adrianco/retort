/**
 * ============================================================================
 * Context Block
 * ----------------------------------------------------------------------------
 * File:    src/loadDatabase.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: Locate the `data/` directory and build a ready-to-query
 *          `SoccerDatabase`. Shared by the MCP server entrypoint and the test
 *          suite so both exercise the exact same loading path.
 * ============================================================================
 */

import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadAllData } from './dataLoader.js';
import { SoccerDatabase } from './database.js';

/** Find the `data` directory by walking up from a starting directory. */
export function resolveDataDir(startDir?: string): string {
  // Allow explicit override via env var for non-standard deployments.
  if (process.env.SOCCER_DATA_DIR && existsSync(process.env.SOCCER_DATA_DIR)) {
    return process.env.SOCCER_DATA_DIR;
  }
  const here = startDir ?? dirname(fileURLToPath(import.meta.url));
  let dir = here;
  for (let i = 0; i < 6; i++) {
    const candidate = join(dir, 'data');
    if (existsSync(join(candidate, 'kaggle'))) return candidate;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  // Fall back to a conventional location relative to CWD.
  return resolve(process.cwd(), 'data');
}

let cached: SoccerDatabase | null = null;

/** Build (and memoize) the database from the resolved data directory. */
export function loadDatabase(dataDir?: string): SoccerDatabase {
  if (cached && !dataDir) return cached;
  const dir = dataDir ?? resolveDataDir();
  const data = loadAllData(dir);
  const db = new SoccerDatabase(data);
  if (!dataDir) cached = db;
  return db;
}
