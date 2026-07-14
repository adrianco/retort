#!/usr/bin/env node
/**
 * ============================================================================
 * Context Block
 * ----------------------------------------------------------------------------
 * File:    src/server.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: MCP server entrypoint / bootstrap. Loads the datasets into the
 *          in-memory `SoccerDatabase`, builds the tool-equipped server via
 *          `createServer`, and serves it over stdio (the standard MCP local
 *          transport). The tool definitions themselves live in
 *          `src/createServer.ts` so they can be unit/integration tested without
 *          touching stdio.
 *
 * Run:     `npm run build && node dist/server.js`  (or `npm run dev`).
 * ============================================================================
 */

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadDatabase } from './loadDatabase.js';
import { createServer } from './createServer.js';

async function main(): Promise<void> {
  const db = loadDatabase();
  const server = createServer(db);

  const transport = new StdioServerTransport();
  await server.connect(transport);

  // Log to stderr so we don't corrupt the stdio JSON-RPC stream on stdout.
  const s = db.summary();
  console.error(
    `[brazilian-soccer-mcp] ready: ${s.totalMatches} matches, ${s.totalPlayers} players loaded.`,
  );
}

main().catch((err) => {
  console.error('[brazilian-soccer-mcp] fatal error:', err);
  process.exit(1);
});
