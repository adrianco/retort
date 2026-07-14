#!/usr/bin/env node
/**
 * ============================================================================
 * File: src/index.ts
 * Project: Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * Context:
 *   Entry point. Loads the Kaggle datasets into the knowledge graph, builds
 *   the MCP server (src/server.ts) and serves it over stdio so it can be
 *   connected to an LLM/MCP client. All diagnostics go to stderr to keep the
 *   stdout JSON-RPC channel clean.
 * ============================================================================
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { KnowledgeGraph } from "./knowledgeGraph.js";
import { createServer } from "./server.js";
import { resolveDataDir } from "./config.js";

async function main(): Promise<void> {
  const dataDir = resolveDataDir();
  console.error(`[brazilian-soccer-mcp] loading datasets from ${dataDir}`);
  const graph = KnowledgeGraph.fromDirectory(dataDir);
  console.error(
    `[brazilian-soccer-mcp] loaded ${graph.matches.length} matches, ${graph.players.length} players, ${graph.listTeams().length} teams`,
  );

  const server = createServer(graph);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[brazilian-soccer-mcp] server ready (stdio)");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] fatal:", err);
  process.exit(1);
});
