#!/usr/bin/env node
/** Entry point: load the CSV data and serve the MCP tools over stdio. */
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadDataset } from './data.js';
import { SoccerDB } from './queries.js';
import { createServer } from './server.js';

async function main(): Promise<void> {
  const db = new SoccerDB(loadDataset());
  const server = createServer(db);
  await server.connect(new StdioServerTransport());
  // stdout is reserved for the protocol; log to stderr.
  console.error(`brazilian-soccer-mcp ready: ${db.matches.length} matches, ${db.players.length} players`);
}

main().catch((err) => {
  console.error('Failed to start brazilian-soccer-mcp:', err);
  process.exit(1);
});
