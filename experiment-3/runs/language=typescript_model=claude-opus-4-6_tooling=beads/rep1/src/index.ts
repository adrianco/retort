import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { SoccerData } from "./data.js";
import { createServer } from "./server.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = process.env.DATA_DIR || join(__dirname, "..", "data", "kaggle");

const data = new SoccerData(dataDir);
const server = createServer(data);

const transport = new StdioServerTransport();
await server.connect(transport);
