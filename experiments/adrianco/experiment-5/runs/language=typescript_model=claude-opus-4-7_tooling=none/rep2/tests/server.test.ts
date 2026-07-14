import { describe, it, expect, beforeAll } from "vitest";
import { resolve } from "node:path";
import { loadAll } from "../src/loader.js";
import { buildServer } from "../src/server.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import type { Dataset } from "../src/types.js";

let dataset: Dataset;
let client: Client;

beforeAll(async () => {
  dataset = loadAll(resolve(process.cwd(), "data/kaggle"));
  const server = buildServer(dataset);
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "0.0.0" });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
});

describe("MCP server", () => {
  it("lists all expected tools", async () => {
    const result = await client.listTools();
    const names = result.tools.map((t) => t.name).sort();
    for (const expected of [
      "list_competitions",
      "list_seasons",
      "find_matches",
      "head_to_head",
      "team_record",
      "list_teams",
      "top_scoring_teams",
      "standings",
      "season_summary",
      "find_players",
      "brazilian_players_by_club",
      "match_stats",
      "biggest_wins",
      "compare_seasons",
    ]) {
      expect(names).toContain(expected);
    }
  });

  it("answers a match query through the MCP layer", async () => {
    const result = await client.callTool({
      name: "find_matches",
      arguments: { team: "Flamengo", team2: "Fluminense", limit: 3 },
    });
    const content = (result.content as Array<{ type: string; text: string }>)[0];
    expect(content.type).toBe("text");
    const parsed = JSON.parse(content.text);
    expect(parsed.count).toBeGreaterThan(0);
    expect(parsed.matches.length).toBeLessThanOrEqual(3);
  });

  it("answers a player query through the MCP layer", async () => {
    const result = await client.callTool({
      name: "find_players",
      arguments: { nationality: "Brazil", limit: 5 },
    });
    const content = (result.content as Array<{ type: string; text: string }>)[0];
    const parsed = JSON.parse(content.text);
    expect(parsed.players.length).toBe(5);
    for (const p of parsed.players) expect(p.nationality.toLowerCase()).toContain("brazil");
  });

  it("computes standings via the MCP layer", async () => {
    const result = await client.callTool({
      name: "standings",
      arguments: { competition: "Brasileirao", season: 2019 },
    });
    const content = (result.content as Array<{ type: string; text: string }>)[0];
    const parsed = JSON.parse(content.text);
    expect(parsed.length).toBeGreaterThan(15);
    expect(parsed[0].rank).toBe(1);
  });
});
