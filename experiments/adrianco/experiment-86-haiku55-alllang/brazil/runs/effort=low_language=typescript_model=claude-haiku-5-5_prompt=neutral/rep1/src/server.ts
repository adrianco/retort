import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { Dataset } from "./model.js";
import {
  clubSummary,
  headToHead,
  matchStatistics,
  searchMatches,
  searchPlayers,
  standings,
  teamRecord,
  DEFAULT_LEAGUE,
} from "./queries.js";
import {
  formatClubSummary,
  formatHeadToHead,
  formatMatchSearch,
  formatMatchStats,
  formatPlayers,
  formatRecord,
  formatStandings,
} from "./format.js";

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Use YYYY-MM-DD")
  .describe("Date as YYYY-MM-DD");
const season = z.number().int().min(2000).max(2100).describe("Season year, e.g. 2023");
const competition = z
  .string()
  .describe(
    'Competition name or part of it: "Brasileirão Série A" ("Brasileirão" alone also includes Série B and C), "Copa do Brasil", "Libertadores"',
  );
const limit = (max: number) => z.number().int().min(1).max(max).optional();

type TextResult = { content: { type: "text"; text: string }[] };
const text = (t: string): TextResult => ({ content: [{ type: "text", text: t }] });

/**
 * Build the MCP server. `getDataset` is called lazily so the CSVs are only
 * parsed on first use, and then cached by the caller.
 */
export function createServer(getDataset: () => Dataset): McpServer {
  const server = new McpServer({ name: "brazilian-soccer", version: "1.0.0" });

  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Find matches by team, opponent, competition, season or date range. Use for questions like 'Show me all Flamengo vs Fluminense matches' or 'What matches did Palmeiras play in 2023?'.",
      inputSchema: {
        team: z.string().optional().describe("Team name, with or without state suffix"),
        opponent: z.string().optional().describe("Second team; with `team`, returns meetings between the two"),
        competition: competition.optional(),
        season: season.optional(),
        start_date: isoDate.optional(),
        end_date: isoDate.optional(),
        limit: limit(100),
      },
    },
    async (args) => {
      const result = searchMatches(getDataset(), {
        team: args.team,
        opponent: args.opponent,
        competition: args.competition,
        season: args.season,
        startDate: args.start_date,
        endDate: args.end_date,
        limit: args.limit,
      });
      return text(formatMatchSearch(result));
    },
  );

  server.registerTool(
    "team_record",
    {
      title: "Team record",
      description:
        "Win/draw/loss record, goals for and against, and win rate for one team, optionally by season, competition or venue. Use for questions like 'What is Corinthians' home record in 2022?'.",
      inputSchema: {
        team: z.string().describe("Team name"),
        competition: competition.optional(),
        season: season.optional(),
        venue: z.enum(["home", "away", "any"]).optional().describe("Restrict to home or away games"),
      },
    },
    async (args) => {
      const rec = teamRecord(getDataset(), {
        team: args.team,
        competition: args.competition,
        season: args.season,
        venue: args.venue,
      });
      const venueLabel = args.venue && args.venue !== "any" ? ` ${args.venue}` : "";
      const scope = [args.competition, args.season].filter((v) => v !== undefined).join(" ");
      const title = `${args.team}${venueLabel} record${scope ? ` (${scope})` : ""}:`;
      return text(formatRecord(title, rec));
    },
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head to head",
      description:
        "All meetings between two teams with the record from the first team's perspective. Use for 'Compare Palmeiras and Santos head-to-head' or 'When did Flamengo last play Corinthians?'.",
      inputSchema: {
        team_a: z.string().describe("First team"),
        team_b: z.string().describe("Second team"),
        competition: competition.optional(),
      },
    },
    async (args) => {
      const h = headToHead(getDataset(), {
        teamA: args.team_a,
        teamB: args.team_b,
        competition: args.competition,
      });
      return text(formatHeadToHead(h));
    },
  );

  server.registerTool(
    "standings",
    {
      title: "League standings",
      description:
        "League table for a season calculated from match results (3 points for a win, 1 for a draw). Also shows goals for/against, which gives the top scorers by team. Defaults to the Brasileirão Série A.",
      inputSchema: {
        season,
        competition: competition.optional().describe(`Defaults to "${DEFAULT_LEAGUE}"`),
      },
    },
    async (args) => {
      const rows = standings(getDataset(), { season: args.season, competition: args.competition });
      const title = `${args.competition ?? DEFAULT_LEAGUE} ${args.season} standings (calculated from matches):`;
      return text(formatStandings(title, rows));
    },
  );

  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search the FIFA player data by name, nationality, club, position or minimum overall rating, sorted by rating. Use for 'Who is Gabriel Barbosa?', 'Find all Brazilian players in the dataset' or 'Show me all forwards from São Paulo FC'.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional().describe('e.g. "Brazil"'),
        club: z.string().optional().describe('e.g. "Flamengo"'),
        position: z.string().optional().describe('FIFA position code, e.g. "ST", "GK", "CDM"'),
        min_overall: z.number().min(0).max(100).optional(),
        limit: limit(100),
      },
    },
    async (args) => {
      const players = searchPlayers(getDataset(), {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.min_overall,
        limit: args.limit,
      });
      return text(formatPlayers(players));
    },
  );

  server.registerTool(
    "club_squad_summary",
    {
      title: "Players per club",
      description:
        "Number of players and average overall rating per club, optionally for one nationality. Use for 'Brazilian players at Brazilian clubs'.",
      inputSchema: {
        nationality: z.string().optional().describe('e.g. "Brazil"'),
        limit: limit(100),
      },
    },
    async (args) => {
      const rows = clubSummary(getDataset(), { nationality: args.nationality }).slice(0, args.limit ?? 20);
      return text(formatClubSummary(rows));
    },
  );

  server.registerTool(
    "match_statistics",
    {
      title: "Match statistics",
      description:
        "Aggregate statistics: average goals per match, home/draw/away rates and the biggest wins, for a season, competition or team. Use for 'What's the average goals per match in the Brasileirão?' or 'Show me the biggest wins in the dataset'.",
      inputSchema: {
        team: z.string().optional(),
        competition: competition.optional(),
        season: season.optional(),
        limit: limit(20).describe("How many biggest wins to list"),
      },
    },
    async (args) => {
      const stats = matchStatistics(getDataset(), {
        team: args.team,
        competition: args.competition,
        season: args.season,
        biggestWinsLimit: args.limit,
      });
      const scope = [args.team, args.competition, args.season].filter((v) => v !== undefined).join(" ");
      return text(formatMatchStats(`Match statistics${scope ? ` (${scope})` : " (all data)"}:`, stats));
    },
  );

  return server;
}
