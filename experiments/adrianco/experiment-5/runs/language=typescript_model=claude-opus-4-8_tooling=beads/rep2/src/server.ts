/**
 * server.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   The MCP server definition. Wires the query services (matches, teams,
 *   players, competitions, stats) to MCP tools that an LLM client can call to
 *   answer natural-language questions about Brazilian soccer.
 *
 *   Tools cover the five capability areas in the spec:
 *     - search_matches / head_to_head            (Match Queries)
 *     - team_record                              (Team Queries)
 *     - search_players / club_player_breakdown   (Player Queries)
 *     - standings / list_seasons                 (Competition Queries)
 *     - match_statistics / biggest_wins /
 *       team_rankings                            (Statistical Analysis)
 *
 *   Each tool validates input with zod, calls the relevant service, and returns
 *   a formatted text block (see format.ts). `createServer` is exported so both
 *   the stdio entry point (index.ts) and tests can construct a server over an
 *   injectable dataset.
 * -----------------------------------------------------------------------------
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { Dataset } from "./types.js";
import { loadDataset } from "./data/loader.js";
import { findMatches, headToHead } from "./services/matches.js";
import { teamRecord } from "./services/teams.js";
import { findPlayers, clubBreakdown } from "./services/players.js";
import { standings, listSeasons, relegated } from "./services/competitions.js";
import { aggregateStats, biggestWins, bestRecords } from "./services/stats.js";
import * as fmt from "./format.js";

const venueSchema = z.enum(["home", "away", "any"]).default("any");

function text(s: string) {
  return { content: [{ type: "text" as const, text: s }] };
}

/** Build an MCP server bound to the given dataset (defaults to the full load). */
export function createServer(dataset?: Dataset): McpServer {
  const ds = dataset ?? loadDataset();

  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  // ---- Match Queries -------------------------------------------------------

  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Find matches by team, opponent, competition, season and/or date range. " +
        "Use `team` alone for a club's fixtures, or `team`+`opponent` for a specific rivalry.",
      inputSchema: {
        team: z.string().optional().describe("Team name (any naming variant)"),
        opponent: z.string().optional().describe("Restrict to matches vs this opponent"),
        competition: z
          .string()
          .optional()
          .describe("e.g. Brasileirão, Copa do Brasil, Libertadores"),
        season: z.number().int().optional().describe("Season year, e.g. 2019"),
        dateFrom: z.string().optional().describe("Inclusive ISO date lower bound"),
        dateTo: z.string().optional().describe("Inclusive ISO date upper bound"),
        venue: venueSchema.describe("Whether `team` played home, away, or any"),
        limit: z.number().int().optional().describe("Max matches to return"),
      },
    },
    async (args) => {
      const matches = findMatches(ds, args);
      const header = `Found ${matches.length} match(es).`;
      return text(`${header}\n${fmt.formatMatchList(matches, args.limit || 25)}`);
    },
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head",
      description:
        "Compare two teams head-to-head: match list plus win/draw tally and goals.",
      inputSchema: {
        teamA: z.string().describe("First team"),
        teamB: z.string().describe("Second team"),
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const h = headToHead(ds, args.teamA, args.teamB, {
        competition: args.competition,
        season: args.season,
      });
      return text(fmt.formatHeadToHead(h));
    },
  );

  // ---- Team Queries --------------------------------------------------------

  server.registerTool(
    "team_record",
    {
      title: "Team record",
      description:
        "Win/draw/loss record, goals and points for a team, optionally filtered " +
        "by season, competition and venue (home/away).",
      inputSchema: {
        team: z.string().describe("Team name"),
        season: z.number().int().optional(),
        competition: z.string().optional(),
        venue: venueSchema,
      },
    },
    async (args) => {
      const r = teamRecord(ds, args.team, {
        season: args.season,
        competition: args.competition,
        venue: args.venue,
      });
      return text(fmt.formatTeamRecord(r));
    },
  );

  // ---- Player Queries ------------------------------------------------------

  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search FIFA players by name, nationality, club, position and minimum rating. " +
        "Sorted by overall rating (descending) unless otherwise specified.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional().describe('e.g. "Brazil"'),
        club: z.string().optional(),
        position: z.string().optional().describe('e.g. "GK", "ST", "LW"'),
        minOverall: z.number().int().optional(),
        sortBy: z.enum(["overall", "potential", "age", "name"]).optional(),
        limit: z.number().int().optional().describe("Default 20"),
      },
    },
    async (args) => {
      const players = findPlayers(ds, args);
      const header = `Found ${players.length} player(s).`;
      return text(`${header}\n${fmt.formatPlayerList(players, args.limit || 20)}`);
    },
  );

  server.registerTool(
    "club_player_breakdown",
    {
      title: "Club player breakdown",
      description:
        "Group matching players by club with count and average rating " +
        '(e.g. nationality="Brazil" for Brazilian players per club).',
      inputSchema: {
        nationality: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().optional(),
        topN: z.number().int().optional().describe("Number of clubs to show"),
      },
    },
    async (args) => {
      const rows = clubBreakdown(
        ds,
        {
          nationality: args.nationality,
          position: args.position,
          minOverall: args.minOverall,
        },
        args.topN || 0,
      );
      return text(fmt.formatClubBreakdown(rows, args.topN || 15));
    },
  );

  // ---- Competition Queries -------------------------------------------------

  server.registerTool(
    "standings",
    {
      title: "League standings",
      description:
        "Reconstruct the final league table for a competition + season from match " +
        "results (points, W/D/L, goals). Use for champions and final positions.",
      inputSchema: {
        competition: z.string().default("Brasileirão"),
        season: z.number().int().describe("Season year, e.g. 2019"),
        relegationCount: z
          .number()
          .int()
          .optional()
          .describe("If set, also list the bottom N (relegated) teams"),
      },
    },
    async (args) => {
      const table = standings(ds, args.competition, args.season);
      let out = fmt.formatStandings(table, args.competition, args.season);
      if (args.relegationCount && args.relegationCount > 0) {
        const down = relegated(ds, args.competition, args.season, args.relegationCount);
        out +=
          `\n\nRelegated (bottom ${args.relegationCount}): ` +
          down.map((r) => `${r.team} (${r.points} pts)`).join(", ");
      }
      return text(out);
    },
  );

  server.registerTool(
    "list_seasons",
    {
      title: "List seasons",
      description: "List the seasons available for a competition (or all data).",
      inputSchema: {
        competition: z.string().optional(),
      },
    },
    async (args) => {
      const seasons = listSeasons(ds, args.competition);
      const label = args.competition ?? "all competitions";
      return text(
        seasons.length
          ? `Seasons available for ${label}: ${seasons.join(", ")}`
          : `No seasons found for ${label}.`,
      );
    },
  );

  // ---- Statistical Analysis ------------------------------------------------

  server.registerTool(
    "match_statistics",
    {
      title: "Match statistics",
      description:
        "Aggregate statistics over a filtered match set: average goals per match, " +
        "home/draw/away win rates.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        team: z.string().optional(),
      },
    },
    async (args) => {
      const s = aggregateStats(ds, args);
      const scope =
        [args.competition, args.season, args.team].filter(Boolean).join(" ") ||
        "All";
      return text(fmt.formatAggregateStats(s, `${scope} matches`));
    },
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description: "Largest winning margins in a filtered match set.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        team: z.string().optional(),
        limit: z.number().int().optional().describe("Default 10"),
      },
    },
    async (args) => {
      const wins = biggestWins(
        ds,
        { competition: args.competition, season: args.season, team: args.team },
        args.limit || 10,
      );
      return text(fmt.formatBiggestWins(wins));
    },
  );

  server.registerTool(
    "team_rankings",
    {
      title: "Team rankings",
      description:
        "Rank teams by record (win rate, points, goals or goal difference), " +
        "optionally for a venue (best home/away record), competition and season.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        venue: venueSchema,
        metric: z
          .enum(["winRate", "points", "goalsFor", "goalDifference"])
          .optional(),
        minMatches: z.number().int().optional().describe("Min matches (default 5)"),
        limit: z.number().int().optional().describe("Default 10"),
      },
    },
    async (args) => {
      const records = bestRecords(ds, args);
      return text(fmt.formatTeamRankings(records, args.limit || 10));
    },
  );

  return server;
}
