/**
 * MCP server wiring.
 *
 * Adapts the transport-agnostic tool catalogue to the MCP SDK. Two details
 * matter for a client:
 *
 *  - Errors from a handler (an unknown team, an unparseable date) are returned
 *    as `isError` tool results rather than thrown, so the model sees the
 *    message -- which usually names the valid alternatives -- and can retry.
 *  - Each result carries both a text block and `structuredContent`, so a model
 *    can read the prose while a program reads the numbers.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { SoccerGraph } from './graph/graph.js';
import { TOOLS } from './tools/index.js';

export const SERVER_NAME = 'brazilian-soccer';
export const SERVER_VERSION = '1.0.0';

export function createServer(graph: SoccerGraph): McpServer {
  const server = new McpServer(
    { name: SERVER_NAME, version: SERVER_VERSION },
    {
      instructions:
        'Knowledge graph over Brazilian soccer: ~16.8k de-duplicated matches from the Brasileirão ' +
        '(Série A 2003-2023, Série B and C 2014-2023), the Copa do Brasil (2012-2023) and the Copa ' +
        'Libertadores (2013-2022), plus an 18k-row FIFA player database. Coverage differs per ' +
        'competition, so call `dataset_info` before assuming a season or club is present. ' +
        'Team names can be given in any spelling found in the sources ("Sao Paulo", "São Paulo-SP"); ' +
        'when a name is ambiguous the error message lists the candidates.',
    },
  );

  for (const tool of TOOLS) {
    server.registerTool(
      tool.name,
      {
        title: tool.title,
        description: tool.description,
        inputSchema: tool.schema.shape,
        annotations: { readOnlyHint: true, openWorldHint: false },
      },
      // The SDK has already validated `args` against `tool.schema`.
      (args: unknown) => {
        try {
          const result = tool.handler(graph, args as never);
          return {
            content: [{ type: 'text' as const, text: result.text }],
            structuredContent: result.data,
          };
        } catch (error) {
          return {
            content: [{ type: 'text' as const, text: describeError(error) }],
            isError: true,
          };
        }
      },
    );
  }

  return server;
}

function describeError(error: unknown): string {
  return error instanceof Error ? error.message : `Unexpected error: ${String(error)}`;
}
