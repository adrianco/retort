#!/usr/bin/env node
import { pathToFileURL } from "node:url";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./server.js";

export { SoccerDataStore } from "./data-store.js";
export { SoccerService } from "./service.js";
export { NaturalLanguageQuery } from "./query.js";
export { createServer } from "./server.js";
export * from "./types.js";
export * from "./normalize.js";

async function main(): Promise<void> {
  const server = await createServer({ dataDirectory: process.env.SOCCER_DATA_DIR });
  await server.connect(new StdioServerTransport());
}

const invokedDirectly = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invokedDirectly) {
  main().catch((error: unknown) => {
    console.error("Failed to start Brazilian Soccer MCP server:", error);
    process.exitCode = 1;
  });
}
