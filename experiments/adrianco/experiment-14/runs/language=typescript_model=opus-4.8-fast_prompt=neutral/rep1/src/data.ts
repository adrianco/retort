/**
 * Brazilian Soccer MCP — Store bootstrap
 * --------------------------------------
 * Context: Resolves the location of the bundled `data/kaggle` CSV directory and
 * builds a ready-to-query `SoccerStore`. Both the MCP entrypoint (`index.ts`)
 * and the test suite call `createStore()` so they share identical loading
 * behaviour. The data directory can be overridden via the `SOCCER_DATA_DIR`
 * environment variable; otherwise it is located relative to this file, which
 * works whether running from `src/` (tsx) or compiled `dist/`.
 */

import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadAll } from "./loader.js";
import { SoccerStore } from "./store.js";

/** Find the `data/kaggle` directory regardless of cwd or src/dist layout. */
export function resolveDataDir(): string {
  if (process.env.SOCCER_DATA_DIR) return resolve(process.env.SOCCER_DATA_DIR);
  const here = dirname(fileURLToPath(import.meta.url));
  const candidates = [
    join(here, "..", "data", "kaggle"), // dist/ or src/ -> repo root
    join(here, "..", "..", "data", "kaggle"),
    join(process.cwd(), "data", "kaggle"),
  ];
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  throw new Error(
    "Could not locate data/kaggle directory. Set SOCCER_DATA_DIR to its path.",
  );
}

/** Load all datasets and construct a queryable store. */
export function createStore(dataDir = resolveDataDir()): SoccerStore {
  const { matches, players } = loadAll(dataDir);
  return new SoccerStore(matches, players);
}
