#!/usr/bin/env node
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { loadSoccerData } from "./data-loader.js";
import { SoccerKnowledgeBase } from "./knowledge-base.js";
import { createSoccerMcpServer } from "./mcp-server.js";
import { SoccerService } from "./soccer-service.js";

export function buildService(dataDirectory?: string): SoccerService {
  const data = loadSoccerData(dataDirectory);
  return new SoccerService(new SoccerKnowledgeBase(data.matches, data.players));
}

async function main(): Promise<void> {
  const service = buildService();
  const server = createSoccerMcpServer(service);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`Brazilian Soccer MCP ready: ${service.graph.summary().matches} matches, ${service.graph.summary().players} players`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error: unknown) => {
    console.error("Brazilian Soccer MCP failed to start:", error);
    process.exitCode = 1;
  });
}
