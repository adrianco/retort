/**
 * Feature: MCP server integration
 *
 * The tools must be reachable through the Model Context Protocol itself,
 * not just via direct function calls. Uses the SDK's in-memory transport
 * to run a real client/server session.
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createServer } from "../src/server.js";
import { dataset } from "./helpers.js";

let client: Client;

async function callText(name: string, args: Record<string, unknown> = {}): Promise<string> {
  const res = await client.callTool({ name, arguments: args });
  const content = res.content as { type: string; text: string }[];
  expect(content.length).toBeGreaterThan(0);
  expect(content[0].type).toBe("text");
  return content[0].text;
}

beforeAll(async () => {
  const server = createServer(dataset());
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
});

afterAll(async () => {
  await client.close();
});

describe("Feature: MCP server integration", () => {
  describe("Scenario: Tools are discoverable", () => {
    it("Given a connected MCP client, When tools are listed, Then all query tools are advertised", async () => {
      const { tools } = await client.listTools();
      const names = tools.map((t) => t.name).sort();
      expect(names).toEqual(
        [
          "best_records",
          "biggest_wins",
          "competition_stats",
          "data_summary",
          "head_to_head",
          "league_standings",
          "player_profile",
          "search_matches",
          "search_players",
          "team_competitions",
          "team_stats",
        ].sort(),
      );
      for (const t of tools) expect(t.description).toBeTruthy();
    });
  });

  describe("Scenario: Match search over MCP", () => {
    it("Given the server, When search_matches is called for Flamengo vs Fluminense, Then formatted match lines return", async () => {
      const text = await callText("search_matches", { team: "Flamengo", opponent: "Fluminense" });
      expect(text).toMatch(/Found \d+ match/);
      expect(text).toMatch(/\d{4}-\d{2}-\d{2}/);
      expect(text).toContain("Flamengo");
      expect(text).toContain("Fluminense");
    });

    it("When called with criteria matching nothing, Then a friendly empty answer returns", async () => {
      const text = await callText("search_matches", { team: "Real Madrid", season: 1950 });
      expect(text).toContain("No matches found");
    });
  });

  describe("Scenario: Head-to-head over MCP", () => {
    it("When head_to_head is called, Then the record summary includes wins/draws and recent meetings", async () => {
      const text = await callText("head_to_head", { team1: "Palmeiras", team2: "Corinthians" });
      expect(text).toMatch(/meetings in dataset/);
      expect(text).toMatch(/wins/);
      expect(text).toMatch(/draws/);
    });
  });

  describe("Scenario: Standings over MCP", () => {
    it("When league_standings is called for 2019, Then Flamengo tops the table with 90 points", async () => {
      const text = await callText("league_standings", { season: 2019 });
      expect(text).toContain("Flamengo");
      expect(text).toContain("90");
      expect(text).toMatch(/Champion.*Flamengo/);
    });
  });

  describe("Scenario: Player tools over MCP", () => {
    it("When search_players is called for Brazilians, Then a ranked list returns", async () => {
      const text = await callText("search_players", { nationality: "Brazil", limit: 5 });
      expect(text).toMatch(/1\. .*Overall: 9\d/);
    });

    it("When player_profile is called for Neymar, Then a detailed profile returns", async () => {
      const text = await callText("player_profile", { name: "Neymar" });
      expect(text).toContain("Neymar");
      expect(text).toMatch(/Overall: \d+/);
      expect(text).toMatch(/Top skills:/);
    });
  });

  describe("Scenario: Analytics over MCP", () => {
    it("When competition_stats is called, Then averages and win rates return", async () => {
      const text = await callText("competition_stats", { competition: "Brasileirão" });
      expect(text).toMatch(/Average goals per match: \d\.\d{2}/);
      expect(text).toMatch(/Home wins: \d+/);
    });

    it("When data_summary is called, Then all six source files are reported", async () => {
      const text = await callText("data_summary");
      for (const f of [
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
        "fifa_data.csv",
      ]) {
        expect(text).toContain(f);
      }
    });
  });
});
