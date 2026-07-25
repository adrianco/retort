#!/usr/bin/env node
/**
 * stdio entry point.
 *
 * The CSVs are parsed before the transport connects so the first tool call is
 * already fast. Anything written to stdout would corrupt the JSON-RPC stream,
 * so progress goes to stderr.
 */

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { getGraph } from './graph/graph.js';
import { createServer, SERVER_NAME, SERVER_VERSION } from './server.js';

async function main(): Promise<void> {
  const graph = getGraph();
  process.stderr.write(
    `${SERVER_NAME} ${SERVER_VERSION}: ${graph.info.mergedMatches} matches, ` +
      `${graph.info.players} players, ${graph.info.teams} teams loaded in ${graph.info.loadMillis} ms\n`,
  );

  const server = createServer(graph);
  await server.connect(new StdioServerTransport());
}

main().catch((error: unknown) => {
  process.stderr.write(`Fatal: ${error instanceof Error ? error.stack : String(error)}\n`);
  process.exit(1);
});
