#!/usr/bin/env node
import path from "node:path";
import { fileURLToPath } from "node:url";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadAllData } from "./dataLoader.js";
import { createServer } from "./server.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = process.env.BRAZILIAN_SOCCER_DATA_DIR
  ?? path.resolve(__dirname, "..", "data", "kaggle");

async function main() {
  const data = loadAllData(DATA_DIR);
  const server = createServer(data);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error("Fatal error starting Brazilian Soccer MCP server:", error);
  process.exit(1);
});
