#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { DataStore } from "./types.js";
declare function ensureData(): DataStore;
declare const server: McpServer;
export { server, ensureData };
//# sourceMappingURL=index.d.ts.map