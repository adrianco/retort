/**
 * End-to-end MCP test: links a real MCP Client to our Server over an in-memory
 * transport and drives it exactly as an LLM client would — listing tools and
 * calling them — proving the protocol wiring works, not just the inner logic.
 */
import { describe, expect, it, beforeAll, afterAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/server.js";
import { store } from "./helpers.js";

describe("MCP server over in-memory transport", () => {
  let client: Client;

  beforeAll(async () => {
    const server = createServer(store());
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    client = new Client({ name: "test-client", version: "1.0.0" }, { capabilities: {} });
    await Promise.all([
      server.connect(serverTransport),
      client.connect(clientTransport),
    ]);
  });

  afterAll(async () => {
    await client.close();
  });

  it("lists all tools via the protocol", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name);
    expect(names).toContain("find_matches");
    expect(names).toContain("search_players");
    expect(names).toContain("league_standings");
    expect(tools.every((t) => t.inputSchema)).toBe(true);
  });

  it("calls league_standings and returns formatted text content", async () => {
    const res = await client.callTool({ name: "league_standings", arguments: { season: 2019, limit: 3 } });
    const content = res.content as Array<{ type: string; text: string }>;
    expect(content[0].type).toBe("text");
    expect(content[0].text).toMatch(/Flamengo.*Champion/);
  });

  it("calls search_players via the protocol", async () => {
    const res = await client.callTool({ name: "search_players", arguments: { nationality: "Brazil", limit: 2 } });
    const content = res.content as Array<{ type: string; text: string }>;
    expect(content[0].text).toMatch(/Neymar/);
  });

  it("reports tool errors as isError content rather than throwing", async () => {
    const res = await client.callTool({ name: "find_matches", arguments: { team: "Flamengo", season: 2019, limit: 2 } });
    const content = res.content as Array<{ type: string; text: string }>;
    expect(content[0].text).toMatch(/Flamengo/);
  });
});
