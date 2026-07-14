/**
 * ============================================================================
 * File: tests/mcpServer.test.ts
 * Feature: MCP server tool interface
 * ----------------------------------------------------------------------------
 * Context:
 *   End-to-end GWT scenarios that exercise the server exactly as an MCP client
 *   (LLM) would: a Client is linked to the server over an in-memory transport,
 *   tools are listed, and representative tool calls from each capability
 *   category are invoked and asserted on both text and structured output.
 * ============================================================================
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";
import { graph } from "./helpers.js";

let client: Client;

beforeAll(async () => {
  const server = createServer(graph());
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
});

afterAll(async () => {
  await client.close();
});

function textOf(result: any): string {
  return (result.content ?? []).map((c: any) => c.text ?? "").join("\n");
}

describe("Feature: MCP server tool interface", () => {
  it("Scenario: the server advertises all capability tools", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name);
    expect(names).toEqual(
      expect.arrayContaining([
        "search_matches",
        "head_to_head",
        "team_record",
        "team_competitions",
        "search_players",
        "standings",
        "competition_stats",
        "biggest_wins",
        "list_competitions",
      ]),
    );
  });

  it("Scenario: search_matches returns formatted matches", async () => {
    const res = await client.callTool({
      name: "search_matches",
      arguments: { team: "Flamengo", opponent: "Fluminense", limit: 5 },
    });
    expect(textOf(res)).toContain("Flamengo");
    expect((res as any).structuredContent.count).toBeGreaterThan(0);
  });

  it("Scenario: head_to_head reports a tally", async () => {
    const res = await client.callTool({
      name: "head_to_head",
      arguments: { teamA: "Palmeiras", teamB: "Santos" },
    });
    const h = (res as any).structuredContent.headToHead;
    expect(h.totalMatches).toBeGreaterThan(0);
    expect(textOf(res)).toContain("head-to-head");
  });

  it("Scenario: standings names the 2019 champion", async () => {
    const res = await client.callTool({
      name: "standings",
      arguments: { competition: "Brasileirão Série A", season: 2019, limit: 5 },
    });
    expect(textOf(res)).toContain("Flamengo");
    expect(textOf(res)).toContain("Champion");
    const rows = (res as any).structuredContent.standings;
    expect(rows[0].points).toBe(90);
  });

  it("Scenario: search_players finds Brazilians sorted by rating", async () => {
    const res = await client.callTool({
      name: "search_players",
      arguments: { nationality: "Brazil", limit: 3 },
    });
    const players = (res as any).structuredContent.players;
    expect(players).toHaveLength(3);
    expect(players[0].name).toContain("Neymar");
  });

  it("Scenario: competition_stats returns aggregate numbers", async () => {
    const res = await client.callTool({
      name: "competition_stats",
      arguments: { competition: "Brasileirão Série A" },
    });
    const stats = (res as any).structuredContent.stats;
    expect(stats.averageGoalsPerMatch).toBeGreaterThan(2);
  });

  it("Scenario: an unknown team is handled gracefully", async () => {
    const res = await client.callTool({
      name: "search_matches",
      arguments: { team: "Definitely Not A Team" },
    });
    expect((res as any).isError).toBeFalsy();
    expect((res as any).structuredContent.count).toBe(0);
  });
});
