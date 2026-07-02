import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";
import type { Match, Player } from "../src/types.js";

function makeMatch(overrides: Partial<Match>): Match {
  return {
    id: "m1",
    source: "Brasileirao_Matches.csv",
    competition: "Brasileirão",
    date: new Date("2023-09-03T00:00:00Z"),
    season: 2023,
    homeTeam: "Flamengo",
    awayTeam: "Fluminense",
    homeGoals: 2,
    awayGoals: 1,
    round: "22",
    ...overrides,
  };
}

const matches: Match[] = [makeMatch({ id: "1" })];
const players: Player[] = [
  { id: "1", name: "Neymar Jr", nationality: "Brazil", club: "Paris Saint-Germain", overall: 92, position: "LW" },
];

let client: Client;

beforeAll(async () => {
  const server = createServer({ matches, players });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([client.connect(clientTransport), server.connect(serverTransport)]);
});

describe("MCP server wiring", () => {
  it("lists all registered tools", async () => {
    const result = await client.listTools();
    const names = result.tools.map((t) => t.name).sort();
    expect(names).toEqual([
      "compare_teams",
      "competition_standings",
      "dataset_statistics",
      "list_team_competitions",
      "player_club_context",
      "search_matches",
      "search_players",
      "team_record",
    ]);
  });

  it("calls search_matches over the real MCP protocol and returns formatted text", async () => {
    const result = await client.callTool({ name: "search_matches", arguments: { team: "Flamengo" } });
    const content = result.content as Array<{ type: string; text: string }>;
    expect(content[0].text).toContain("Flamengo 2-1 Fluminense");
  });

  it("calls search_players over the real MCP protocol", async () => {
    const result = await client.callTool({ name: "search_players", arguments: { nationality: "Brazil" } });
    const content = result.content as Array<{ type: string; text: string }>;
    expect(content[0].text).toContain("Neymar Jr");
  });
});
