#!/usr/bin/env node
/**
 * Entry point: serves the Brazilian soccer MCP server over stdio.
 * Data is loaded eagerly at startup so the first query is fast.
 * Set BRAZIL_SOCCER_DATA_DIR to point at a different copy of data/kaggle.
 */
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { getDataset } from "./data.js";
import { createServer } from "./server.js";

async function main() {
  const ds = getDataset();
  console.error(
    `brazilian-soccer-mcp: loaded ${ds.matches.length} matches, ${ds.players.length} players, ${ds.teams.teams.size} teams in ${ds.loadMs.toFixed(0)} ms`,
  );
  const { server } = createServer(ds);
  await server.connect(new StdioServerTransport());
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
