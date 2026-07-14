/**
 * MCP server wiring.
 *
 * `buildServer` constructs an `McpServer`, binds the query engine, and registers
 * every tool from the tool registry, translating each handler's formatted string
 * into MCP text content. `runStdio` connects the server over stdio for use as a
 * standard MCP server process. Keeping construction (`buildServer`) separate from
 * transport (`runStdio`) lets the server be exercised with an in-memory client
 * in tests.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import type { z } from "zod";
import { SoccerDatabase } from "./database.js";
import { createTools } from "./tools.js";

export const SERVER_INFO = {
  name: "brazilian-soccer-mcp",
  version: "1.0.0",
} as const;

/** Build an MCP server exposing the soccer tools backed by `db`. */
export function buildServer(db: SoccerDatabase): McpServer {
  const server = new McpServer(SERVER_INFO, {
    capabilities: { tools: {} },
    instructions:
      "Tools for querying Brazilian soccer data: matches, team records, " +
      "head-to-head comparisons, league standings, statistics and FIFA players.",
  });

  for (const tool of createTools(db)) {
    const shape = (tool.schema as z.ZodObject<z.ZodRawShape>).shape;
    server.registerTool(
      tool.name,
      { description: tool.description, inputSchema: shape },
      async (args: unknown) => {
        try {
          const text = tool.handler(args as never);
          return { content: [{ type: "text" as const, text }] };
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          return {
            content: [{ type: "text" as const, text: `Error: ${message}` }],
            isError: true,
          };
        }
      }
    );
  }

  return server;
}

/** Connect a server backed by `db` to the stdio transport. */
export async function runStdio(db: SoccerDatabase): Promise<void> {
  const server = buildServer(db);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
