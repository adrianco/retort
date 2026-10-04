// Protocol driver: the only layer that knows the system is an MCP server over stdio.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { expect } from "vitest";

export class McpDriver {
  private client = new Client({ name: "acceptance-tests", version: "1.0.0" });
  last: { text: string; data: any; elapsedMs: number } = { text: "", data: {}, elapsedMs: 0 };

  async start() {
    await this.client.connect(new StdioClientTransport({ command: "node", args: ["dist/server.js"] }));
  }
  async stop() { await this.client.close(); }

  async call(tool: string, args: Record<string, unknown>) {
    const t0 = Date.now();
    const res: any = await this.client.callTool({ name: tool, arguments: args });
    const elapsedMs = Date.now() - t0;
    expect(res.isError, `tool ${tool} failed: ${JSON.stringify(res.content)}`).toBeFalsy();
    this.last = { text: res.content.map((c: any) => c.text).join("\n"), data: res.structuredContent, elapsedMs };
    return this.last;
  }
}
