import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";
import { realStore } from "./fixtures.js";

/**
 * End-to-end scenarios exercising the MCP tools through a real client/server
 * pair over an in-memory transport — the same path an LLM client would use.
 */
async function connectedClient(): Promise<Client> {
  const server = createServer(realStore());
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  return client;
}

function textOf(result: unknown): string {
  const content = (result as { content: Array<{ type: string; text?: string }> }).content;
  return content.map((c) => c.text ?? "").join("\n");
}

let client: Client;
beforeAll(async () => {
  client = await connectedClient();
});

describe("MCP tool surface", () => {
  it("given the server, when tools are listed, then every capability category is exposed", async () => {
    // When
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name);
    // Then
    expect(names).toEqual(
      expect.arrayContaining([
        "find_matches",
        "head_to_head",
        "last_meeting",
        "team_record",
        "search_players",
        "players_by_club_summary",
        "league_standings",
        "competition_champion",
        "aggregate_stats",
        "biggest_wins",
        "top_scoring_teams",
      ]),
    );
  });
});

describe("Answering sample questions through MCP tools", () => {
  it("given 'Who won the 2019 Brasileirão?', when league_standings is called, then Flamengo tops the table", async () => {
    // When
    const result = await client.callTool({
      name: "league_standings",
      arguments: { season: 2019 },
    });
    // Then
    const text = textOf(result);
    expect(text).toContain("1. Flamengo");
    expect(text).toContain("Champion");
  });

  it("given 'What matches did Palmeiras play in 2023?', when find_matches is called, then Palmeiras matches are returned", async () => {
    // When
    const result = await client.callTool({
      name: "find_matches",
      arguments: { team: "Palmeiras", season: 2023 },
    });
    // Then
    const text = textOf(result);
    expect(text.toLowerCase()).toContain("palmeiras");
  });

  it("given 'Who is Neymar?', when search_players is called, then Neymar is found", async () => {
    // When
    const result = await client.callTool({
      name: "search_players",
      arguments: { name: "Neymar" },
    });
    // Then
    expect(textOf(result)).toContain("Neymar");
  });

  it("given 'Compare Palmeiras and Santos', when head_to_head is called, then a tally is returned", async () => {
    // When
    const result = await client.callTool({
      name: "head_to_head",
      arguments: { teamA: "Palmeiras", teamB: "Santos" },
    });
    // Then
    expect(textOf(result)).toMatch(/head-to-head/i);
  });

  it("given an unknown team, when last_meeting is called, then a graceful not-found message is returned", async () => {
    // When
    const result = await client.callTool({
      name: "last_meeting",
      arguments: { teamA: "Nonexistent United", teamB: "Palmeiras" },
    });
    // Then
    expect(textOf(result)).toMatch(/no match found/i);
  });
});
