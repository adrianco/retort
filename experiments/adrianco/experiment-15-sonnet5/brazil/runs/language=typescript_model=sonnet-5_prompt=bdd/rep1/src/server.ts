import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { SoccerDataStore } from "./data/store.js";
import { headToHead, mostRecentMatch, searchMatches } from "./queries/matches.js";
import { competitionsForTeam, getTeamRecord, rankTeamsByRecord } from "./queries/teams.js";
import { brazilianPlayersAtBrazilianClubs, searchPlayers } from "./queries/players.js";
import { bottomOfTable, calculateStandings, seasonsForCompetition } from "./queries/competitions.js";
import { biggestWins, calculateGoalStats } from "./queries/stats.js";
import { formatDate } from "./data/normalize.js";
import type { Competition, Match, Player, StandingsRow, TeamRecord } from "./types.js";

const COMPETITION_ENUM = z.enum(["Brasileirao", "CopaDoBrasil", "Libertadores", "Other"]);

function matchLine(match: Match): string {
  const score = match.homeGoals !== null && match.awayGoals !== null ? `${match.homeGoals}-${match.awayGoals}` : "score unknown";
  const round = match.round ? ` (${match.sourceLabel} Round ${match.round})` : match.stage ? ` (${match.sourceLabel}, ${match.stage})` : ` (${match.sourceLabel})`;
  return `${formatDate(match.date)}: ${match.homeTeam} ${score} ${match.awayTeam}${round}`;
}

function playerLine(player: Player): string {
  return `${player.name} - Overall: ${player.overall ?? "?"}, Position: ${player.position ?? "?"}, Club: ${player.club || "Free agent"}, Nationality: ${player.nationality}`;
}

function recordLine(record: TeamRecord): string {
  const winRatePct = (record.winRate * 100).toFixed(1);
  return `${record.team}: ${record.matches} matches, ${record.wins}W-${record.draws}D-${record.losses}L, GF ${record.goalsFor} GA ${record.goalsAgainst}, win rate ${winRatePct}%`;
}

function standingsLine(row: StandingsRow): string {
  return `${row.position}. ${row.team} - ${row.points} pts (${row.wins}W, ${row.draws}D, ${row.losses}L), GF ${row.goalsFor} GA ${row.goalsAgainst}`;
}

function textResult(text: string) {
  return { content: [{ type: "text" as const, text }] };
}

/** Builds the MCP server and registers every tool over the given data store. */
export function createServer(store: SoccerDataStore): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Find matches by team, opponent, competition, season, and/or date range (ISO dates). Returns the most recent matches first.",
      inputSchema: {
        team: z.string().optional().describe("A team name, e.g. 'Flamengo' or 'Palmeiras-SP'"),
        opponent: z.string().optional().describe("An opposing team name, to find matches between two teams"),
        competition: COMPETITION_ENUM.optional(),
        season: z.number().int().optional(),
        dateFrom: z.string().optional().describe("ISO date, e.g. '2023-01-01'"),
        dateTo: z.string().optional().describe("ISO date, e.g. '2023-12-31'"),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async (args) => {
      const result = searchMatches(store, args);
      if (result.matches.length === 0) {
        return textResult("No matches found for the given criteria.");
      }
      const lines = result.matches.map(matchLine);
      const suffix = result.totalMatches > result.matches.length ? `\n... (${result.totalMatches - result.matches.length} more matches in dataset)` : "";
      return textResult(`${lines.join("\n")}${suffix}\n\nTotal matching matches in dataset: ${result.totalMatches}`);
    },
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head record",
      description: "Finds every match between two teams and tallies the head-to-head win/draw/loss record.",
      inputSchema: {
        teamA: z.string(),
        teamB: z.string(),
        competition: COMPETITION_ENUM.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async (args) => {
      const result = headToHead(store, args.teamA, args.teamB, args);
      if (result.totalMatches === 0) {
        return textResult(`No matches found between ${result.teamA} and ${result.teamB}.`);
      }
      const lines = result.matches.map(matchLine);
      const summary = `Head-to-head in dataset: ${result.teamA} ${result.teamAWins} wins, ${result.teamB} ${result.teamBWins} wins, ${result.draws} draws`;
      return textResult(`${result.teamA} vs ${result.teamB}:\n${lines.join("\n")}\n\n${summary}`);
    },
  );

  server.registerTool(
    "most_recent_match",
    {
      title: "Most recent match between two teams",
      description: "Finds the most recent match between two teams across all competitions and datasets.",
      inputSchema: { teamA: z.string(), teamB: z.string() },
    },
    async (args) => {
      const match = mostRecentMatch(store, args.teamA, args.teamB);
      if (!match) return textResult(`No matches found between ${args.teamA} and ${args.teamB}.`);
      return textResult(matchLine(match));
    },
  );

  server.registerTool(
    "team_record",
    {
      title: "Team win/loss/draw record",
      description:
        "Computes a team's match record (wins, draws, losses, goals for/against, win rate), optionally scoped to home/away, a competition, and/or a season.",
      inputSchema: {
        team: z.string(),
        competition: COMPETITION_ENUM.optional(),
        season: z.number().int().optional(),
        venue: z.enum(["home", "away", "all"]).optional(),
      },
    },
    async (args) => {
      const record = getTeamRecord(store, args.team, args);
      return textResult(recordLine(record));
    },
  );

  server.registerTool(
    "team_competitions",
    {
      title: "Competitions a team has played in",
      description: "Lists the distinct competitions/source datasets a team appears in.",
      inputSchema: { team: z.string() },
    },
    async (args) => {
      const labels = competitionsForTeam(store, args.team);
      if (labels.length === 0) return textResult(`No matches found for ${args.team}.`);
      return textResult(labels.join(", "));
    },
  );

  server.registerTool(
    "rank_teams",
    {
      title: "Rank teams by record",
      description:
        "Ranks all teams by win rate, goals scored, or goal difference within an optional competition/season/venue. Useful for questions like 'best home record' or 'most goals scored'.",
      inputSchema: {
        competition: COMPETITION_ENUM.optional(),
        season: z.number().int().optional(),
        venue: z.enum(["home", "away", "all"]).optional(),
        sortBy: z.enum(["winRate", "goalsFor", "goalDifference"]).optional(),
        minMatches: z.number().int().positive().optional(),
        limit: z.number().int().positive().max(100).optional(),
      },
    },
    async (args) => {
      const records = rankTeamsByRecord(store, { ...args, limit: args.limit ?? 10 });
      if (records.length === 0) return textResult("No teams matched the given criteria.");
      return textResult(records.map((r, i) => `${i + 1}. ${recordLine(r)}`).join("\n"));
    },
  );

  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description: "Searches FIFA player data by name, nationality, club, and/or position.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().optional(),
        sortBy: z.enum(["overall", "potential", "age", "name"]).optional(),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async (args) => {
      const players = searchPlayers(store, { ...args, limit: args.limit ?? 25 });
      if (players.length === 0) return textResult("No players found for the given criteria.");
      return textResult(players.map(playerLine).join("\n"));
    },
  );

  server.registerTool(
    "brazilian_players_by_club",
    {
      title: "Brazilian players grouped by Brazilian club",
      description: "Groups Brazilian-nationality players by the Brazilian (Brasileirão) clubs they play for, with average FIFA overall rating per club.",
      inputSchema: {},
    },
    async () => {
      const summaries = brazilianPlayersAtBrazilianClubs(store);
      if (summaries.length === 0) return textResult("No matching players found.");
      return textResult(summaries.map((s) => `${s.club}: ${s.playerCount} players (avg rating: ${s.averageOverall})`).join("\n"));
    },
  );

  server.registerTool(
    "standings",
    {
      title: "Calculated league standings",
      description: "Calculates a league table (points, W/D/L, goals) for a competition and season from the raw match results.",
      inputSchema: { competition: COMPETITION_ENUM, season: z.number().int() },
    },
    async (args) => {
      const rows = calculateStandings(store, args.competition as Competition, args.season);
      if (rows.length === 0) return textResult(`No match data found for ${args.competition} ${args.season}.`);
      return textResult(`${args.competition} ${args.season} standings (calculated from matches):\n${rows.map(standingsLine).join("\n")}`);
    },
  );

  server.registerTool(
    "relegation_zone",
    {
      title: "Bottom-of-table teams (relegation proxy)",
      description:
        "Returns the bottom N teams of a calculated table as a proxy for relegation. Exact relegation rules varied by year and are not encoded in the match data.",
      inputSchema: { competition: COMPETITION_ENUM, season: z.number().int(), count: z.number().int().positive().optional() },
    },
    async (args) => {
      const rows = bottomOfTable(store, args.competition as Competition, args.season, args.count ?? 4);
      if (rows.length === 0) return textResult(`No match data found for ${args.competition} ${args.season}.`);
      return textResult(rows.map(standingsLine).join("\n"));
    },
  );

  server.registerTool(
    "seasons_for_competition",
    {
      title: "Seasons available for a competition",
      description: "Lists the seasons for which a competition has match data.",
      inputSchema: { competition: COMPETITION_ENUM },
    },
    async (args) => {
      const seasons = seasonsForCompetition(store, args.competition as Competition);
      return textResult(seasons.length ? seasons.join(", ") : `No seasons found for ${args.competition}.`);
    },
  );

  server.registerTool(
    "goal_stats",
    {
      title: "Goal and outcome statistics",
      description: "Computes average goals per match, home win rate, away win rate, and draw rate, optionally scoped to a competition/season.",
      inputSchema: { competition: COMPETITION_ENUM.optional(), season: z.number().int().optional() },
    },
    async (args) => {
      const stats = calculateGoalStats(store, args);
      if (stats.matchesConsidered === 0) return textResult("No matches with known scores found for the given criteria.");
      return textResult(
        `Matches considered: ${stats.matchesConsidered}\nAverage goals per match: ${stats.averageGoalsPerMatch}\nHome win rate: ${(stats.homeWinRate * 100).toFixed(1)}%\nAway win rate: ${(stats.awayWinRate * 100).toFixed(1)}%\nDraw rate: ${(stats.drawRate * 100).toFixed(1)}%`,
      );
    },
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description: "Finds the biggest victories (largest goal difference) in the dataset, optionally scoped to a competition/season.",
      inputSchema: { competition: COMPETITION_ENUM.optional(), season: z.number().int().optional(), limit: z.number().int().positive().max(100).optional() },
    },
    async (args) => {
      const matches = biggestWins(store, args);
      if (matches.length === 0) return textResult("No matches with known scores found for the given criteria.");
      return textResult(matches.map((m, i) => `${i + 1}. ${matchLine(m)}`).join("\n"));
    },
  );

  return server;
}
