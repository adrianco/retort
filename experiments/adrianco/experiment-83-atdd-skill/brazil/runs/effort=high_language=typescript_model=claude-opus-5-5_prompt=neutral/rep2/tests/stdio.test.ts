/**
 * Launches the real entry point as a child process and talks MCP over stdio,
 * as an LLM host (e.g. Claude Desktop / Claude Code) would.
 * Uses the compiled dist/index.js when present, otherwise runs src/index.ts via tsx.
 */
import { existsSync } from "node:fs";
import { join } from "node:path";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const root = join(import.meta.dirname, "..");
const dist = join(root, "dist", "index.js");
const [command, args] = existsSync(dist)
  ? [process.execPath, [dist]]
  : [join(root, "node_modules", ".bin", "tsx"), [join(root, "src", "index.ts")]];

let client: Client;

beforeAll(async () => {
  client = new Client({ name: "stdio-test", version: "1.0.0" });
  await client.connect(new StdioClientTransport({ command, args, cwd: root, stderr: "ignore" }));
});

afterAll(async () => {
  await client?.close();
});

describe("stdio server", () => {
  it("serves tools over stdio", async () => {
    const { tools } = await client.listTools();
    expect(tools.length).toBe(17);
    const r = (await client.callTool({ name: "league_standings", arguments: { season: 2019, limit: 1 } })) as {
      content: { text: string }[];
    };
    expect(r.content[0].text).toContain("1. Flamengo - 90 pts (28W, 6D, 4L)");
  });
});
