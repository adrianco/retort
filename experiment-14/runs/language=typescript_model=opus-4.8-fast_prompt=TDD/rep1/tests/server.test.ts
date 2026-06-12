import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { buildServer } from "../src/server.js";
import { SoccerDatabase } from "../src/database.js";
import type { Match, Player } from "../src/types.js";
import { normalizeTeamName, normalizeName, parseDate } from "../src/normalize.js";

function mkMatch(p: Partial<Match> & { home: string; away: string; hg: number; ag: number }): Match {
  return {
    competition: p.competition ?? "Brasileirão Série A",
    date: p.date ?? parseDate("2023-01-01"),
    season: p.season ?? 2023,
    round: p.round,
    homeTeam: p.home,
    awayTeam: p.away,
    homeKey: normalizeTeamName(p.home),
    awayKey: normalizeTeamName(p.away),
    homeGoals: p.hg,
    awayGoals: p.ag,
    source: "test",
  };
}

async function makeClient() {
  const db = new SoccerDatabase({
    matches: [
      mkMatch({ home: "Flamengo-RJ", away: "Fluminense-RJ", hg: 2, ag: 1, round: "22" }),
      mkMatch({ home: "Fluminense-RJ", away: "Flamengo-RJ", hg: 1, ag: 0, round: "8" }),
    ],
    players: [
      {
        id: 1,
        name: "Gabriel Barbosa",
        nameKey: normalizeName("Gabriel Barbosa"),
        age: 26,
        nationality: "Brazil",
        overall: 83,
        potential: 85,
        club: "Flamengo",
        clubKey: normalizeTeamName("Flamengo"),
        position: "ST",
        jerseyNumber: 9,
        height: "",
        weight: "",
      } satisfies Player,
    ],
  });
  const server = buildServer(db);
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
  return client;
}

describe("MCP server", () => {
  let client: Client;
  beforeAll(async () => {
    client = await makeClient();
  });

  it("advertises all eight tools", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toContain("find_matches");
    expect(names).toContain("search_players");
    expect(names.length).toBe(8);
  });

  it("calls find_matches and returns formatted text", async () => {
    const res = await client.callTool({
      name: "find_matches",
      arguments: { team: "Flamengo", team2: "Fluminense" },
    });
    const content = res.content as Array<{ type: string; text: string }>;
    expect(content[0].type).toBe("text");
    expect(content[0].text).toContain("Head-to-head");
    expect(content[0].text).toContain("Flamengo");
  });

  it("calls search_players", async () => {
    const res = await client.callTool({
      name: "search_players",
      arguments: { name: "Gabriel" },
    });
    const content = res.content as Array<{ type: string; text: string }>;
    expect(content[0].text).toContain("Gabriel Barbosa");
  });

  it("reports validation errors for bad arguments", async () => {
    const res = await client.callTool({
      name: "standings",
      arguments: { competition: "Brasileirão" }, // missing required season
    });
    expect(res.isError).toBe(true);
  });
});
