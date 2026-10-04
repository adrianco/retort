import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadDataset } from "./data.js";
import { createServer } from "./server.js";

await createServer(loadDataset()).connect(new StdioServerTransport());
