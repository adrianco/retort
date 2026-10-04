#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { Dataset } from "./data.js";
import { SoccerService } from "./queries.js";
import { TOOLS, runTool } from "./tools.js";

export function createServer(svc = new SoccerService(Dataset.load())): McpServer {
  const server = new McpServer({ name: "brazilian-soccer", version: "1.0.0" });
  for (const [name, t] of Object.entries(TOOLS)) {
    server.registerTool(name, { description: t.description, inputSchema: t.shape }, async (args: unknown) => {
      try {
        return { content: [{ type: "text" as const, text: runTool(svc, name, args) }] };
      } catch (e) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    });
  }
  return server;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await createServer().connect(new StdioServerTransport());
}
