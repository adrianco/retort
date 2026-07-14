import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { Dataset } from "./types.js";
import { findMatches, headToHead } from "./queries/matches.js";
import { teamRecord, listTeams, topScoringTeams, computeStandings } from "./queries/teams.js";
import { findPlayers, brazilianPlayersByClub, summarizePlayer } from "./queries/players.js";
import { matchStats, biggestWins, compareSeasons } from "./queries/stats.js";
import { seasonSummary, listSeasons, listCompetitions } from "./queries/competitions.js";

function asText(value: unknown) {
  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(value, null, 2),
      },
    ],
  };
}

export function buildServer(dataset: Dataset): McpServer {
  const server = new McpServer(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    {
      capabilities: { tools: {} },
      instructions:
        "Knowledge graph over Brazilian soccer. Tools cover match lookup, team records, player search, competition standings, and statistical analysis across Brasileirão, Copa do Brasil, Libertadores, and the FIFA player database.",
    },
  );

  server.registerTool(
    "list_competitions",
    {
      title: "List Competitions",
      description: "List the competitions covered by the dataset along with match counts and seasons.",
      inputSchema: {},
    },
    async () => asText(listCompetitions(dataset)),
  );

  server.registerTool(
    "list_seasons",
    {
      title: "List Seasons",
      description: "List the seasons available for a given competition (or across all data).",
      inputSchema: {
        competition: z.string().optional().describe("Competition key or label (e.g. 'Brasileirao', 'Libertadores')."),
      },
    },
    async (args) => asText(listSeasons(dataset, args.competition)),
  );

  server.registerTool(
    "find_matches",
    {
      title: "Find Matches",
      description: "Search matches by team, opponent, season, date range, competition, and round/stage.",
      inputSchema: {
        team: z.string().optional().describe("Team name (matches home or away)."),
        team2: z.string().optional().describe("Optional second team — restrict to matches between team and team2."),
        homeTeam: z.string().optional(),
        awayTeam: z.string().optional(),
        season: z.number().int().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
        dateFrom: z.string().optional().describe("ISO date yyyy-mm-dd."),
        dateTo: z.string().optional().describe("ISO date yyyy-mm-dd."),
        competition: z.string().optional(),
        stage: z.string().optional(),
        round: z.string().optional(),
        limit: z.number().int().min(1).max(500).optional(),
      },
    },
    async (args) => {
      const matches = findMatches(dataset, { ...args, limit: args.limit ?? 50 });
      return asText({ count: matches.length, matches });
    },
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-Head",
      description: "Aggregate head-to-head record between two teams (wins, draws, goals) with the most recent matches.",
      inputSchema: {
        teamA: z.string(),
        teamB: z.string(),
        competition: z.string().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
      },
    },
    async (args) => asText(headToHead(dataset, args.teamA, args.teamB, args)),
  );

  server.registerTool(
    "team_record",
    {
      title: "Team Record",
      description: "Get a team's overall, home, and away record, optionally scoped by competition or season.",
      inputSchema: {
        team: z.string(),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
      },
    },
    async (args) => asText(teamRecord(dataset, args.team, args)),
  );

  server.registerTool(
    "list_teams",
    {
      title: "List Teams",
      description: "List teams that appear in the match data, optionally filtered by competition and season.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => asText(listTeams(dataset, args)),
  );

  server.registerTool(
    "top_scoring_teams",
    {
      title: "Top Scoring Teams",
      description: "Return the highest goal-scoring teams within a competition/season scope.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().min(1).max(100).optional(),
      },
    },
    async (args) => asText(topScoringTeams(dataset, args)),
  );

  server.registerTool(
    "standings",
    {
      title: "Standings",
      description: "Compute standings (3 pts/win, 1/draw) from match results for a competition/season.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => asText(computeStandings(dataset, args)),
  );

  server.registerTool(
    "season_summary",
    {
      title: "Season Summary",
      description: "Champion, top three, bottom three, and team count for a season.",
      inputSchema: {
        season: z.number().int(),
        competition: z.string().optional().describe("Defaults to Brasileirao."),
      },
    },
    async (args) => asText(seasonSummary(dataset, args.season, args.competition ?? "Brasileirao")),
  );

  server.registerTool(
    "find_players",
    {
      title: "Find Players",
      description: "Search the FIFA player database by name, nationality, club, position, rating, or age.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().optional(),
        maxOverall: z.number().int().optional(),
        minAge: z.number().int().optional(),
        maxAge: z.number().int().optional(),
        limit: z.number().int().min(1).max(500).optional(),
        sortBy: z.enum(["overall", "potential", "age", "name"]).optional(),
        sortDir: z.enum(["asc", "desc"]).optional(),
      },
    },
    async (args) => {
      const players = findPlayers(dataset, { ...args, limit: args.limit ?? 25 });
      return asText({ count: players.length, players: players.map(summarizePlayer) });
    },
  );

  server.registerTool(
    "brazilian_players_by_club",
    {
      title: "Brazilian Players By Club",
      description: "Breakdown of Brazilian players per club (counts, average overall, top player).",
      inputSchema: {},
    },
    async () => asText(brazilianPlayersByClub(dataset)),
  );

  server.registerTool(
    "match_stats",
    {
      title: "Match Stats",
      description: "Average goals per match, home/away/draw rates for a competition/season/team scope.",
      inputSchema: {
        team: z.string().optional(),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
      },
    },
    async (args) => asText(matchStats(dataset, args)),
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest Wins",
      description: "Largest goal-margin victories in the dataset, scoped by competition/season/team.",
      inputSchema: {
        team: z.string().optional(),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().min(1).max(100).optional(),
      },
    },
    async (args) => asText(biggestWins(dataset, args)),
  );

  server.registerTool(
    "compare_seasons",
    {
      title: "Compare Seasons",
      description: "Compare aggregate match statistics across a list of seasons.",
      inputSchema: {
        seasons: z.array(z.number().int()).min(2),
        competition: z.string().optional(),
      },
    },
    async (args) => asText(compareSeasons(dataset, args.seasons, { competition: args.competition })),
  );

  return server;
}
