/**
 * Brazilian Soccer MCP — Server adapter
 * -------------------------------------
 * Context: Thin Model Context Protocol adapter. It registers the tools declared
 * in `tools.ts`, answers `ListTools` with their schemas, and routes `CallTool`
 * requests through `callTool`, wrapping the resulting text in MCP content. All
 * domain logic lives in the store/tools layers; this file only translates
 * between the protocol and those pure functions, so the transport can be
 * swapped or tested independently.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import type { SoccerStore } from "./store.js";
import { TOOL_DEFS, callTool } from "./tools.js";

export function createServer(store: SoccerStore): Server {
  const server = new Server(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    { capabilities: { tools: {} } },
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: TOOL_DEFS.map((t) => ({
      name: t.name,
      description: t.description,
      inputSchema: t.inputSchema,
    })),
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
      const text = callTool(store, name, (args ?? {}) as Record<string, unknown>);
      return { content: [{ type: "text", text }] };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        isError: true,
        content: [{ type: "text", text: `Error: ${message}` }],
      };
    }
  });

  return server;
}
