#!/usr/bin/env node
/** Brazilian Soccer MCP server (stdio transport). */
import { realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { SoccerKB, UnknownEntityError } from './queries.js';
import { tools } from './tools.js';

export function createServer(kb: SoccerKB = new SoccerKB()): McpServer {
  const server = new McpServer({ name: 'brazilian-soccer', version: '1.0.0' });
  for (const tool of tools) {
    server.registerTool(tool.name, { description: tool.description, inputSchema: tool.schema }, async (args: unknown) => {
      try {
        return { content: [{ type: 'text' as const, text: tool.run(kb, args) }] };
      } catch (e) {
        if (!(e instanceof UnknownEntityError)) throw e;
        return { content: [{ type: 'text' as const, text: e.message }], isError: true };
      }
    });
  }
  return server;
}

const isMain = process.argv[1] !== undefined && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const server = createServer();
  await server.connect(new StdioServerTransport());
  console.error('Brazilian Soccer MCP server running on stdio');
}
