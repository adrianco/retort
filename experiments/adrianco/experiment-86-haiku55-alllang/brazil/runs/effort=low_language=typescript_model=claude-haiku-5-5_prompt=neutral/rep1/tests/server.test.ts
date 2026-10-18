import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { beforeAll, describe, expect, it } from "vitest";
import { DEFAULT_DATA_DIR, loadDataset } from "../src/loader.js";
import { createServer } from "../src/server.js";
import type { Dataset } from "../src/model.js";

let client: Client;
let dataset: Dataset;

async function callText(name: string, args: Record<string, unknown>): Promise<string> {
  const result = await client.callTool({ name, arguments: args });
  const first = (result.content as { type: string; text: string }[])[0];
  if (!first || first.type !== "text") throw new Error("expected text content");
  return first.text;
}

beforeAll(async () => {
  dataset = loadDataset(DEFAULT_DATA_DIR);
  const server = createServer(() => dataset);
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
});

describe("Feature: MCP tool surface", () => {
  it("Given the server, When tools are listed, Then all query tools are advertised", async () => {
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual([
      "club_squad_summary",
      "head_to_head",
      "match_statistics",
      "search_matches",
      "search_players",
      "standings",
      "team_record",
    ]);
  });

  it("Given a team and season, When search_matches is called, Then matches are listed with scores and competition", async () => {
    const text = await callText("search_matches", { team: "Palmeiras", season: 2023, limit: 3 });
    expect(text).toMatch(/^Matches found: \d+/);
    expect(text).toMatch(/- 2023-\d{2}-\d{2}: .+ \d+-\d+ .+ \(.+\)/);
  });

  it("Given a Fla-Flu query, When head_to_head is called, Then the record and recent meetings are returned", async () => {
    const text = await callText("head_to_head", { team_a: "Flamengo", team_b: "Fluminense" });
    expect(text).toContain("head-to-head in dataset");
    expect(text).toContain("Most recent:");
  });

  it("Given a season, When standings is called, Then a points table is returned", async () => {
    const text = await callText("standings", { season: 2019 });
    expect(text).toContain("2019 standings");
    expect(text).toMatch(/1\. .+ - \d+ pts \(\d+W, \d+D, \d+L\)/);
  });

  it("Given a Brazilian nationality, When search_players is called, Then only Brazilian players are returned", async () => {
    const text = await callText("search_players", { nationality: "Brazil", limit: 5 });
    const lines = text.split("\n");
    expect(lines).toHaveLength(5);
    expect(lines.every((l) => l.includes("Nationality: Brazil"))).toBe(true);
  });

  it("Given an unknown team, When team_record is called, Then a no-match message is returned", async () => {
    const text = await callText("team_record", { team: "Time Inexistente FC" });
    expect(text).toContain("No matches found in dataset.");
  });

  it("Given no filters, When match_statistics is called, Then aggregate statistics are returned", async () => {
    const text = await callText("match_statistics", { competition: "Brasileirão", limit: 3 });
    expect(text).toContain("Average goals per match:");
    expect(text).toContain("Biggest victories:");
  });

  it("Given an invalid date, When search_matches is called, Then the schema rejects it", async () => {
    const result = await client.callTool({
      name: "search_matches",
      arguments: { start_date: "2023/01/01" },
    });
    expect(result.isError).toBe(true);
  });
});
