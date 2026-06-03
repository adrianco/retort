/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Test:    tests/server.test.ts
 * Purpose: Integration tests that drive the MCP server through an in-memory
 *          client/transport pair, exercising the real tool-call path
 *          (validation + dispatch + formatting) rather than the query layer.
 * ============================================================================
 */

import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";

let client: Client;

beforeAll(async () => {
  const server = createServer();
  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();
  client = new Client({ name: "test-client", version: "1.0.0" });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
});

async function call(name: string, args: Record<string, unknown> = {}) {
  const res = (await client.callTool({ name, arguments: args })) as {
    content: { type: string; text: string }[];
    structuredContent?: Record<string, unknown>;
  };
  return res;
}

describe("Feature: MCP server tool surface", () => {
  it("Given the server When listing tools Then all categories are present", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name);
    expect(names).toEqual(
      expect.arrayContaining([
        "search_matches",
        "head_to_head",
        "team_record",
        "search_players",
        "standings",
        "competition_summary",
        "match_statistics",
        "list_competitions",
      ]),
    );
    expect(tools.length).toBeGreaterThanOrEqual(12);
  });

  it("When calling standings Then the text crowns Flamengo 2019", async () => {
    const res = await call("standings", {
      competition: "Brasileirão Série A",
      season: 2019,
      limit: 5,
    });
    expect(res.content[0].text).toContain("Flamengo");
    expect(res.content[0].text).toContain("Champion");
    const table = res.structuredContent?.table as unknown[];
    expect(Array.isArray(table)).toBe(true);
  });

  it("When calling search_players for Brazilians Then Neymar tops the list", async () => {
    const res = await call("search_players", {
      nationality: "Brazil",
      limit: 3,
    });
    expect(res.content[0].text).toContain("Neymar Jr");
  });

  it("When calling head_to_head Then a record summary is returned", async () => {
    const res = await call("head_to_head", {
      team1: "Flamengo",
      team2: "Fluminense",
    });
    expect(res.content[0].text.toLowerCase()).toContain("head-to-head");
    expect(res.structuredContent?.totalMatches).toBeGreaterThan(0);
  });

  it("When calling dataset_info Then it reports six source files", async () => {
    const res = await call("dataset_info");
    expect(res.structuredContent?.files).toHaveLength(6);
  });
});
