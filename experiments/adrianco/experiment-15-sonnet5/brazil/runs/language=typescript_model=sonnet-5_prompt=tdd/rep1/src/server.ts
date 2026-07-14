import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  searchMatchesTool,
  teamRecordTool,
  compareTeamsTool,
  searchPlayersTool,
  competitionStandingsTool,
  datasetStatisticsTool,
  listTeamCompetitionsTool,
  playerClubContextTool,
  type AppData,
} from "./tools.js";

function textResult(text: string) {
  return { content: [{ type: "text" as const, text }] };
}

export function createServer(data: AppData): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.registerTool(
    "search_matches",
    {
      description: "Find matches played by a team, optionally filtered by opponent, competition, season, or date range.",
      inputSchema: {
        team: z.string().describe("Team name to search for"),
        opponent: z.string().optional().describe("Restrict to matches against this opponent"),
        competition: z.string().optional().describe("Restrict to this competition (e.g. Brasileirão, Copa do Brasil, Copa Libertadores)"),
        season: z.number().optional().describe("Restrict to this season/year"),
        startDate: z.string().optional().describe("Restrict to matches on/after this ISO date (YYYY-MM-DD)"),
        endDate: z.string().optional().describe("Restrict to matches on/before this ISO date (YYYY-MM-DD)"),
        limit: z.number().optional().describe("Maximum number of matches to return"),
      },
    },
    async (args) => textResult(searchMatchesTool(data, args)),
  );

  server.registerTool(
    "team_record",
    {
      description: "Get a team's win/draw/loss record and goal tally, optionally filtered by competition, season, and home/away venue.",
      inputSchema: {
        team: z.string().describe("Team name"),
        competition: z.string().optional().describe("Restrict to this competition"),
        season: z.number().optional().describe("Restrict to this season/year"),
        venue: z.enum(["home", "away", "all"]).optional().describe("Restrict to home or away matches only"),
      },
    },
    async (args) => textResult(teamRecordTool(data, args)),
  );

  server.registerTool(
    "compare_teams",
    {
      description: "Compare two teams head-to-head plus their overall records, optionally filtered by competition and season.",
      inputSchema: {
        teamA: z.string().describe("First team name"),
        teamB: z.string().describe("Second team name"),
        competition: z.string().optional().describe("Restrict to this competition"),
        season: z.number().optional().describe("Restrict to this season/year"),
      },
    },
    async (args) => textResult(compareTeamsTool(data, args)),
  );

  server.registerTool(
    "search_players",
    {
      description: "Search FIFA player data by name, nationality, club, and/or position, ranked by overall rating.",
      inputSchema: {
        name: z.string().optional().describe("Player name (partial match)"),
        nationality: z.string().optional().describe("Player nationality (e.g. Brazil)"),
        club: z.string().optional().describe("Club name (partial match)"),
        position: z.string().optional().describe("Playing position (e.g. GK, CDM, LW)"),
        limit: z.number().optional().describe("Maximum number of players to return"),
      },
    },
    async (args) => textResult(searchPlayersTool(data, args)),
  );

  server.registerTool(
    "competition_standings",
    {
      description: "Calculate league standings for a competition and season from match results.",
      inputSchema: {
        competition: z.string().describe("Competition name (e.g. Brasileirão, Copa do Brasil, Copa Libertadores)"),
        season: z.number().describe("Season/year"),
      },
    },
    async (args) => textResult(competitionStandingsTool(data, args)),
  );

  server.registerTool(
    "dataset_statistics",
    {
      description: "Compute aggregate statistics (average goals per match, home/away win rates, biggest wins), optionally scoped to a competition and/or season.",
      inputSchema: {
        competition: z.string().optional().describe("Restrict to this competition"),
        season: z.number().optional().describe("Restrict to this season/year"),
      },
    },
    async (args) => textResult(datasetStatisticsTool(data, args)),
  );

  server.registerTool(
    "player_club_context",
    {
      description: "Cross-file lookup: find a player by name (FIFA data) and show their club's match record (match data) together.",
      inputSchema: {
        name: z.string().describe("Player name (partial match)"),
      },
    },
    async (args) => textResult(playerClubContextTool(data, args)),
  );

  server.registerTool(
    "list_team_competitions",
    {
      description: "List the distinct competitions a team has played in across the dataset.",
      inputSchema: {
        team: z.string().describe("Team name"),
      },
    },
    async (args) => textResult(listTeamCompetitionsTool(data, args)),
  );

  return server;
}
