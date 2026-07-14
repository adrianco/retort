import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { findMatches } from "./tools/matches.js";
import { getTeamStats } from "./tools/teams.js";
import { findPlayers } from "./tools/players.js";
import { getHeadToHead } from "./tools/headToHead.js";
import { getStandings } from "./tools/standings.js";

export async function createServer(): Promise<Server> {
  const server = new Server(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    { capabilities: { tools: {} } }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [
      {
        name: "find_matches",
        description: "Find soccer matches from Brazilian competitions",
        inputSchema: {
          type: "object",
          properties: {
            team: { type: "string", description: "Team name to search for" },
            competition: { type: "string", enum: ["brasileirao", "copa_do_brasil", "libertadores", "br_football", "historico"], description: "Competition to search in" },
            season: { type: "number", description: "Season year" },
            limit: { type: "number", description: "Max results (default 20)" },
          },
        },
      },
      {
        name: "get_team_stats",
        description: "Get statistics for a team in a competition",
        inputSchema: {
          type: "object",
          properties: {
            team: { type: "string", description: "Team name" },
            competition: { type: "string", description: "Competition name" },
            season: { type: "number", description: "Season year" },
          },
          required: ["team"],
        },
      },
      {
        name: "find_players",
        description: "Find players from FIFA dataset",
        inputSchema: {
          type: "object",
          properties: {
            name: { type: "string", description: "Player name (partial match)" },
            nationality: { type: "string", description: "Player nationality" },
            club: { type: "string", description: "Club name (partial match)" },
            minRating: { type: "number", description: "Minimum Overall rating" },
            position: { type: "string", description: "Player position" },
            limit: { type: "number", description: "Max results (default 20)" },
          },
        },
      },
      {
        name: "get_head_to_head",
        description: "Get head-to-head record between two teams",
        inputSchema: {
          type: "object",
          properties: {
            team1: { type: "string", description: "First team name" },
            team2: { type: "string", description: "Second team name" },
            competition: { type: "string", description: "Competition to filter by" },
            season: { type: "number", description: "Season to filter by" },
          },
          required: ["team1", "team2"],
        },
      },
      {
        name: "get_standings",
        description: "Get standings table for a competition and season",
        inputSchema: {
          type: "object",
          properties: {
            competition: { type: "string", description: "Competition name (brasileirao or historico)" },
            season: { type: "number", description: "Season year" },
          },
          required: ["competition", "season"],
        },
      },
    ],
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
      let result: any;

      switch (name) {
        case "find_matches":
          result = findMatches(args as any);
          break;
        case "get_team_stats":
          result = getTeamStats(args as any);
          break;
        case "find_players":
          result = findPlayers(args as any);
          break;
        case "get_head_to_head":
          result = getHeadToHead(args as any);
          break;
        case "get_standings":
          result = getStandings(args as any);
          break;
        default:
          throw new Error(`Unknown tool: ${name}`);
      }

      return {
        content: [{ type: "text", text: JSON.stringify(result) }],
      };
    } catch (error) {
      return {
        content: [{ type: "text", text: JSON.stringify({ error: String(error) }) }],
        isError: true,
      };
    }
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  return server;
}
