import path from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { describe, expect, it } from "vitest";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

describe("documented stdio entrypoint", () => {
  it("starts and returns the real 2019 Série A standings", async () => {
    const client = new Client({ name: "stdio-smoke-test", version: "1.0.0" });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [path.join(projectRoot, "dist/index.js")],
      cwd: projectRoot,
      stderr: "pipe"
    });

    try {
      await client.connect(transport);
      const tools = await client.listTools();
      expect(tools.tools.some((tool) => tool.name === "calculate_standings")).toBe(true);

      const response = await client.callTool({
        name: "calculate_standings",
        arguments: { season: 2019, competition: "Brasileirão Serie A" }
      });

      expect(response.isError).not.toBe(true);
      expect(response.content).toEqual(expect.arrayContaining([
        expect.objectContaining({ type: "text", text: expect.stringContaining("Flamengo-RJ") })
      ]));
      expect(response.structuredContent).toMatchObject({ season: 2019 });
      expect(response.structuredContent?.standings).toEqual(expect.arrayContaining([
        expect.objectContaining({ position: 1, team: "Flamengo-RJ", points: 90 })
      ]));
    } finally {
      await client.close();
    }
  }, 15_000);
});
