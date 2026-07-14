// Feature: MCP server tool registration
//   The MCP server exposes a set of tools. This test verifies the server builds
//   and that the expected tools are advertised via list-tools.
import { describe, it, expect, beforeAll } from "vitest";
import { buildServer } from "../src/server.js";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";

const EXPECTED_TOOLS = [
  "find_matches",
  "team_stats",
  "head_to_head",
  "last_match_between",
  "team_competitions",
  "team_recent_matches",
  "list_teams",
  "find_players",
  "top_brazilian_players",
  "standings",
  "champion",
  "relegated",
  "list_competitions",
  "list_seasons",
  "aggregate_stats",
  "biggest_wins",
  "top_scoring_teams",
  "best_record",
];

let client: Client;

beforeAll(async () => {
  const server = buildServer();
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
});

describe("Feature: MCP server", () => {
  it("Scenario: lists all expected tools", async () => {
    const res = await client.listTools();
    const names = res.tools.map((t) => t.name).sort();
    for (const t of EXPECTED_TOOLS) {
      expect(names).toContain(t);
    }
  });

  it("Scenario: 'find_matches' returns a text result", async () => {
    const res = await client.callTool({
      name: "find_matches",
      arguments: { team: "Flamengo", opponent: "Fluminense", limit: 3 },
    });
    expect(res.isError).toBeFalsy();
    const content = res.content as Array<{ type: string; text?: string }>;
    expect(content[0].type).toBe("text");
    expect(content[0].text).toMatch(/match/i);
  });

  it("Scenario: 'standings' returns a numbered table", async () => {
    const res = await client.callTool({
      name: "standings",
      arguments: { competition: "Brasileirão", season: 2019, limit: 3 },
    });
    const content = res.content as Array<{ type: string; text?: string }>;
    expect(content[0].text).toMatch(/1\./);
  });
});
