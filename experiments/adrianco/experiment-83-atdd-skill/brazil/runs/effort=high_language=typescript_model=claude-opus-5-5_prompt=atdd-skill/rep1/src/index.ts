#!/usr/bin/env node
/**
 * Entry point: loads the datasets and serves the MCP tools over stdio.
 *
 * Data directory: --data-dir <dir>, else $BRAZILIAN_SOCCER_DATA_DIR, else
 * the bundled data/kaggle directory.
 */
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { SoccerKnowledge } from './domain/knowledge.js';
import { createServer } from './server.js';

function dataDir(argv: string[]): string {
  const flag = argv.indexOf('--data-dir');
  if (flag !== -1 && argv[flag + 1]) return resolve(argv[flag + 1]);
  if (process.env.BRAZILIAN_SOCCER_DATA_DIR) return resolve(process.env.BRAZILIAN_SOCCER_DATA_DIR);
  return fileURLToPath(new URL('../../data/kaggle', import.meta.url));
}

const dir = dataDir(process.argv.slice(2));
const started = Date.now();
const knowledge = SoccerKnowledge.load(dir);
console.error(`brazilian-soccer: loaded data from ${dir} in ${Date.now() - started}ms`);

await createServer(knowledge).connect(new StdioServerTransport());
