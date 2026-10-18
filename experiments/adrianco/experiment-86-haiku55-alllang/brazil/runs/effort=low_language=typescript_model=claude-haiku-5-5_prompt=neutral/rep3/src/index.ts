#!/usr/bin/env node
/*
 * Context: Entry point. Starts the MCP server over stdio so it can be attached to an LLM
 * client (e.g. Claude Desktop or Claude Code `claude mcp add`). Logs go to stderr only,
 * because stdout carries the JSON-RPC stream.
 * Related: server.ts.
 */
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createServer } from './server.js';
import { loadDataset } from './dataset.js';

async function main(): Promise<void> {
  const server = createServer();
  await server.connect(new StdioServerTransport());
  // Warm the cache in the background so the first query is fast.
  loadDataset().then(
    (ds) => console.error(`brazilian-soccer-mcp: loaded ${ds.matches.length} matches, ${ds.players.length} players`),
    (err) => console.error('brazilian-soccer-mcp: failed to load datasets:', err),
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
