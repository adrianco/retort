#!/usr/bin/env node
/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/index.ts
 * Purpose: Executable entrypoint for the Brazilian Soccer MCP server. Wires the
 *          server (from server.ts) to a stdio transport so it can be launched
 *          by any MCP client (Claude Desktop, etc.).
 * Inputs:  Optional env var BRAZILIAN_SOCCER_DATA_DIR to override the data dir.
 * Outputs: Speaks the MCP protocol over stdin/stdout.
 * Notes:   All logging goes to stderr to keep stdout clean for the protocol.
 * ============================================================================
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const dataDir = process.env.BRAZILIAN_SOCCER_DATA_DIR;
  const server = createServer(dataDir);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // eslint-disable-next-line no-console
  console.error("Brazilian Soccer MCP server running on stdio.");
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error("Fatal error starting MCP server:", err);
  process.exit(1);
});
