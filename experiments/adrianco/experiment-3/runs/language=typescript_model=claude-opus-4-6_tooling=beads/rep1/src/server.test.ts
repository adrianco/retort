import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { SoccerData } from "./data.js";
import { createServer } from "./server.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = join(__dirname, "..", "data", "kaggle");

let client: Client;

beforeAll(async () => {
  const data = new SoccerData(dataDir);
  const server = createServer(data);
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([client.connect(clientTransport), server.connect(serverTransport)]);
});

describe("MCP Server Tools", () => {
  it("should list all tools", async () => {
    const result = await client.listTools();
    const names = result.tools.map((t) => t.name);
    expect(names).toContain("search_matches");
    expect(names).toContain("head_to_head");
    expect(names).toContain("team_stats");
    expect(names).toContain("search_players");
    expect(names).toContain("competition_standings");
    expect(names).toContain("statistical_analysis");
  });

  it("search_matches returns results for Flamengo", async () => {
    const result = await client.callTool({ name: "search_matches", arguments: { team: "Flamengo", limit: 5 } });
    const text = (result.content as Array<{ type: string; text: string }>)[0].text;
    expect(text).toContain("Found");
    expect(text.toLowerCase()).toContain("flamengo");
  });

  it("search_players finds players at a Brazilian club", async () => {
    const result = await client.callTool({
      name: "search_players",
      arguments: { club: "Grêmio" },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0].text;
    expect(text).toContain("Found");
    expect(text.toLowerCase()).toContain("grêmio");
  });

  it("head_to_head compares two teams", async () => {
    const result = await client.callTool({
      name: "head_to_head",
      arguments: { team1: "Flamengo", team2: "Fluminense" },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0].text;
    expect(text).toContain("wins");
    expect(text).toContain("Draws");
  });

  it("team_stats returns valid statistics", async () => {
    const result = await client.callTool({
      name: "team_stats",
      arguments: { team: "Palmeiras", season: 2019 },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0].text;
    expect(text).toContain("Matches:");
    expect(text).toContain("Wins:");
    expect(text).toContain("Win rate:");
  });

  it("search_players finds Neymar", async () => {
    const result = await client.callTool({
      name: "search_players",
      arguments: { name: "Neymar" },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0].text;
    expect(text.toLowerCase()).toContain("neymar");
  });

  it("competition_standings calculates 2019 standings", async () => {
    const result = await client.callTool({
      name: "competition_standings",
      arguments: { season: 2019 },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0].text;
    expect(text).toContain("Standings");
    expect(text).toContain("pts");
  });

  it("statistical_analysis returns averages", async () => {
    const result = await client.callTool({
      name: "statistical_analysis",
      arguments: { analysis_type: "averages" },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0].text;
    expect(text).toContain("Average goals per match");
    expect(text).toContain("Home win rate");
  });

  it("statistical_analysis returns biggest wins", async () => {
    const result = await client.callTool({
      name: "statistical_analysis",
      arguments: { analysis_type: "biggest_wins", limit: 5 },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0].text;
    expect(text).toContain("Biggest wins");
  });

  it("search_matches handles no results gracefully", async () => {
    const result = await client.callTool({
      name: "search_matches",
      arguments: { team: "NonexistentTeamXYZ" },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0].text;
    expect(text).toContain("No matches found");
  });

  it("search_players handles no results gracefully", async () => {
    const result = await client.callTool({
      name: "search_players",
      arguments: { name: "ZZZNonexistentPlayer" },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0].text;
    expect(text).toContain("No players found");
  });
});
