#!/usr/bin/env node
/**
 * Entry point: load the datasets, build the MCP server, and serve it over
 * stdio so an MCP-capable LLM client can call the query tools.
 *
 * The data directory defaults to ./data/kaggle relative to the current working
 * directory, and can be overridden with the SOCCER_DATA_DIR environment
 * variable.
 */
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { DataStore, defaultDataDir } from "./dataStore.js";
import { createServer } from "./server.js";

function resolveDataDir(): string {
  if (process.env.SOCCER_DATA_DIR) return process.env.SOCCER_DATA_DIR;
  // dist/index.js -> project root is two levels up.
  const here = dirname(fileURLToPath(import.meta.url));
  const projectRoot = join(here, "..");
  return defaultDataDir(projectRoot);
}

async function main(): Promise<void> {
  const store = new DataStore(resolveDataDir());
  store.load();
  // Diagnostics go to stderr so they don't corrupt the stdio JSON-RPC stream.
  console.error(
    `[brazilian-soccer-mcp] loaded ${store.matches.length} matches and ${store.players.length} players`,
  );

  const server = createServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[brazilian-soccer-mcp] server ready on stdio");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] fatal:", err);
  process.exit(1);
});
