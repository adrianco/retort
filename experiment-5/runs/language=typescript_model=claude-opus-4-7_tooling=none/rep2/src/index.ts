#!/usr/bin/env node
import { resolve } from "node:path";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadAll } from "./loader.js";
import { buildServer } from "./server.js";

async function main(): Promise<void> {
  const dataDir = resolve(process.env.BRAZILIAN_SOCCER_DATA_DIR ?? "./data/kaggle");
  process.stderr.write(`[brazilian-soccer-mcp] loading data from ${dataDir}\n`);
  const dataset = loadAll(dataDir);
  process.stderr.write(
    `[brazilian-soccer-mcp] loaded ${dataset.matches.length} matches and ${dataset.players.length} players\n`,
  );
  const server = buildServer(dataset);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  process.stderr.write(`[brazilian-soccer-mcp] fatal: ${err instanceof Error ? err.stack ?? err.message : String(err)}\n`);
  process.exit(1);
});
