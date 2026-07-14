/**
 * ============================================================================
 * File: src/server.ts
 * Project: Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * Context:
 *   Wires the KnowledgeGraph query surface into MCP tools using the official
 *   @modelcontextprotocol/sdk McpServer. Each tool maps to one of the five
 *   required capability categories from the specification and returns a
 *   human-readable text block (rendered via src/format.ts) plus structured
 *   JSON in `structuredContent` for programmatic consumers.
 *
 *   Tools registered:
 *     - search_matches        (match queries)
 *     - head_to_head          (match / statistical)
 *     - team_record           (team queries)
 *     - team_competitions     (team queries)
 *     - search_players        (player queries)
 *     - standings             (competition queries)
 *     - competition_stats     (statistical analysis)
 *     - biggest_wins          (statistical analysis)
 *     - list_competitions     (discovery)
 * ============================================================================
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { KnowledgeGraph } from "./knowledgeGraph.js";
import {
  formatCompetitionStats,
  formatHeadToHead,
  formatMatchList,
  formatPlayerList,
  formatRecord,
  formatStandings,
} from "./format.js";

function text(body: string, structured?: Record<string, unknown>) {
  return {
    content: [{ type: "text" as const, text: body }],
    ...(structured ? { structuredContent: structured } : {}),
  };
}

/** Build and configure an McpServer backed by the given knowledge graph. */
export function createServer(graph: KnowledgeGraph): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  const venueEnum = z.enum(["home", "away", "either"]);

  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Find Brazilian soccer matches by team, opponent, competition, season and/or date range. Returns matches most-recent first.",
      inputSchema: {
        team: z.string().optional().describe("Team name (e.g. 'Flamengo'). State suffixes are ignored."),
        opponent: z.string().optional().describe("Restrict to fixtures against this opponent."),
        venue: venueEnum.optional().describe("Whether `team` played at home, away or either (default)."),
        competition: z.string().optional().describe("Competition name, e.g. 'Brasileirão Série A', 'Copa do Brasil', 'Copa Libertadores'."),
        season: z.number().int().optional().describe("Season year, e.g. 2023."),
        from: z.string().optional().describe("Inclusive start date (YYYY-MM-DD)."),
        to: z.string().optional().describe("Inclusive end date (YYYY-MM-DD)."),
        limit: z.number().int().positive().optional().describe("Maximum matches to return (default 25)."),
      },
    },
    async (args) => {
      const limit = args.limit ?? 25;
      const matches = graph.findMatches({ ...args, limit });
      const heading = `Matches${args.team ? ` for ${args.team}` : ""}${args.opponent ? ` vs ${args.opponent}` : ""} (${matches.length} shown):`;
      return text(formatMatchList(matches, heading), { count: matches.length, matches });
    },
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head record",
      description: "Compare two teams head-to-head across the dataset: wins, draws, goals and recent meetings.",
      inputSchema: {
        teamA: z.string().describe("First team."),
        teamB: z.string().describe("Second team."),
        competition: z.string().optional().describe("Optional competition filter."),
      },
    },
    async (args) => {
      const h = graph.headToHead(args.teamA, args.teamB, args.competition);
      return text(formatHeadToHead(h), { headToHead: h });
    },
  );

  server.registerTool(
    "team_record",
    {
      title: "Team record",
      description: "Win/draw/loss record and goals for a team, optionally filtered by competition, season and home/away venue.",
      inputSchema: {
        team: z.string().describe("Team name."),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        venue: venueEnum.optional().describe("Restrict to home or away matches."),
      },
    },
    async (args) => {
      const rec = graph.teamRecord(args.team, args);
      const labelParts = [args.season?.toString(), args.competition, args.venue && args.venue !== "either" ? args.venue : undefined].filter(Boolean);
      const label = labelParts.length ? labelParts.join(" ") : undefined;
      const team = graph.resolveTeam(args.team)?.name ?? args.team;
      return text(formatRecord(team, rec, label), { team, record: rec });
    },
  );

  server.registerTool(
    "team_competitions",
    {
      title: "Team competitions",
      description: "List the competitions a team appears in within the dataset.",
      inputSchema: { team: z.string().describe("Team name.") },
    },
    async (args) => {
      const comps = graph.teamCompetitions(args.team);
      const team = graph.resolveTeam(args.team)?.name ?? args.team;
      const body = comps.length
        ? `${team} appears in:\n${comps.map((c) => `- ${c}`).join("\n")}`
        : `No competitions found for ${team}.`;
      return text(body, { team, competitions: comps });
    },
  );

  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description: "Search FIFA player data by name, nationality, club, position and/or minimum overall rating. Sorted by overall rating.",
      inputSchema: {
        name: z.string().optional().describe("Substring of the player's name."),
        nationality: z.string().optional().describe("Exact nationality, e.g. 'Brazil'."),
        club: z.string().optional().describe("Club name, e.g. 'Flamengo'."),
        position: z.string().optional().describe("Position code, e.g. 'ST', 'GK', 'LW'."),
        minOverall: z.number().int().optional().describe("Minimum FIFA overall rating."),
        limit: z.number().int().positive().optional().describe("Maximum players to return (default 25)."),
      },
    },
    async (args) => {
      const limit = args.limit ?? 25;
      const players = graph.findPlayers({ ...args, limit });
      const heading = `Players (${players.length} shown):`;
      return text(formatPlayerList(players, heading), { count: players.length, players });
    },
  );

  server.registerTool(
    "standings",
    {
      title: "Competition standings",
      description: "Compute a league table (points, W/D/L, goal difference) for a competition and season from match results.",
      inputSchema: {
        competition: z.string().describe("Competition name, e.g. 'Brasileirão Série A'."),
        season: z.number().int().describe("Season year, e.g. 2019."),
        limit: z.number().int().positive().optional().describe("Limit number of table rows."),
      },
    },
    async (args) => {
      const rows = graph.standings(args.competition, args.season);
      return text(formatStandings(args.competition, args.season, rows, args.limit), {
        competition: args.competition,
        season: args.season,
        standings: rows,
      });
    },
  );

  server.registerTool(
    "competition_stats",
    {
      title: "Competition statistics",
      description: "Aggregate statistics (average goals per match, home/away/draw rates) for a competition and/or season. Omit both for an all-data summary.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const stats = graph.competitionStats(args.competition, args.season);
      return text(formatCompetitionStats(stats), { stats });
    },
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description: "List the matches with the largest goal margins, optionally filtered by competition and season.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().optional().describe("How many matches to return (default 10)."),
      },
    },
    async (args) => {
      const matches = graph.biggestWins(args);
      return text(formatMatchList(matches, "Biggest victories in dataset:"), { matches });
    },
  );

  server.registerTool(
    "list_competitions",
    {
      title: "List competitions",
      description: "List all competitions and the seasons available in the dataset.",
      inputSchema: {},
    },
    async () => {
      const comps = graph.listCompetitions();
      const lines = comps.map((c) => {
        const seasons = graph.seasons(c);
        const range = seasons.length ? ` (${seasons[0]}–${seasons[seasons.length - 1]})` : "";
        return `- ${c}${range}`;
      });
      return text(`Competitions in dataset:\n${lines.join("\n")}`, { competitions: comps });
    },
  );

  return server;
}
