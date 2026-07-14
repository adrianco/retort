#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { Dataset } from "./data.js";
import {
  findMatches,
  teamStats,
  headToHead,
  standings,
  findPlayers,
  globalStats,
  biggestWins,
} from "./queries.js";

const dataset = Dataset.load();

const server = new Server(
  { name: "brazilian-soccer-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } },
);

const tools = [
  {
    name: "find_matches",
    description: "Search matches by team(s), competition, season, or date range.",
    inputSchema: {
      type: "object",
      properties: {
        team: { type: "string" },
        teamA: { type: "string" },
        teamB: { type: "string" },
        competition: { type: "string" },
        season: { type: "number" },
        dateFrom: { type: "string" },
        dateTo: { type: "string" },
        homeOnly: { type: "boolean" },
        awayOnly: { type: "boolean" },
        limit: { type: "number" },
      },
    },
  },
  {
    name: "team_stats",
    description: "Aggregate win/loss/draw and goals for a team, optionally filtered by season/competition.",
    inputSchema: {
      type: "object",
      properties: {
        team: { type: "string" },
        season: { type: "number" },
        competition: { type: "string" },
        homeOnly: { type: "boolean" },
        awayOnly: { type: "boolean" },
      },
      required: ["team"],
    },
  },
  {
    name: "head_to_head",
    description: "Head-to-head record between two teams across all competitions.",
    inputSchema: {
      type: "object",
      properties: { teamA: { type: "string" }, teamB: { type: "string" } },
      required: ["teamA", "teamB"],
    },
  },
  {
    name: "standings",
    description: "Compute standings (3-1-0 points) for a competition/season from match results.",
    inputSchema: {
      type: "object",
      properties: {
        season: { type: "number" },
        competition: { type: "string", default: "Brasileirão" },
      },
      required: ["season"],
    },
  },
  {
    name: "find_players",
    description: "Search FIFA players by name/nationality/club/position with filters.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string" },
        nationality: { type: "string" },
        club: { type: "string" },
        position: { type: "string" },
        minOverall: { type: "number" },
        limit: { type: "number" },
      },
    },
  },
  {
    name: "global_stats",
    description: "Aggregate match statistics (avg goals, home/away win rates) with optional filters.",
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
    description: "Return matches with the largest goal differential.",
    inputSchema: {
      type: "object",
      properties: {
        competition: { type: "string" },
        limit: { type: "number", default: 10 },
      },
    },
  },
];

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args = {} } = req.params;
  const a = args as Record<string, any>;
  let result: unknown;
  switch (name) {
    case "find_matches":
      result = findMatches(dataset, a);
      break;
    case "team_stats":
      result = teamStats(dataset, a.team, a);
      break;
    case "head_to_head":
      result = headToHead(dataset, a.teamA, a.teamB);
      break;
    case "standings":
      result = standings(dataset, a.season, a.competition ?? "Brasileirão");
      break;
    case "find_players":
      result = findPlayers(dataset, a);
      break;
    case "global_stats":
      result = globalStats(dataset, a);
      break;
    case "biggest_wins":
      result = biggestWins(dataset, a);
      break;
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
  return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
});

const transport = new StdioServerTransport();
await server.connect(transport);
