#!/usr/bin/env node
/**
 * ============================================================================
 * Context: Brazilian Soccer MCP Server — Entry Point
 * ----------------------------------------------------------------------------
 * Purpose : Boots the MCP server over a stdio transport so it can be launched
 *           by an MCP-capable client (Claude Desktop, etc.). Loads the dataset
 *           up front and reports load stats on stderr (stdout is reserved for
 *           the JSON-RPC protocol stream).
 * Usage   : `node dist/index.js`  (or `npm run dev` during development).
 * ============================================================================
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { loadDataset } from "./dataLoader.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const dataset = loadDataset();
  // Diagnostics on stderr only — stdout carries the MCP protocol.
  console.error(
    `[brazilian-soccer-mcp] loaded ${dataset.matches.length} matches, ` +
      `${dataset.players.length} players, ${dataset.competitions.length} competitions.`
  );

  const server = createServer(dataset);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[brazilian-soccer-mcp] ready on stdio.");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] fatal:", err);
  process.exit(1);
});
