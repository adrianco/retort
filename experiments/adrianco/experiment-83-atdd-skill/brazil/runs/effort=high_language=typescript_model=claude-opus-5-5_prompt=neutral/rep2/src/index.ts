#!/usr/bin/env node
/**
 * Entry point: loads the datasets and serves the MCP tools over stdio.
 *
 *   node dist/index.js [--data-dir path/to/kaggle]
 *
 * The data directory defaults to ./data/kaggle relative to the package, and
 * can also be set with the BRAZIL_SOCCER_DATA_DIR environment variable.
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SoccerKnowledgeBase } from "./queries.js";
import { createServer } from "./server.js";

async function main(): Promise<void> {
  const flag = process.argv.indexOf("--data-dir");
  const dataDir = (flag >= 0 ? process.argv[flag + 1] : undefined) ?? process.env.BRAZIL_SOCCER_DATA_DIR;
  const kb = SoccerKnowledgeBase.load(dataDir);
  const s = kb.data.stats;
  // stdout carries the MCP protocol; diagnostics go to stderr.
  console.error(
    `brazilian-soccer-mcp: loaded ${kb.data.canonical.length} unique matches, ${kb.data.teams.size} teams, ` +
      `${kb.data.players.length} players in ${s.loadMs.toFixed(0)} ms`,
  );
  const server = createServer(kb);
  await server.connect(new StdioServerTransport());
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
