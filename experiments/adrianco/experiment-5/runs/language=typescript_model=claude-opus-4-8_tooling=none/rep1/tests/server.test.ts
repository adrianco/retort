/**
 * Context
 * -------
 * Feature: MCP Server integration.
 * Connects a real MCP Client to the server over an in-memory transport pair
 * and exercises the tools end-to-end (tool listing, a match search, a player
 * search and a standings computation), asserting on both the human-readable
 * text content and the structured JSON payload.
 */

import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";

let client: Client;

beforeAll(async () => {
  // Given a running MCP server connected to a client over in-memory transport
  const server = createServer();
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
});

function textOf(res: any): string {
  return (res.content ?? []).map((c: any) => c.text ?? "").join("\n");
}

describe("Feature: MCP Server", () => {
  it("Scenario: lists all expected tools", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual(
      [
        "biggest_wins",
        "competition_standings",
        "competition_stats",
        "get_player",
        "head_to_head",
        "search_matches",
        "search_players",
        "team_competitions",
        "team_stats",
        "top_scoring_teams",
      ].sort(),
    );
  });

  it("Scenario: search_matches returns text and structured data", async () => {
    const res: any = await client.callTool({
      name: "search_matches",
      arguments: { team: "Flamengo", opponent: "Fluminense", limit: 5 },
    });
    expect(res.isError).toBeFalsy();
    expect(textOf(res)).toMatch(/Flamengo|Fluminense/);
    const data = res.structuredContent?.data;
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBeGreaterThan(0);
  });

  it("Scenario: competition_standings returns the 2019 champion", async () => {
    const res: any = await client.callTool({
      name: "competition_standings",
      arguments: { competition: "Brasileirão", season: 2019, limit: 5 },
    });
    expect(textOf(res)).toMatch(/Flamengo/);
    expect(textOf(res)).toMatch(/90 pts/);
    expect(res.structuredContent?.data?.[0]?.points).toBe(90);
  });

  it("Scenario: search_players finds Brazilians sorted by rating", async () => {
    const res: any = await client.callTool({
      name: "search_players",
      arguments: { nationality: "Brazil", limit: 3 },
    });
    const data = res.structuredContent?.data;
    expect(data.length).toBe(3);
    expect(data[0].name).toMatch(/Neymar/i);
  });

  it("Scenario: get_player returns full detail for a known player", async () => {
    const res: any = await client.callTool({
      name: "get_player",
      arguments: { name: "Gabriel Jesus" },
    });
    expect(textOf(res)).toMatch(/Gabriel Jesus/i);
    expect(textOf(res)).toMatch(/Nationality: Brazil/);
  });

  it("Scenario: unknown player is handled gracefully", async () => {
    const res: any = await client.callTool({
      name: "get_player",
      arguments: { name: "Nonexistent Player Zzz" },
    });
    expect(textOf(res)).toMatch(/No player found/i);
  });
});
