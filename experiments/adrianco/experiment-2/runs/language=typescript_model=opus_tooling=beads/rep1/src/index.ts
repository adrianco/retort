#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { getData } from "./data.js";
import {
  findMatches,
  teamStats,
  headToHead,
  standings,
  findPlayers,
  overallStats,
  biggestWins,
} from "./queries.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DATA_DIR = process.env.SOCCER_DATA_DIR || join(__dirname, "..", "data", "kaggle");

const tools = [
  {
    name: "find_matches",
    description:
      "Find soccer matches by team, competition, season, or date range. Returns a list of matches sorted by date desc.",
    inputSchema: {
      type: "object",
      properties: {
        team: { type: "string", description: "Team name (home or away)" },
        team2: { type: "string", description: "Second team for head-to-head matches" },
        homeTeam: { type: "string" },
        awayTeam: { type: "string" },
        competition: { type: "string", description: "E.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'" },
        season: { type: "number" },
        dateFrom: { type: "string", description: "ISO date YYYY-MM-DD" },
        dateTo: { type: "string" },
        limit: { type: "number", default: 20 },
      },
    },
  },
  {
    name: "team_stats",
    description: "Compute team stats (wins/draws/losses, goals) optionally filtered by season/competition.",
    inputSchema: {
      type: "object",
      required: ["team"],
      properties: {
        team: { type: "string" },
        season: { type: "number" },
        competition: { type: "string" },
        homeOnly: { type: "boolean" },
        awayOnly: { type: "boolean" },
      },
    },
  },
  {
    name: "head_to_head",
    description: "Head-to-head record between two teams across all data.",
    inputSchema: {
      type: "object",
      required: ["team1", "team2"],
      properties: {
        team1: { type: "string" },
        team2: { type: "string" },
        limit: { type: "number", default: 10 },
      },
    },
  },
  {
    name: "standings",
    description: "Compute league standings table for a season (default: Brasileirão).",
    inputSchema: {
      type: "object",
      required: ["season"],
      properties: {
        season: { type: "number" },
        competition: { type: "string", default: "Brasileirão" },
      },
    },
  },
  {
    name: "find_players",
    description: "Search FIFA player database by name, nationality, club, position, or rating.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string" },
        nationality: { type: "string" },
        club: { type: "string" },
        position: { type: "string" },
        minOverall: { type: "number" },
        limit: { type: "number", default: 20 },
      },
    },
  },
  {
    name: "overall_stats",
    description: "Aggregate stats (avg goals/match, home win rate) optionally filtered by competition/season.",
    inputSchema: {
      type: "object",
      properties: {
        competition: { type: "string" },
        season: { type: "number" },
      },
    },
  },
  {
    name: "biggest_wins",
    description: "Return matches with the largest goal differences.",
    inputSchema: {
      type: "object",
      properties: {
        competition: { type: "string" },
        limit: { type: "number", default: 10 },
      },
    },
  },
];

async function main() {
  const data = getData(DATA_DIR);

  const server = new Server(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    { capabilities: { tools: {} } }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const { name, arguments: args } = req.params;
    const a = (args ?? {}) as Record<string, unknown>;
    try {
      let result: unknown;
      switch (name) {
        case "find_matches":
          result = findMatches(data, a as any);
          break;
        case "team_stats":
          result = teamStats(data, a.team as string, a as any);
          break;
        case "head_to_head":
          result = headToHead(data, a.team1 as string, a.team2 as string, a.limit as number | undefined);
          break;
        case "standings":
          result = standings(data, a.season as number, (a.competition as string) || "Brasileirão");
          break;
        case "find_players":
          result = findPlayers(data, a as any);
          break;
        case "overall_stats":
          result = overallStats(data, a as any);
          break;
        case "biggest_wins":
          result = biggestWins(data, a as any);
          break;
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } catch (err) {
      return {
        isError: true,
        content: [{ type: "text", text: `Error: ${(err as Error).message}` }],
      };
    }
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`Brazilian Soccer MCP server running. Matches: ${data.matches.length}, Players: ${data.players.length}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
