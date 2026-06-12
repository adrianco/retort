#!/usr/bin/env node
/**
 * Entry point: load the bundled Kaggle datasets and serve the Brazilian Soccer
 * knowledge base over MCP via stdio, so any MCP-capable LLM client can connect.
 *
 * Data directory resolution order:
 *   1. $BRAZILIAN_SOCCER_DATA_DIR
 *   2. ./data/kaggle relative to the current working directory
 *   3. ../data/kaggle relative to this file (when run from dist/)
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { DataStore } from './data/store.js';
import { loadInto } from './data/loaders.js';
import { createSoccerServer } from './server.js';

function resolveDataDir(): string {
  const candidates = [
    process.env.BRAZILIAN_SOCCER_DATA_DIR,
    path.resolve(process.cwd(), 'data/kaggle'),
    path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../data/kaggle'),
    path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../data/kaggle'),
  ].filter(Boolean) as string[];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return candidates[candidates.length - 1];
}

async function main(): Promise<void> {
  const dataDir = resolveDataDir();
  const store = new DataStore();
  const report = loadInto(store, dataDir);
  // Diagnostics go to stderr so they never corrupt the stdio MCP channel.
  console.error(
    `[brazilian-soccer-mcp] loaded ${report.totalMatches} matches, ` +
      `${report.totalPlayers} players from ${dataDir}`,
  );

  const server = createSoccerServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('[brazilian-soccer-mcp] server ready on stdio');
}

main().catch((err) => {
  console.error('[brazilian-soccer-mcp] fatal:', err);
  process.exit(1);
});
