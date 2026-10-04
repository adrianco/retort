/**
 * MCP server wiring: registers every tool from tools.ts on an McpServer.
 * Query errors (unknown team, bad season...) are returned as tool errors with
 * a helpful message rather than protocol failures.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { getDataset, type Dataset } from "./data.js";
import { QueryError, SoccerQueries } from "./query.js";
import { TOOLS } from "./tools.js";

export function createServer(dataset?: Dataset): { server: McpServer; queries: () => SoccerQueries } {
  const server = new McpServer({ name: "brazilian-soccer-mcp", version: "1.0.0" });
  let q: SoccerQueries | undefined;
  const queries = () => (q ??= new SoccerQueries(dataset ?? getDataset()));

  for (const tool of TOOLS) {
    server.registerTool(
      tool.name,
      { title: tool.title, description: tool.description, inputSchema: tool.inputSchema },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      async (args: any) => {
        try {
          return { content: [{ type: "text" as const, text: tool.handler(queries(), args ?? {}) }] };
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          return {
            isError: true,
            content: [{ type: "text" as const, text: err instanceof QueryError ? msg : `Error: ${msg}` }],
          };
        }
      },
    );
  }
  return { server, queries };
}
