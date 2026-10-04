#!/usr/bin/env node
/** MCP server (stdio) exposing Brazilian soccer query tools. */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { getDataset } from "./data.js";
import * as q from "./queries.js";

const competition = z.string().optional().describe("Brasileirão, Copa do Brasil, Libertadores, Serie B or Serie C");
const season = z.number().int().optional().describe("Season year, e.g. 2019");
const venue = z.enum(["home", "away", "any"]).optional();

const text = (fn: () => string) => {
  try {
    return { content: [{ type: "text" as const, text: fn() }] };
  } catch (e) {
    return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
  }
};

export function createServer(): McpServer {
  const server = new McpServer({ name: "brazilian-soccer", version: "1.0.0" });
  const ds = () => getDataset();

  server.registerTool("search_matches", {
    description: "Find matches by team, opponent, venue, competition, season, date range or stage (e.g. 'final'). Sorted newest first.",
    inputSchema: { team: z.string().optional(), opponent: z.string().optional(), venue, competition, season,
      dateFrom: z.string().optional().describe("YYYY-MM-DD"), dateTo: z.string().optional().describe("YYYY-MM-DD"),
      stage: z.string().optional().describe("Stage/round text, e.g. 'final', 'semifinals'"), limit: z.number().int().optional() },
  }, (a) => text(() => q.searchMatches(ds(), a)));

  server.registerTool("head_to_head", {
    description: "Head-to-head record and recent matches between two teams.",
    inputSchema: { teamA: z.string(), teamB: z.string(), competition, limit: z.number().int().optional() },
  }, (a) => text(() => q.headToHead(ds(), a.teamA, a.teamB, a.competition, a.limit)));

  server.registerTool("team_record", {
    description: "Win/draw/loss record and goals for a team, optionally by season, competition and home/away.",
    inputSchema: { team: z.string(), season, competition, venue },
  }, (a) => text(() => q.teamRecord(ds(), a.team, a)));

  server.registerTool("standings", {
    description: "League table for a season calculated from match results (champion and relegation marked).",
    inputSchema: { season: z.number().int(), competition, top: z.number().int().optional() },
  }, (a) => text(() => q.standings(ds(), a.season, a.competition, a.top)));

  server.registerTool("season_champion", { description: "Who won the Brasileirão in a given season.", inputSchema: { season: z.number().int() } },
    (a) => text(() => q.champion(ds(), a.season)));

  server.registerTool("relegated_teams", { description: "Bottom 4 (relegated) teams of a Brasileirão season.", inputSchema: { season: z.number().int() } },
    (a) => text(() => q.relegated(ds(), a.season)));

  server.registerTool("competition_stats", {
    description: "Aggregate statistics: goals per match, home/away win and draw rates.",
    inputSchema: { competition, season },
  }, (a) => text(() => q.competitionStats(ds(), a.competition, a.season)));

  server.registerTool("compare_seasons", {
    description: "Compare aggregate statistics across several seasons.",
    inputSchema: { seasons: z.array(z.number().int()), competition },
  }, (a) => text(() => q.compareSeasons(ds(), a.seasons, a.competition)));

  server.registerTool("biggest_wins", {
    description: "Largest victory margins, optionally filtered by competition, season or team.",
    inputSchema: { competition, season, team: z.string().optional(), limit: z.number().int().optional() },
  }, (a) => text(() => q.biggestWins(ds(), a, a.limit)));

  server.registerTool("rank_teams", {
    description: "Rank teams by win rate, goals for, goals against or points (e.g. best home/away record, most goals in a season).",
    inputSchema: { competition, season, venue, sortBy: z.enum(["winRate", "goalsFor", "goalsAgainst", "points"]).optional(),
      minMatches: z.number().int().optional(), limit: z.number().int().optional() },
  }, (a) => text(() => q.rankTeams(ds(), a)));

  server.registerTool("team_competitions", { description: "Competitions a team has played in the dataset.", inputSchema: { team: z.string() } },
    (a) => text(() => q.teamCompetitions(ds(), a.team)));

  server.registerTool("derbies", {
    description: "Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, ...).",
    inputSchema: { season, competition, limit: z.number().int().optional() },
  }, (a) => text(() => q.derbies(ds(), a)));

  server.registerTool("search_players", {
    description: "Search FIFA player data by name, nationality, club, position (or 'forward'/'midfielder'/'defender'/'goalkeeper'), min rating.",
    inputSchema: { name: z.string().optional(), nationality: z.string().optional(), club: z.string().optional(), position: z.string().optional(),
      minOverall: z.number().int().optional(), maxAge: z.number().int().optional(),
      sortBy: z.enum(["overall", "potential", "age", "name"]).optional(), limit: z.number().int().optional() },
  }, (a) => text(() => q.searchPlayers(ds(), a)));

  server.registerTool("player_details", { description: "Full profile of a player by name.", inputSchema: { name: z.string() } },
    (a) => text(() => q.playerDetails(ds(), a.name)));

  server.registerTool("brazilian_clubs_players", {
    description: "Players (default: Brazilian nationality; pass empty string for all) at clubs that appear in Brazilian match data, grouped by club.",
    inputSchema: { nationality: z.string().optional() },
  }, (a) => text(() => q.brazilianClubsSummary(ds(), a.nationality ?? "Brazil")));

  server.registerTool("team_profile", { description: "Cross-dataset team profile: match record, competitions and FIFA squad.", inputSchema: { team: z.string() } },
    (a) => text(() => q.teamProfile(ds(), a.team)));

  server.registerTool("dataset_info", { description: "Which data files are loaded and row counts.", inputSchema: {} },
    () => text(() => q.datasetInfo(ds())));

  return server;
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith("server.js")) {
  getDataset(); // warm cache before serving
  await createServer().connect(new StdioServerTransport());
}
