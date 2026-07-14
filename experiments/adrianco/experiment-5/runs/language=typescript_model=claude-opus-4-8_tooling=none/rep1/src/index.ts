#!/usr/bin/env node
/**
 * Context
 * -------
 * Executable entry point for the Brazilian Soccer MCP server. Eagerly loads the
 * datasets (so the first client request is fast and load errors surface
 * immediately), then connects the server over the stdio transport used by MCP
 * clients such as Claude Desktop.
 *
 * Run directly with `node dist/index.js` (after `npm run build`) or via
 * `npm run dev` (tsx). All diagnostic logging goes to stderr to keep stdout
 * reserved for the MCP JSON-RPC protocol stream.
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { getDataStore } from "./dataStore.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const store = getDataStore();
  try {
    const counts = store.loadAll();
    console.error(
      `[brazilian-soccer-mcp] Loaded ${counts.matches} matches and ${counts.players} players from ${store.dataDir}`,
    );
  } catch (err) {
    console.error(`[brazilian-soccer-mcp] Failed to load datasets from ${store.dataDir}:`, err);
    process.exit(1);
  }

  const server = createServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[brazilian-soccer-mcp] Server connected over stdio. Ready for requests.");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] Fatal error:", err);
  process.exit(1);
});
