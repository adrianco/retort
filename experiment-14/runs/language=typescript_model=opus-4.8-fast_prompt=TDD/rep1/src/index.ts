#!/usr/bin/env node
/**
 * Entry point for the Brazilian Soccer MCP server.
 *
 * Loads the bundled Kaggle datasets into an in-memory `SoccerDatabase` and
 * serves the query tools over the MCP stdio transport. The data directory can be
 * overridden with the `BRAZILIAN_SOCCER_DATA_DIR` environment variable;
 * otherwise it resolves to `data/kaggle` alongside the installed package.
 */

import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { loadAll } from "./loader.js";
import { SoccerDatabase } from "./database.js";
import { runStdio } from "./server.js";

function resolveDataDir(): string {
  const override = process.env.BRAZILIAN_SOCCER_DATA_DIR;
  if (override) return resolve(override);
  // dist/index.js -> project root -> data/kaggle
  const here = dirname(fileURLToPath(import.meta.url));
  return join(here, "..", "data", "kaggle");
}

async function main(): Promise<void> {
  const dataDir = resolveDataDir();
  const corpus = loadAll(dataDir);
  const db = new SoccerDatabase(corpus);
  // Log to stderr so stdout stays a clean MCP channel.
  console.error(
    `[brazilian-soccer-mcp] loaded ${db.matches.length} canonical matches ` +
      `and ${db.players.length} players from ${dataDir}`
  );
  await runStdio(db);
  console.error("[brazilian-soccer-mcp] server connected over stdio");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] fatal:", err);
  process.exit(1);
});
