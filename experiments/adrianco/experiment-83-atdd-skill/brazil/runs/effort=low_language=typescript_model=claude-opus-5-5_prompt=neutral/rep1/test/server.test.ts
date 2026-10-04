import { test } from "node:test";
import assert from "node:assert/strict";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";

test("MCP server lists and calls tools", async () => {
  const [ct, st] = InMemoryTransport.createLinkedPair();
  const server = createServer();
  await server.connect(st);
  const client = new Client({ name: "test", version: "1.0.0" });
  await client.connect(ct);
  const { tools } = await client.listTools();
  for (const n of ["search_matches", "head_to_head", "team_record", "standings", "search_players", "biggest_wins", "rank_teams"])
    assert.ok(tools.some((t) => t.name === n), n);
  const r = await client.callTool({ name: "standings", arguments: { season: 2019, top: 3 } });
  const text = (r.content as { text: string }[])[0].text;
  assert.match(text, /1\. Flamengo - 90 pts/);
  const bad = await client.callTool({ name: "competition_stats", arguments: { competition: "NFL" } });
  assert.equal(bad.isError, true);
  await client.close();
});
