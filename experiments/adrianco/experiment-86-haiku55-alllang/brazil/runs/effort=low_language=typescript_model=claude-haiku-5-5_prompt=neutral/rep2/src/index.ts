#!/usr/bin/env node
/**
 * Context: stdio entry point. Set BRAZIL_SOCCER_DATA_DIR to override the
 * default data/kaggle directory. The dataset loads once at startup so every
 * tool call stays within the spec's latency targets.
 */
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { DEFAULT_DATA_DIR, getDataset } from './loader.js';
import { createServer } from './tools.js';

async function main(): Promise<void> {
  const dataDir = process.env.BRAZIL_SOCCER_DATA_DIR ?? DEFAULT_DATA_DIR;
  const dataset = getDataset(dataDir);
  const server = createServer(dataset);
  await server.connect(new StdioServerTransport());
  console.error(`brazilian-soccer MCP ready: ${dataset.matches.length} matches, ${dataset.players.length} players`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
