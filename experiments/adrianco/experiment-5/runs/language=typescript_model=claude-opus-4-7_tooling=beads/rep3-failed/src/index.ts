#!/usr/bin/env node
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { getStore } from './data/loader.js';
import { buildServer } from './server.js';

function resolveDataDir(): string {
  if (process.env.SOCCER_DATA_DIR) {
    return path.resolve(process.env.SOCCER_DATA_DIR);
  }
  const cwdData = path.resolve(process.cwd(), 'data');
  if (fs.existsSync(path.join(cwdData, 'kaggle'))) return cwdData;
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.resolve(here, '..', 'data');
}

async function main() {
  const dataDir = resolveDataDir();
  process.stderr.write(`[brazilian-soccer-mcp] loading data from ${dataDir}\n`);
  const store = getStore(dataDir);
  process.stderr.write(
    `[brazilian-soccer-mcp] loaded ${store.matches.length} matches, ${store.players.length} players\n`,
  );

  const server = buildServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write('[brazilian-soccer-mcp] ready on stdio\n');
}

main().catch((err) => {
  process.stderr.write(`[brazilian-soccer-mcp] fatal: ${err?.stack || err}\n`);
  process.exit(1);
});
