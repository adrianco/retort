import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { buildService } from "../src/index.js";
import { createSoccerMcpServer } from "../src/mcp-server.js";

describe("MCP protocol surface", () => {
  const client = new Client({ name: "test-client", version: "1.0.0" });
  const server = createSoccerMcpServer(buildService());

  beforeAll(async () => {
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  });

  afterAll(async () => {
    await Promise.all([client.close(), server.close()]);
  });

  it("advertises the complete tool set", async () => {
    const response = await client.listTools();
    expect(response.tools.map((tool) => tool.name)).toEqual(expect.arrayContaining([
      "ask_soccer", "search_matches", "get_head_to_head", "get_team_statistics",
      "get_team_profile", "search_players", "get_standings",
      "get_competition_statistics", "get_derbies", "get_dataset_summary",
    ]));
  });

  it("returns formatted and structured results through MCP", async () => {
    const response = await client.callTool({ name: "get_standings", arguments: { season: 2019, competition: "Brasileirão" } });
    expect(response.isError).not.toBe(true);
    expect(response.content).toEqual(expect.arrayContaining([expect.objectContaining({ type: "text" })]));
    expect(response.structuredContent).toMatchObject({ kind: "standings" });
  });

  it("returns tool errors without crashing the server", async () => {
    const response = await client.callTool({ name: "get_team_statistics", arguments: { team: "Definitely Not A Team" } });
    expect(response.isError).toBe(true);
  });
});
