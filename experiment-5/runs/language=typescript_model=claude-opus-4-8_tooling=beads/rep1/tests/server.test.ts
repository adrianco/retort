/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Feature: MCP server integration
 * Drives the fully-wired server over an in-memory transport with a real MCP
 * client: lists the registered tools and invokes representative ones from each
 * capability category, asserting on the returned text content.
 * ============================================================================
 */

import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";
import { dataset } from "./helpers.js";

let client: Client;

beforeAll(async () => {
  const server = createServer(dataset());
  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
});

async function callText(name: string, args: Record<string, unknown>): Promise<string> {
  const res = (await client.callTool({ name, arguments: args })) as {
    content: Array<{ type: string; text: string }>;
  };
  return res.content.map((c) => c.text).join("\n");
}

describe("Feature: MCP server integration", () => {
  it("Scenario: exposes all nine capability tools", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual(
      [
        "aggregate_stats",
        "biggest_wins",
        "club_squad",
        "head_to_head",
        "search_matches",
        "search_players",
        "season_summary",
        "standings",
        "team_stats",
        "top_scoring_teams",
      ].sort()
    );
  });

  it("Scenario: search_matches returns formatted matches", async () => {
    const text = await callText("search_matches", {
      team: "Flamengo",
      opponent: "Fluminense",
    });
    expect(text).toMatch(/Flamengo/);
    expect(text).toMatch(/Found \d+ match/);
  });

  it("Scenario: standings tool returns the 2019 champion", async () => {
    const text = await callText("standings", {
      competition: "Brasileirão Série A",
      season: 2019,
    });
    expect(text).toMatch(/Flamengo/);
    expect(text).toMatch(/90 pts/);
  });

  it("Scenario: search_players finds Brazilians", async () => {
    const text = await callText("search_players", {
      nationality: "Brazil",
      limit: 3,
    });
    expect(text).toMatch(/Brazil/);
    expect(text).toMatch(/Overall/);
  });

  it("Scenario: aggregate_stats reports an average", async () => {
    const text = await callText("aggregate_stats", {
      competition: "Brasileirão Série A",
    });
    expect(text).toMatch(/Average goals per match/);
  });

  it("Scenario: invalid competition is rejected by the schema", async () => {
    const res = (await client.callTool({
      name: "standings",
      arguments: { competition: "Premier League", season: 2019 },
    })) as { isError?: boolean; content: Array<{ text: string }> };
    // The schema rejects the unknown competition, surfaced as a tool error.
    expect(res.isError).toBe(true);
    expect(res.content[0].text).toMatch(/Invalid enum value/i);
  });
});
