import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { describe, it } from "node:test";
import { join } from "node:path";
import { createServer } from "../src/index.js";

const server = createServer(join(process.cwd(), "data", "kaggle"));

describe("MCP protocol surface", () => {
  it("Given a spawned stdio server, when JSON-RPC lines are sent, then protocol responses are emitted on stdout", async () => {
    const child = spawn(process.execPath, [join(process.cwd(), "dist", "src", "index.js")], { cwd: process.cwd(), stdio: ["pipe", "pipe", "pipe"] });
    const responses = await new Promise<Array<Record<string, unknown>>>((resolve, reject) => {
      const collected: Array<Record<string, unknown>> = [];
      let buffer = "";
      const timeout = setTimeout(() => reject(new Error("stdio server response timed out")), 5_000);
      child.stdout.setEncoding("utf8");
      child.stdout.on("data", (chunk: string) => {
        buffer += chunk;
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) if (line) collected.push(JSON.parse(line) as Record<string, unknown>);
        if (collected.length === 2) {
          clearTimeout(timeout);
          resolve(collected);
        }
      });
      child.once("error", reject);
      child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id: 10, method: "initialize", params: { protocolVersion: "2025-11-25" } })}\n`);
      child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id: 11, method: "tools/list" })}\n`);
    }).finally(() => child.kill());
    assert.deepEqual(responses.map((response) => response.id), [10, 11]);
    assert.ok((responses[0]?.result as Record<string, unknown>).serverInfo);
    assert.ok(((responses[1]?.result as Record<string, unknown>).tools as unknown[]).length > 0);
  });

  it("Given an MCP client, when initialized, then server identity and capabilities are negotiated", async () => {
    const response = await server.handle({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "test", version: "1" } } });
    assert.ok(response?.result);
    const result = response.result as Record<string, unknown>;
    assert.equal(result.protocolVersion, "2025-11-25");
    assert.equal((result.serverInfo as Record<string, unknown>).name, "brazilian-soccer-mcp");
  });

  it("Given tools/list, when requested, then all read-only query capabilities are discoverable", async () => {
    const response = await server.handle({ jsonrpc: "2.0", id: 2, method: "tools/list" });
    const tools = ((response?.result as Record<string, unknown>).tools as Array<Record<string, unknown>>);
    assert.equal(tools.length, 9);
    assert.ok(tools.some((tool) => tool.name === "answer_soccer_question"));
    assert.ok(tools.some((tool) => tool.name === "explore_soccer_graph"));
    assert.ok(tools.every((tool) => (tool.inputSchema as Record<string, unknown>).type === "object"));
  });

  it("Given a valid tools/call, when searching head-to-head matches, then text and structured content are returned", async () => {
    const response = await server.handle({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "compare_teams", arguments: { team1: "Flamengo", team2: "Fluminense" } } });
    assert.equal(response?.error, undefined);
    const result = response?.result as Record<string, unknown>;
    assert.ok(Array.isArray(result.content));
    assert.ok(result.structuredContent);
  });

  it("Given every registered analytics tool, when called through MCP, then each handler returns grounded structured data", async () => {
    const calls: Array<[string, Record<string, unknown>]> = [
      ["search_matches", { team: "Flamengo", season: 2019, competition: "Brasileirão" }],
      ["get_team_statistics", { team: "Flamengo", season: 2019, competition: "Brasileirão" }],
      ["compare_teams", { team1: "Flamengo", team2: "Fluminense" }],
      ["search_players", { name: "Neymar" }],
      ["get_standings", { season: 2019, competition: "Brasileirão" }],
      ["get_competition_statistics", { competition: "Copa Libertadores", season: 2018 }],
      ["explore_soccer_graph", { team: "Santos", season: 2019, limit: 5 }],
      ["answer_soccer_question", { question: "Who won the 2019 Brasileirão?" }],
      ["dataset_summary", {}],
    ];
    for (let index = 0; index < calls.length; index++) {
      const [name, args] = calls[index]!;
      const response = await server.handle({ jsonrpc: "2.0", id: 100 + index, method: "tools/call", params: { name, arguments: args } });
      assert.equal(response?.error, undefined, `${name} returned a protocol error`);
      const result = response?.result as Record<string, unknown>;
      assert.ok(result.structuredContent !== undefined, `${name} omitted structuredContent`);
      assert.ok(Array.isArray(result.content), `${name} omitted MCP content`);
    }
  });

  it("Given resources and prompts, when read, then dataset coverage and guided analysis are exposed", async () => {
    const resources = await server.handle({ jsonrpc: "2.0", id: 4, method: "resources/list" });
    assert.equal(((resources?.result as Record<string, unknown>).resources as unknown[]).length, 2);
    const prompt = await server.handle({ jsonrpc: "2.0", id: 5, method: "prompts/get", params: { name: "analyze_brazilian_soccer", arguments: { question: "Who won in 2019?" } } });
    assert.ok(((prompt?.result as Record<string, unknown>).messages as unknown[]).length > 0);
  });

  it("Given invalid arguments, when a tool is called, then a JSON-RPC error helps the model self-correct", async () => {
    const response = await server.handle({ jsonrpc: "2.0", id: 6, method: "tools/call", params: { name: "compare_teams", arguments: { team1: "Flamengo" } } });
    assert.equal(response?.error?.code, -32602);
    assert.match(response?.error?.message ?? "", /team2/);
  });
});
