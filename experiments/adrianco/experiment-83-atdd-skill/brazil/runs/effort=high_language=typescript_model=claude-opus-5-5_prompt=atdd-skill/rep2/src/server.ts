#!/usr/bin/env node
/**
 * Brazilian Soccer MCP server.
 *
 * Loads the Kaggle datasets from SOCCER_DATA_DIR (default: data/kaggle next
 * to this package) and serves questions about them over MCP on stdio.
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadDatasets } from './datasets.js';
import { SoccerKnowledge } from './knowledge.js';
import { registerTools } from './tools.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const defaultDataDir = path.resolve(here, '..', '..', 'data', 'kaggle');

export function createServer(dataDir: string): McpServer {
  const started = Date.now();
  const kb = new SoccerKnowledge(loadDatasets(dataDir));
  const overview = kb.overview();
  console.error(
    `brazilian-soccer-mcp: loaded ${overview.totals.matches} matches and ${overview.totals.players} players from ${dataDir} in ${Date.now() - started}ms`,
  );
  const server = new McpServer({ name: 'brazilian-soccer', version: '1.0.0' });
  registerTools(server, kb);
  return server;
}

async function main(): Promise<void> {
  const dataDir = process.env.SOCCER_DATA_DIR ?? defaultDataDir;
  await createServer(dataDir).connect(new StdioServerTransport());
}

main().catch((error) => {
  console.error('brazilian-soccer-mcp failed to start:', error);
  process.exit(1);
});
