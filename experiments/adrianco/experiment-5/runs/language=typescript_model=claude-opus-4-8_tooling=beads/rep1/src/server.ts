/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/server.ts
 * Purpose: Define the MCP server and register all Brazilian-soccer tools,
 *          wiring each tool to the query layer.
 *
 * The server loads the unified dataset once (cached in loader.ts) and exposes
 * nine tools spanning the five capability categories in TASK.md:
 *   Match:        search_matches, head_to_head
 *   Team:         team_stats
 *   Player:       search_players, club_squad
 *   Competition:  standings, season_summary
 *   Statistical:  aggregate_stats, biggest_wins, top_scoring_teams
 *
 * `createServer` is factored out so both the stdio entrypoint (index.ts) and
 * the test suite can build a fully-wired server (or call the query layer
 * directly). Each tool returns human-readable text content; the underlying
 * query functions also return structured objects for programmatic callers.
 * ============================================================================
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { loadDataset } from "./data/loader.js";
import type { Dataset, Competition } from "./data/types.js";
import { searchMatches, headToHead } from "./queries/matches.js";
import { teamStats } from "./queries/teams.js";
import { searchPlayers, clubSquad } from "./queries/players.js";
import { standings, seasonSummary } from "./queries/competitions.js";
import { aggregateStats, biggestWins, topScoringTeams } from "./queries/stats.js";

const COMPETITIONS: Competition[] = [
  "Brasileirão Série A",
  "Brasileirão Série B",
  "Brasileirão Série C",
  "Copa do Brasil",
  "Copa Libertadores",
];

const competitionSchema = z
  .enum(COMPETITIONS as [Competition, ...Competition[]])
  .describe("Competition name");

function textResult(text: string) {
  return { content: [{ type: "text" as const, text }] };
}

/** Build a fully-wired MCP server backed by the given (or default) dataset. */
export function createServer(dataset?: Dataset): McpServer {
  const ds = dataset ?? loadDataset();

  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  // --- Match queries -------------------------------------------------------
  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Search Brazilian soccer matches by team, opponent, competition, " +
        "season and/or date range. Returns the most recent matches first.",
      inputSchema: {
        team: z.string().optional().describe("Team name (home or away)"),
        opponent: z
          .string()
          .optional()
          .describe("Restrict to matches against this opponent"),
        side: z
          .enum(["home", "away", "either"])
          .optional()
          .describe("Restrict `team` to home, away, or either (default)"),
        competition: competitionSchema.optional(),
        season: z.number().int().optional().describe("Season year, e.g. 2019"),
        from: z.string().optional().describe("Start date, ISO YYYY-MM-DD"),
        to: z.string().optional().describe("End date, ISO YYYY-MM-DD"),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async (args) => {
      const res = searchMatches(
        ds,
        {
          team: args.team,
          opponent: args.opponent,
          teamSide: args.side,
          competition: args.competition,
          season: args.season,
          from: args.from,
          to: args.to,
        },
        args.limit ?? 25
      );
      return textResult(res.text);
    }
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head record",
      description:
        "Compute the all-time head-to-head record between two teams: wins, " +
        "draws, goals and recent meetings. Optionally scope by competition/season.",
      inputSchema: {
        teamA: z.string().describe("First team"),
        teamB: z.string().describe("Second team"),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const res = headToHead(ds, args.teamA, args.teamB, {
        competition: args.competition,
        season: args.season,
      });
      return textResult(res.text);
    }
  );

  // --- Team queries --------------------------------------------------------
  server.registerTool(
    "team_stats",
    {
      title: "Team statistics",
      description:
        "Win/draw/loss record, goals for/against and win rate for a team, " +
        "split into overall / home / away. Optionally scope by competition/season.",
      inputSchema: {
        team: z.string().describe("Team name"),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const res = teamStats(ds, args.team, {
        competition: args.competition,
        season: args.season,
      });
      return textResult(res.text);
    }
  );

  // --- Player queries ------------------------------------------------------
  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search FIFA player data by name, nationality, club, position and/or " +
        "minimum overall rating. Results are ranked by overall rating.",
      inputSchema: {
        name: z.string().optional().describe("Substring of the player name"),
        nationality: z
          .string()
          .optional()
          .describe('Nationality, e.g. "Brazil"'),
        club: z.string().optional().describe("Club name"),
        position: z.string().optional().describe('Position code, e.g. "ST"'),
        minOverall: z.number().int().optional().describe("Minimum overall rating"),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async (args) => {
      const res = searchPlayers(
        ds,
        {
          name: args.name,
          nationality: args.nationality,
          club: args.club,
          position: args.position,
          minOverall: args.minOverall,
        },
        args.limit ?? 25
      );
      return textResult(res.text);
    }
  );

  server.registerTool(
    "club_squad",
    {
      title: "Club squad",
      description:
        "List the players registered to a club in the FIFA dataset, ranked by " +
        "overall rating, with the squad's average rating.",
      inputSchema: {
        club: z.string().describe("Club name"),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async (args) => {
      const res = clubSquad(ds, args.club, args.limit ?? 30);
      return textResult(res.text);
    }
  );

  // --- Competition queries -------------------------------------------------
  server.registerTool(
    "standings",
    {
      title: "League standings",
      description:
        "Compute the final league table for a competition and season from " +
        "match results (3 pts win, 1 pt draw).",
      inputSchema: {
        competition: competitionSchema,
        season: z.number().int().describe("Season year, e.g. 2019"),
      },
    },
    async (args) => {
      const res = standings(ds, args.competition, args.season);
      return textResult(res.text);
    }
  );

  server.registerTool(
    "season_summary",
    {
      title: "Season summary",
      description:
        "Summarize a league season: champion and relegation zone, computed " +
        "from match results.",
      inputSchema: {
        competition: competitionSchema,
        season: z.number().int(),
        relegationSpots: z.number().int().min(0).max(10).optional(),
      },
    },
    async (args) => {
      const res = seasonSummary(
        ds,
        args.competition,
        args.season,
        args.relegationSpots ?? 4
      );
      return textResult(res.text);
    }
  );

  // --- Statistical analysis ------------------------------------------------
  server.registerTool(
    "aggregate_stats",
    {
      title: "Aggregate statistics",
      description:
        "Average goals per match, home/away win rates and draw rate for a " +
        "filtered slice of matches (by competition / season / team).",
      inputSchema: {
        team: z.string().optional(),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        from: z.string().optional().describe("Start date, ISO YYYY-MM-DD"),
        to: z.string().optional().describe("End date, ISO YYYY-MM-DD"),
      },
    },
    async (args) => {
      const res = aggregateStats(ds, {
        team: args.team,
        competition: args.competition,
        season: args.season,
        from: args.from,
        to: args.to,
      });
      return textResult(res.text);
    }
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description:
        "Find matches with the largest goal margins, optionally scoped by " +
        "competition / season / team.",
      inputSchema: {
        team: z.string().optional(),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(100).optional(),
      },
    },
    async (args) => {
      const res = biggestWins(
        ds,
        {
          team: args.team,
          competition: args.competition,
          season: args.season,
        },
        args.limit ?? 10
      );
      return textResult(res.text);
    }
  );

  server.registerTool(
    "top_scoring_teams",
    {
      title: "Top scoring teams",
      description:
        "Rank teams by total goals scored within a filtered slice of matches.",
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(100).optional(),
      },
    },
    async (args) => {
      const res = topScoringTeams(
        ds,
        { competition: args.competition, season: args.season },
        args.limit ?? 10
      );
      return textResult(res.text);
    }
  );

  return server;
}
