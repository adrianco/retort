/**
 * End-to-end tests through the MCP protocol using the SDK client and an
 * in-memory transport pair.
 */
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";
import { TOOLS } from "../src/tools.js";
import { queries } from "./helpers.js";

let client: Client;

beforeAll(async () => {
  const { server } = createServer(queries().ds);
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
});

afterAll(async () => {
  await client.close();
});

const text = (res: Awaited<ReturnType<Client["callTool"]>>) =>
  (res.content as { type: string; text: string }[]).map((c) => c.text).join("\n");

describe("MCP server", () => {
  it("lists all tools with descriptions and JSON schemas", async () => {
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual(TOOLS.map((t) => t.name).sort());
    for (const t of tools) {
      expect(t.description!.length).toBeGreaterThan(20);
      expect(t.inputSchema.type).toBe("object");
    }
    const sm = tools.find((t) => t.name === "search_matches")!;
    expect(Object.keys(sm.inputSchema.properties ?? {})).toEqual(expect.arrayContaining(["team", "opponent", "competition", "season", "date_from", "date_to"]));
  });

  it("answers a head-to-head question", async () => {
    const res = await client.callTool({ name: "head_to_head", arguments: { team_a: "Flamengo", team_b: "Fluminense", limit: 3 } });
    expect(res.isError).toBeFalsy();
    expect(text(res)).toContain("Flamengo vs Fluminense (Fla-Flu derby):");
  });

  it("answers a standings question", async () => {
    const res = await client.callTool({ name: "standings", arguments: { season: 2019, top: 1 } });
    expect(text(res)).toContain("1. Flamengo - 90 pts (28W, 6D, 4L)");
  });

  it("answers a player question", async () => {
    const res = await client.callTool({ name: "search_players", arguments: { nationality: "Brazil", limit: 3 } });
    expect(text(res)).toContain("Neymar Jr");
  });

  it("returns tool errors (not protocol errors) for bad input", async () => {
    const unknownTeam = await client.callTool({ name: "team_record", arguments: { team: "Real Madrid FC Zzz" } });
    expect(unknownTeam.isError).toBe(true);
    expect(text(unknownTeam)).toMatch(/No team matching/);

    const badSeason = await client.callTool({ name: "standings", arguments: { season: 1990 } });
    expect(badSeason.isError).toBe(true);
    expect(text(badSeason)).toMatch(/Seasons available: 2003-2023/);

    const knockout = await client.callTool({ name: "standings", arguments: { season: 2019, competition: "libertadores" } });
    expect(knockout.isError).toBe(true);
    expect(text(knockout)).toMatch(/knockout competition/);
  });

  it("rejects arguments that violate the schema", async () => {
    const res = await client.callTool({ name: "standings", arguments: { season: "two thousand" } }).catch((e: Error) => e);
    if (res instanceof Error) expect(res.message).toMatch(/season|Invalid/i);
    else expect(res.isError).toBe(true);
  });

  it("every tool runs successfully with representative arguments", async () => {
    const examples: Record<string, Record<string, unknown>> = {
      search_matches: { team: "Santos", season: 2015, limit: 3 },
      head_to_head: { team_a: "Grêmio", team_b: "Internacional" },
      team_record: { team: "Cruzeiro", season: 2014 },
      team_profile: { team: "Bahia" },
      standings: { season: 2015, competition: "serie-b", top: 4 },
      cup_bracket: { competition: "copa-do-brasil", season: 2019 },
      cup_finals: { competition: "libertadores" },
      match_statistics: { competition: "libertadores", season: 2019 },
      biggest_wins: { team: "Flamengo", limit: 3 },
      team_rankings: { metric: "points", competition: "serie-a", season: 2015, limit: 3 },
      compare_seasons: { seasons: [2016, 2017], competition: "serie-a" },
      derbies: { team: "Corinthians", season: 2019 },
      search_players: { club: "Santos", position: "GK" },
      get_player: { name: "Casemiro" },
      club_player_summary: { group_by: "nationality", limit: 5 },
      find_team: { query: "Botafogo" },
      dataset_info: {},
    };
    for (const tool of TOOLS) {
      const args = examples[tool.name];
      expect(args, `example for ${tool.name}`).toBeDefined();
      const res = await client.callTool({ name: tool.name, arguments: args });
      expect(res.isError, `${tool.name}: ${text(res)}`).toBeFalsy();
      expect(text(res).length).toBeGreaterThan(20);
    }
  });
});
