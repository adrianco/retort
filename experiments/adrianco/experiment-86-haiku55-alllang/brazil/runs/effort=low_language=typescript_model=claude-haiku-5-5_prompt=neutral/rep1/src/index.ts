#!/usr/bin/env node
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./server.js";
import { DEFAULT_DATA_DIR, loadDataset } from "./loader.js";
import type { Dataset } from "./model.js";

/**
 * Entry point: serve the Brazilian soccer tools over stdio.
 * Set BRAZIL_SOCCER_DATA_DIR to point at a different CSV directory.
 * Logs go to stderr because stdout carries the MCP protocol.
 */
async function main(): Promise<void> {
  const dir = process.env.BRAZIL_SOCCER_DATA_DIR ?? DEFAULT_DATA_DIR;
  let dataset: Dataset | undefined;
  const getDataset = (): Dataset => {
    dataset ??= loadDataset(dir);
    return dataset;
  };

  const server = createServer(getDataset);
  await server.connect(new StdioServerTransport());
  console.error(`brazilian-soccer MCP server ready (data: ${dir})`);
}

main().catch((err: unknown) => {
  console.error("Failed to start brazilian-soccer MCP server:", err);
  process.exit(1);
});
