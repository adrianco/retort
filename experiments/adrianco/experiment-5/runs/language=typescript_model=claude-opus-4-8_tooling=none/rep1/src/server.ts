/**
 * Context
 * -------
 * Defines the MCP server and registers one tool per capability area from the
 * spec (matches, teams, players, competitions, statistics). Each tool validates
 * its input with zod, calls the pure query functions in `queries.ts`, and
 * returns BOTH a human-readable text block (via `format.ts`) and a
 * `structuredContent` JSON payload so programmatic clients get typed data.
 *
 * The transport (stdio) is wired up separately in `index.ts`, keeping this
 * module importable and testable without spawning a process.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { DataStore, getDataStore } from "./dataStore.js";
import {
  biggestWins,
  competitionStats,
  findMatches,
  findPlayers,
  headToHead,
  standings,
  teamCompetitions,
  teamStats,
  topScoringTeams,
} from "./queries.js";
import {
  formatCompetitionStats,
  formatHeadToHead,
  formatMatchList,
  formatPlayerDetail,
  formatPlayerList,
  formatStandings,
  formatTeamStats,
} from "./format.js";

/** Helper: a tool result with text + structured JSON content. */
function result(text: string, structured: unknown) {
  return {
    content: [{ type: "text" as const, text }],
    structuredContent: { data: structured } as Record<string, unknown>,
  };
}

export function createServer(store: DataStore = getDataStore()): McpServer {
  const server = new McpServer(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    {
      instructions:
        "Knowledge interface over Brazilian soccer datasets (Brasileirão, Copa do " +
        "Brasil, Copa Libertadores matches and FIFA players). Use search_matches / " +
        "head_to_head / team_stats / search_players / get_player / competition_standings " +
        "/ competition_stats / biggest_wins / top_scoring_teams / team_competitions.",
    },
  );

  // 1. Match queries -------------------------------------------------------
  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Find matches by team, opponent, competition, season and/or date range. " +
        "Use `team` + `opponent` for head-to-head fixtures. Results are sorted most-recent first.",
      inputSchema: {
        team: z.string().optional().describe("Team name (matches home or away)"),
        opponent: z.string().optional().describe("Second team, for matches between two clubs"),
        homeTeam: z.string().optional().describe("Restrict to this team playing at home"),
        awayTeam: z.string().optional().describe("Restrict to this team playing away"),
        competition: z
          .string()
          .optional()
          .describe("Brasileirão / Serie A / Serie B / Serie C / Copa do Brasil / Libertadores"),
        season: z.number().int().optional().describe("Season year, e.g. 2019"),
        startDate: z.string().optional().describe("ISO date lower bound (YYYY-MM-DD)"),
        endDate: z.string().optional().describe("ISO date upper bound (YYYY-MM-DD)"),
        limit: z.number().int().positive().max(500).optional().describe("Max matches to return"),
      },
    },
    async (args) => {
      const matches = findMatches(store, args);
      const text = formatMatchList(matches, {
        max: args.limit ?? 25,
        title: `Found ${matches.length} match(es).`,
      });
      return result(text, matches);
    },
  );

  // Head-to-head -----------------------------------------------------------
  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head record",
      description: "Win/draw/loss record and match list between two teams across all competitions.",
      inputSchema: {
        teamA: z.string().describe("First team"),
        teamB: z.string().describe("Second team"),
      },
    },
    async ({ teamA, teamB }) => {
      const h = headToHead(store, teamA, teamB);
      return result(formatHeadToHead(h), h);
    },
  );

  // 2. Team queries --------------------------------------------------------
  server.registerTool(
    "team_stats",
    {
      title: "Team statistics",
      description:
        "Win/draw/loss record, goals for/against, win rate and home/away split for a team, " +
        "optionally scoped to a competition and/or season.",
      inputSchema: {
        team: z.string().describe("Team name"),
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async ({ team, competition, season }) => {
      const s = teamStats(store, team, { competition, season });
      return result(formatTeamStats(s), s);
    },
  );

  server.registerTool(
    "team_competitions",
    {
      title: "Team competitions",
      description: "List the competitions a team appears in within the dataset, with match counts.",
      inputSchema: { team: z.string().describe("Team name") },
    },
    async ({ team }) => {
      const comps = teamCompetitions(store, team);
      const text =
        comps.length === 0
          ? `No matches found for ${team}.`
          : `Competitions for ${team}:\n` +
            comps.map((c) => `- ${c.competition}: ${c.matches} matches`).join("\n");
      return result(text, comps);
    },
  );

  // 3. Player queries ------------------------------------------------------
  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search FIFA players by name, nationality (e.g. Brazil), club, and/or position. " +
        "Sorted by Overall rating descending.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional().describe('e.g. "Brazil"'),
        club: z.string().optional().describe('e.g. "Flamengo"'),
        position: z.string().optional().describe('e.g. "ST", "GK", "CB"'),
        minOverall: z.number().int().optional(),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async (args) => {
      const players = findPlayers(store, args);
      const text = formatPlayerList(players, {
        max: args.limit ?? 25,
        title: `Found ${players.length} player(s).`,
      });
      return result(text, players);
    },
  );

  server.registerTool(
    "get_player",
    {
      title: "Get player",
      description: "Look up the best-matching single player by name and return full attributes.",
      inputSchema: { name: z.string().describe("Player name to search for") },
    },
    async ({ name }) => {
      const players = findPlayers(store, { name, limit: 1 });
      if (players.length === 0) return result(`No player found matching "${name}".`, null);
      return result(formatPlayerDetail(players[0]), players[0]);
    },
  );

  // 4. Competition queries -------------------------------------------------
  server.registerTool(
    "competition_standings",
    {
      title: "Competition standings",
      description:
        "Compute the final league table for a competition and season from match results " +
        "(3pts win / 1pt draw). Best for Brasileirão Série A/B/C seasons.",
      inputSchema: {
        competition: z.string().describe("Competition name, e.g. Brasileirão / Serie B"),
        season: z.number().int().describe("Season year, e.g. 2019"),
        limit: z.number().int().positive().optional().describe("Top N rows"),
      },
    },
    async ({ competition, season, limit }) => {
      const rows = standings(store, competition, season);
      const text = formatStandings(rows, competition, season, { max: limit });
      return result(text, rows);
    },
  );

  server.registerTool(
    "competition_stats",
    {
      title: "Competition statistics",
      description:
        "Aggregate stats for a competition/season (or everything): match count, total & " +
        "average goals, home/away win split, home win rate.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async ({ competition, season }) => {
      const s = competitionStats(store, { competition, season });
      return result(formatCompetitionStats(s), s);
    },
  );

  // 5. Statistical analysis ------------------------------------------------
  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description: "Largest goal-margin victories, optionally scoped to a competition/season.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(100).optional(),
      },
    },
    async ({ competition, season, limit }) => {
      const wins = biggestWins(store, { competition, season, limit });
      const text =
        `Biggest victories${competition ? ` (${competition})` : ""}:\n` +
        wins
          .map(
            (w, i) =>
              `${i + 1}. ${w.match.date ?? "?"}: ${w.match.homeTeam} ${w.match.homeGoal}-${w.match.awayGoal} ${w.match.awayTeam} (${w.match.competition}, margin ${w.margin})`,
          )
          .join("\n");
      return result(text, wins);
    },
  );

  server.registerTool(
    "top_scoring_teams",
    {
      title: "Top scoring teams",
      description: "Teams ranked by total goals scored in a competition/season.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(100).optional(),
      },
    },
    async ({ competition, season, limit }) => {
      const teams = topScoringTeams(store, { competition, season, limit });
      const scope = [season, competition].filter(Boolean).join(" ");
      const text =
        `Top scoring teams${scope ? ` (${scope})` : ""}:\n` +
        teams.map((t, i) => `${i + 1}. ${t.team} - ${t.goals} goals`).join("\n");
      return result(text, teams);
    },
  );

  return server;
}
