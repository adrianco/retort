/**
 * tests/server.test.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   End-to-end BDD specs for the MCP server. A real MCP Client is linked to the
 *   server over an in-memory transport pair, then tools are listed and invoked
 *   exactly as a downstream LLM client would — verifying the wiring between the
 *   MCP layer, the services and the formatters.
 * -----------------------------------------------------------------------------
 */

import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";

let client: Client;

async function callText(name: string, args: Record<string, unknown>): Promise<string> {
  const res = (await client.callTool({ name, arguments: args })) as {
    content: Array<{ type: string; text?: string }>;
  };
  return res.content.map((c) => c.text ?? "").join("\n");
}

describe("Feature: MCP server tools", () => {
  beforeAll(async () => {
    const server = createServer();
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    client = new Client({ name: "test-client", version: "1.0.0" });
    await Promise.all([
      client.connect(clientTransport),
      server.connect(serverTransport),
    ]);
  });

  describe("Scenario: Tool discovery", () => {
    it("Given a connected client, Then all capability tools are advertised", async () => {
      const { tools } = await client.listTools();
      const names = tools.map((t) => t.name);
      for (const expected of [
        "search_matches",
        "head_to_head",
        "team_record",
        "search_players",
        "club_player_breakdown",
        "standings",
        "list_seasons",
        "match_statistics",
        "biggest_wins",
        "team_rankings",
      ]) {
        expect(names).toContain(expected);
      }
    });
  });

  describe("Scenario: Answering sample questions through tools", () => {
    it("'Who won the 2019 Brasileirão?' -> standings names Flamengo as Champion", async () => {
      const text = await callText("standings", { competition: "Brasileirão", season: 2019 });
      expect(text).toMatch(/Flamengo/);
      expect(text).toMatch(/Champion/);
    });

    it("'Show me Flamengo vs Fluminense' -> head_to_head returns a tally", async () => {
      const text = await callText("head_to_head", { teamA: "Flamengo", teamB: "Fluminense" });
      expect(text).toMatch(/Head-to-head/);
      expect(text).toMatch(/Flamengo \d+ wins/);
    });

    it("'Who are the top Brazilian players?' -> search_players returns Neymar first", async () => {
      const text = await callText("search_players", { nationality: "Brazil", limit: 5 });
      expect(text).toMatch(/Neymar/);
      expect(text).toMatch(/Overall: 9\d/);
    });

    it("'Corinthians 2022 home record' -> team_record returns a win rate", async () => {
      const text = await callText("team_record", {
        team: "Corinthians",
        season: 2022,
        competition: "Brasileirão",
        venue: "home",
      });
      expect(text).toMatch(/Corinthians/);
      expect(text).toMatch(/Win rate:/);
    });

    it("'Average goals in the Brasileirão' -> match_statistics reports an average", async () => {
      const text = await callText("match_statistics", { competition: "Brasileirão" });
      expect(text).toMatch(/Average goals per match: \d\.\d{2}/);
    });

    it("'Biggest wins' -> biggest_wins lists ranked scorelines", async () => {
      const text = await callText("biggest_wins", { limit: 3 });
      expect(text).toMatch(/margin \d/);
    });
  });

  describe("Scenario: Performance", () => {
    it("Given an aggregate query, Then it responds well under 5 seconds", async () => {
      const start = Date.now();
      await callText("standings", { competition: "Brasileirão", season: 2018 });
      expect(Date.now() - start).toBeLessThan(5000);
    });
  });
});
