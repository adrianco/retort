#!/usr/bin/env node
/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/index.ts
 * Purpose: Executable entrypoint for the Brazilian Soccer MCP server.
 *
 * Loads the dataset, builds the wired server (see server.ts) and connects it
 * over stdio — the transport MCP clients (e.g. Claude Desktop) use to launch
 * and talk to a local server. Startup diagnostics go to stderr so they never
 * corrupt the stdio JSON-RPC stream on stdout.
 * ============================================================================
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./server.js";
import { loadDataset } from "./data/loader.js";

async function main(): Promise<void> {
  const ds = loadDataset();
  console.error(
    `[brazilian-soccer-mcp] loaded ${ds.matches.length} matches and ` +
      `${ds.players.length} players`
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
