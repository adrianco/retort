#!/usr/bin/env node
/**
 * Entry point: loads the CSV datasets and serves the MCP tools over stdio.
 *
 * Usage:
 *   node dist/index.js [path-to-data-dir]
 *
 * The data directory defaults to ./data/kaggle relative to the project root.
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadDataset } from "./loader.js";
import { createServer } from "./server.js";

function findDataDir(): string {
  const arg = process.argv[2];
  if (arg) return resolve(arg);
  const here = dirname(fileURLToPath(import.meta.url));
  const candidates = [
    join(here, "..", "data", "kaggle"),
    join(process.cwd(), "data", "kaggle"),
  ];
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  throw new Error(
    "Could not locate the data/kaggle directory; pass it as the first argument.",
  );
}

async function main() {
  const dataDir = findDataDir();
  const started = Date.now();
  const dataset = loadDataset(dataDir);
  // Log to stderr — stdout is reserved for the MCP protocol.
  console.error(
    `[brazilian-soccer-mcp] loaded ${dataset.matches.length} matches and ${dataset.players.length} players in ${Date.now() - started}ms`,
  );
  const server = createServer(dataset);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[brazilian-soccer-mcp] server running on stdio");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] fatal:", err);
  process.exit(1);
});
