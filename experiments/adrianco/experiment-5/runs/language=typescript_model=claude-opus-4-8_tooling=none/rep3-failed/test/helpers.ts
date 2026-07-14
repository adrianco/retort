/**
 * ============================================================================
 * Context Block
 * ----------------------------------------------------------------------------
 * File:    test/helpers.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: Shared test fixture — loads the real datasets once and exposes the
 *          singleton `SoccerDatabase` to every BDD spec, so the Given step
 *          ("Given the match data is loaded") is fast and consistent.
 * ============================================================================
 */

import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadDatabase } from '../src/loadDatabase.js';
import type { SoccerDatabase } from '../src/database.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(HERE, '..', 'data');

let db: SoccerDatabase | null = null;

/** Given: the full match + player data is loaded into the knowledge graph. */
export function givenLoadedDatabase(): SoccerDatabase {
  if (!db) db = loadDatabase(DATA_DIR);
  return db;
}
