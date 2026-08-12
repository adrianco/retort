#!/usr/bin/env node
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadSoccerData } from "./data-loader.js";
import { BrazilianSoccerMcpServer, serveStdio } from "./mcp-server.js";
import { SoccerService } from "./soccer-service.js";

export function resolveDataDirectory(): string {
  if (process.env.BRAZILIAN_SOCCER_DATA_DIR) return resolve(process.env.BRAZILIAN_SOCCER_DATA_DIR);
  const moduleDirectory = dirname(fileURLToPath(import.meta.url));
  const candidates = [join(process.cwd(), "data", "kaggle"), join(moduleDirectory, "..", "..", "data", "kaggle"), join(moduleDirectory, "..", "data", "kaggle")];
  const found = candidates.find((candidate) => existsSync(join(candidate, "Brasileirao_Matches.csv")));
  if (!found) throw new Error("Could not find data/kaggle. Set BRAZILIAN_SOCCER_DATA_DIR to the dataset directory.");
  return found;
}

export function createServer(dataDirectory = resolveDataDirectory()): BrazilianSoccerMcpServer {
  return new BrazilianSoccerMcpServer(new SoccerService(loadSoccerData(dataDirectory)));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  serveStdio(createServer()).catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
