#!/usr/bin/env node
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadData } from './loader.js';
import { createServer } from './server.js';

async function main(): Promise<void> {
  const dataDir = process.env.BR_SOCCER_DATA_DIR ?? 'data/kaggle';
  process.stderr.write(`Loading data from ${dataDir}...\n`);
  const store = loadData({ dataDir });
  process.stderr.write(
    `Loaded ${store.matches.length} matches and ${store.players.length} players.\n`,
  );

  const server = createServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write('Brazilian Soccer MCP server ready on stdio.\n');
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err instanceof Error ? err.stack ?? err.message : String(err)}\n`);
  process.exit(1);
});
