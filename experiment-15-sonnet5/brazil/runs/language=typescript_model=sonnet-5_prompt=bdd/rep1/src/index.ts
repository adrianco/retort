import path from "node:path";
import { fileURLToPath } from "node:url";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SoccerDataStore } from "./data/store.js";
import { createServer } from "./server.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = process.env.SOCCER_DATA_DIR ?? path.join(__dirname, "..", "data", "kaggle");

async function main(): Promise<void> {
  const store = await SoccerDataStore.load(DATA_DIR);
  const server = createServer(store);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`Brazilian Soccer MCP server running (${store.matches.length} matches, ${store.players.length} players loaded from ${DATA_DIR})`);
}

main().catch((error) => {
  console.error("Fatal error starting Brazilian Soccer MCP server:", error);
  process.exit(1);
});
