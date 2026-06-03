#!/usr/bin/env node
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { buildServer } from './server.js';

async function main(): Promise<void> {
  const server = await buildServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Log to stderr so stdout stays exclusively for MCP protocol messages.
  process.stderr.write('Brazilian Soccer MCP server ready (stdio).\n');
}

main().catch((err) => {
  process.stderr.write(`Fatal error: ${err instanceof Error ? err.stack ?? err.message : String(err)}\n`);
  process.exit(1);
});
