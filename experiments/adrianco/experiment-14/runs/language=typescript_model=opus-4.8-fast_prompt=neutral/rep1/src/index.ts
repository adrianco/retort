#!/usr/bin/env node
/**
 * Brazilian Soccer MCP — Entrypoint
 * ---------------------------------
 * Context: Boots the MCP server over stdio. It loads every provided Kaggle
 * dataset into a `SoccerStore`, wires the store into the protocol adapter
 * (`server.ts`), and connects a stdio transport so an MCP-compatible LLM client
 * can call the soccer query tools. Startup diagnostics are written to stderr so
 * they never corrupt the stdio JSON-RPC stream on stdout.
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createStore, resolveDataDir } from "./data.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const dataDir = resolveDataDir();
  const store = createStore(dataDir);
  console.error(
    `[brazilian-soccer-mcp] loaded ${store.matches.length} matches, ` +
      `${store.players.length} players, ${store.teamCount()} teams from ${dataDir}`,
  );

  const server = createServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[brazilian-soccer-mcp] server ready on stdio");
}

main().catch((err) => {
  console.error("[brazilian-soccer-mcp] fatal:", err);
  process.exit(1);
});
