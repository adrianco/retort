#!/usr/bin/env node
/**
 * index.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   Executable entry point for the Brazilian Soccer MCP server. Loads the full
 *   dataset, builds the MCP server (server.ts) and serves it over stdio — the
 *   standard transport for MCP clients such as Claude Desktop / Claude Code.
 *
 *   Logging goes to stderr only; stdout is reserved for the MCP JSON-RPC stream.
 * -----------------------------------------------------------------------------
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./server.js";
import { loadDataset } from "./data/loader.js";

async function main(): Promise<void> {
  const ds = loadDataset();
  console.error(
    `[brazilian-soccer-mcp] loaded ${ds.matches.length} matches and ${ds.players.length} players`,
  );
  const server = createServer(ds);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[brazilian-soccer-mcp] server ready on stdio");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] fatal:", err);
  process.exit(1);
});
