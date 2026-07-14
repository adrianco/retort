/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/server.ts
 * Purpose: Build the Brazilian Soccer MCP server and register all query tools.
 *          Each tool wraps a function from the query layer, validates input
 *          with Zod, and returns both human-readable text and structured JSON.
 * Inputs:  Optional data directory (defaults to bundled data/kaggle).
 * Outputs: A configured `McpServer` instance (transport-agnostic).
 * Notes:   The dataset is loaded once (cached) on first tool call. Tools cover
 *          all five required capability categories: match, team, player,
 *          competition, and statistical-analysis queries.
 * ============================================================================
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { loadDataset, type Dataset } from "./data/loader.js";
import { findMatches, headToHead } from "./queries/matches.js";
import {
  teamRecord,
  teamCompetitions,
  resolveTeam,
} from "./queries/teams.js";
import { findPlayers, playersByClub } from "./queries/players.js";
import {
  standings,
  competitionSummary,
  availableSeasons,
} from "./queries/competitions.js";
import {
  aggregateStats,
  biggestWins,
  topScoringTeams,
  bestVenueRecords,
} from "./queries/statistics.js";
import {
  formatMatchList,
  formatHeadToHead,
  formatTeamRecord,
  formatStandings,
  formatPlayerList,
} from "./format.js";

/** Build a CallToolResult from text + structured payload. */
function result(text: string, structured?: unknown) {
  return {
    content: [{ type: "text" as const, text }],
    ...(structured !== undefined
      ? { structuredContent: structured as Record<string, unknown> }
      : {}),
  };
}

const COMPETITIONS = [
  "Brasileirão Série A",
  "Brasileirão Série B",
  "Brasileirão Série C",
  "Copa do Brasil",
  "Copa Libertadores",
];

/**
 * Create and configure the MCP server. The dataset is lazily loaded the first
 * time a tool runs so server startup stays fast.
 */
export function createServer(dataDir?: string): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  let ds: Dataset | null = null;
  const data = (): Dataset => (ds ??= loadDataset(dataDir));

  // --- 1. Match queries --------------------------------------------------
  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Find matches by team, opponent, competition, season, and/or date " +
        "range. Team names are matched flexibly (accents, state suffixes, " +
        "and common variants are handled). Returns matches most-recent first.",
      inputSchema: {
        team: z.string().optional().describe("Team name (home, away, or either)"),
        opponent: z
          .string()
          .optional()
          .describe("Second team; restricts to matches between team & opponent"),
        side: z.enum(["home", "away", "either"]).optional(),
        competition: z
          .string()
          .optional()
          .describe(`One of: ${COMPETITIONS.join(", ")} (aliases accepted)`),
        season: z.number().int().optional().describe("Season year, e.g. 2019"),
        dateFrom: z.string().optional().describe("Inclusive ISO date YYYY-MM-DD"),
        dateTo: z.string().optional().describe("Inclusive ISO date YYYY-MM-DD"),
        limit: z.number().int().positive().optional().default(25),
      },
    },
    async (args) => {
      const matches = findMatches(data(), {
        team: args.team,
        team2: args.opponent,
        side: args.side,
        competition: args.competition,
        season: args.season,
        dateFrom: args.dateFrom,
        dateTo: args.dateTo,
        limit: args.limit,
      });
      const text = formatMatchList(matches, args.limit ?? 25);
      return result(`Found ${matches.length} match(es).\n${text}`, {
        count: matches.length,
        matches,
      });
    },
  );

  // --- head-to-head ------------------------------------------------------
  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head record",
      description:
        "Compute the head-to-head record between two teams (wins, draws, " +
        "goals) across all competitions, optionally scoped by competition " +
        "or season.",
      inputSchema: {
        team1: z.string(),
        team2: z.string(),
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const h = headToHead(data(), args.team1, args.team2, {
        competition: args.competition,
        season: args.season,
      });
      return result(formatHeadToHead(h), h);
    },
  );

  // --- 2. Team queries ---------------------------------------------------
  server.registerTool(
    "team_record",
    {
      title: "Team record",
      description:
        "Compute a team's win/draw/loss record and goals, optionally filtered " +
        "by season, competition, and venue (home/away/all).",
      inputSchema: {
        team: z.string(),
        season: z.number().int().optional(),
        competition: z.string().optional(),
        venue: z.enum(["home", "away", "all"]).optional(),
      },
    },
    async (args) => {
      const rec = teamRecord(data(), args.team, {
        season: args.season,
        competition: args.competition,
        venue: args.venue,
      });
      const scopeParts: string[] = [];
      if (args.season != null) scopeParts.push(String(args.season));
      if (args.competition) scopeParts.push(args.competition);
      if (args.venue && args.venue !== "all") scopeParts.push(`${args.venue} only`);
      return result(formatTeamRecord(rec, scopeParts.join(" ")), rec);
    },
  );

  server.registerTool(
    "team_competitions",
    {
      title: "Team competitions",
      description:
        "List the competitions a team has appeared in (per the datasets) with " +
        "appearance counts.",
      inputSchema: { team: z.string() },
    },
    async (args) => {
      const comps = teamCompetitions(data(), args.team);
      const name = resolveTeam(data(), args.team) ?? args.team;
      const text =
        comps.length === 0
          ? `No competitions found for "${args.team}".`
          : `${name} has appeared in:\n` +
            comps
              .map((c) => `- ${c.competition}: ${c.appearances} matches`)
              .join("\n");
      return result(text, { team: name, competitions: comps });
    },
  );

  // --- 3. Player queries -------------------------------------------------
  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search the FIFA player database by name, nationality, club, and/or " +
        "position. Sorted by overall rating by default. Use nationality " +
        "'Brazil' for Brazilian players.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional().describe("e.g. GK, CB, LW, ST"),
        minOverall: z.number().int().optional(),
        sortBy: z.enum(["overall", "potential", "age", "name"]).optional(),
        limit: z.number().int().positive().optional().default(25),
      },
    },
    async (args) => {
      const players = findPlayers(data(), {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
        sortBy: args.sortBy,
        limit: args.limit,
      });
      return result(
        `Found ${players.length} player(s).\n${formatPlayerList(players, args.limit ?? 25)}`,
        { count: players.length, players },
      );
    },
  );

  server.registerTool(
    "players_by_club",
    {
      title: "Players grouped by club",
      description:
        "Summarize players grouped by club (count + average overall rating), " +
        "optionally filtered by nationality (e.g. 'Brazil'). Useful for " +
        "'Brazilian players at Brazilian clubs' style questions.",
      inputSchema: {
        nationality: z.string().optional(),
        limit: z.number().int().positive().optional().default(20),
      },
    },
    async (args) => {
      const summaries = playersByClub(data(), {
        nationality: args.nationality,
        limit: args.limit,
      });
      const text =
        summaries.length === 0
          ? "No players found."
          : summaries
              .map(
                (s) =>
                  `- ${s.club}: ${s.count} players (avg rating: ${s.avgOverall})`,
              )
              .join("\n");
      return result(text, { clubs: summaries });
    },
  );

  // --- 4. Competition queries -------------------------------------------
  server.registerTool(
    "standings",
    {
      title: "League standings",
      description:
        "Compute the final league table for a competition + season directly " +
        "from match results (3-1-0 points).",
      inputSchema: {
        competition: z.string().describe(`e.g. ${COMPETITIONS.join(", ")}`),
        season: z.number().int(),
        limit: z.number().int().positive().optional().default(30),
      },
    },
    async (args) => {
      const rows = standings(data(), args.competition, args.season);
      const title = `${args.competition} ${args.season} Standings`;
      return result(formatStandings(rows, title, args.limit ?? 30), {
        competition: args.competition,
        season: args.season,
        table: rows,
      });
    },
  );

  server.registerTool(
    "competition_summary",
    {
      title: "Competition season summary",
      description:
        "Summarize a competition season: champion, full table, and " +
        "(for full league tables) the relegated teams.",
      inputSchema: {
        competition: z.string(),
        season: z.number().int(),
      },
    },
    async (args) => {
      const sum = competitionSummary(data(), args.competition, args.season);
      const lines = [
        `${args.competition} ${args.season}:`,
        `Champion: ${sum.champion ?? "n/a"}`,
      ];
      if (sum.relegated.length > 0)
        lines.push(`Relegated: ${sum.relegated.join(", ")}`);
      lines.push("");
      lines.push(
        formatStandings(sum.table, `${args.competition} ${args.season} Standings`, 30),
      );
      return result(lines.join("\n"), sum);
    },
  );

  // --- 5. Statistical analysis ------------------------------------------
  server.registerTool(
    "match_statistics",
    {
      title: "Aggregate match statistics",
      description:
        "Headline aggregates over a scope (optional competition/season): " +
        "average goals per match, home/away/draw win rates.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const a = aggregateStats(data(), {
        competition: args.competition,
        season: args.season,
      });
      const scope =
        [args.competition, args.season].filter((x) => x != null).join(" ") ||
        "all competitions";
      const text = [
        `Statistics for ${scope}:`,
        `- Matches (with scores): ${a.scoredMatches}`,
        `- Total goals: ${a.totalGoals}`,
        `- Average goals per match: ${a.avgGoalsPerMatch.toFixed(2)}`,
        `- Home win rate: ${(a.homeWinRate * 100).toFixed(1)}%`,
        `- Away win rate: ${(a.awayWinRate * 100).toFixed(1)}%`,
        `- Draw rate: ${(a.drawRate * 100).toFixed(1)}%`,
      ].join("\n");
      return result(text, a);
    },
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest victories",
      description:
        "List the matches with the largest winning margin within a scope.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().optional().default(10),
      },
    },
    async (args) => {
      const wins = biggestWins(
        data(),
        { competition: args.competition, season: args.season },
        args.limit ?? 10,
      );
      const text =
        wins.length === 0
          ? "No matches found."
          : wins
              .map((w, i) => {
                const m = w.match;
                return `${i + 1}. ${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition}, margin ${w.margin})`;
              })
              .join("\n");
      return result(text, { wins });
    },
  );

  server.registerTool(
    "top_scoring_teams",
    {
      title: "Top scoring teams",
      description:
        "Rank teams by total goals scored within a scope (competition/season).",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().optional().default(10),
      },
    },
    async (args) => {
      const ranks = topScoringTeams(
        data(),
        { competition: args.competition, season: args.season },
        args.limit ?? 10,
      );
      const text =
        ranks.length === 0
          ? "No matches found."
          : ranks
              .map(
                (r, i) =>
                  `${i + 1}. ${r.team} - ${r.goalsFor} goals in ${r.matches} matches`,
              )
              .join("\n");
      return result(text, { teams: ranks });
    },
  );

  server.registerTool(
    "best_venue_records",
    {
      title: "Best home/away records",
      description:
        "Rank teams by win rate at a given venue (home or away) within a " +
        "scope. Teams below the minimum match threshold are excluded.",
      inputSchema: {
        venue: z.enum(["home", "away"]),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().optional().default(10),
        minMatches: z.number().int().positive().optional().default(5),
      },
    },
    async (args) => {
      const recs = bestVenueRecords(
        data(),
        args.venue,
        { competition: args.competition, season: args.season },
        { limit: args.limit, minMatches: args.minMatches },
      );
      const text =
        recs.length === 0
          ? "No matches found."
          : recs
              .map(
                (r, i) =>
                  `${i + 1}. ${r.team} - ${(r.winRate * 100).toFixed(1)}% (${r.wins}W, ${r.draws}D, ${r.losses}L in ${r.played} ${args.venue} matches)`,
              )
              .join("\n");
      return result(text, { venue: args.venue, records: recs });
    },
  );

  // --- meta / discovery --------------------------------------------------
  server.registerTool(
    "list_competitions",
    {
      title: "List competitions & seasons",
      description:
        "List the available competitions and the seasons present in the data.",
      inputSchema: {},
    },
    async () => {
      const d = data();
      const out = COMPETITIONS.map((c) => ({
        competition: c,
        seasons: availableSeasons(d, c),
      })).filter((c) => c.seasons.length > 0);
      const text = out
        .map(
          (c) =>
            `- ${c.competition}: ${c.seasons[0]}-${c.seasons[c.seasons.length - 1]} (${c.seasons.length} seasons)`,
        )
        .join("\n");
      return result(text, { competitions: out });
    },
  );

  server.registerTool(
    "dataset_info",
    {
      title: "Dataset coverage",
      description:
        "Report what data is loaded: number of matches, players, distinct " +
        "teams, and the source files.",
      inputSchema: {},
    },
    async () => {
      const d = data();
      const text = [
        `Loaded ${d.matches.length} matches and ${d.players.length} players.`,
        `Distinct teams: ${d.teamKeys.size}`,
        `Source files (${d.loadedFiles.length}): ${d.loadedFiles.join(", ")}`,
      ].join("\n");
      return result(text, {
        matches: d.matches.length,
        players: d.players.length,
        teams: d.teamKeys.size,
        files: d.loadedFiles,
      });
    },
  );

  return server;
}
