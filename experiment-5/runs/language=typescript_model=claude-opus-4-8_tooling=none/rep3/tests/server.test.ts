/**
 * ============================================================================
 * Context: BDD tests — MCP Tool Surface
 * ----------------------------------------------------------------------------
 * Feature : The MCP server exposes the expected tools and they return
 *           formatted text answers. Uses the in-memory transport pair from the
 *           MCP SDK so the full client→server round-trip is exercised.
 * ============================================================================
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";
import { loadDataset } from "../src/dataLoader.js";

let client: Client;

async function callText(name: string, args: Record<string, unknown>): Promise<string> {
  const res = (await client.callTool({ name, arguments: args })) as {
    content: Array<{ type: string; text?: string }>;
  };
  return res.content.map((c) => c.text ?? "").join("\n");
}

describe("Feature: MCP server tool surface", () => {
  beforeAll(async () => {
    // Given a connected client and server over an in-memory transport
    const server = createServer(loadDataset());
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    client = new Client({ name: "test-client", version: "1.0.0" });
    await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  });

  afterAll(async () => {
    await client.close();
  });

  it("Scenario: all expected tools are registered", async () => {
    // When I list the available tools
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    // Then the spec's capability tools are present
    expect(names).toEqual(
      expect.arrayContaining([
        "search_matches",
        "team_stats",
        "head_to_head",
        "team_competitions",
        "search_players",
        "competition_standings",
        "list_competitions",
        "match_statistics",
      ])
    );
  });

  it("Scenario: search_matches answers a derby question", async () => {
    const out = await callText("search_matches", { team: "Flamengo", opponent: "Fluminense" });
    expect(out).toMatch(/Found \d+ match/);
    expect(out.toLowerCase()).toContain("flamengo");
    expect(out.toLowerCase()).toContain("fluminense");
  });

  it("Scenario: team_stats returns a record", async () => {
    const out = await callText("team_stats", { team: "Palmeiras", season: 2018 });
    expect(out).toContain("Wins:");
    expect(out).toContain("Win rate:");
  });

  it("Scenario: search_players finds Brazilian players", async () => {
    const out = await callText("search_players", { nationality: "Brazil", limit: 5 });
    expect(out).toMatch(/player/);
    expect(out).toMatch(/Overall:/);
  });

  it("Scenario: competition_standings crowns the 2019 champion", async () => {
    const out = await callText("competition_standings", { competition: "Série A", season: 2019 });
    expect(out).toContain("Final Standings");
    expect(out).toContain("Champion");
  });

  it("Scenario: match_statistics summary reports goals per match", async () => {
    const out = await callText("match_statistics", { competition: "Série A", mode: "summary" });
    expect(out).toContain("Average goals per match:");
  });
});
