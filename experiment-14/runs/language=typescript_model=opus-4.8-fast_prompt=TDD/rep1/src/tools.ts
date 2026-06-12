/**
 * Tool registry mapping the MCP-exposed capabilities to the query engine.
 *
 * Each `ToolDef` bundles a name, description, a Zod schema (for input
 * validation), a derived JSON Schema (for MCP advertisement) and a handler that
 * turns validated arguments into a formatted, human-readable answer string.
 * Keeping this layer transport-agnostic lets the handlers be unit-tested
 * directly, while `server.ts` wires them into the MCP stdio transport.
 */

import { z } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";
import type { SoccerDatabase } from "./database.js";
import { parseDate } from "./normalize.js";
import {
  formatMatchList,
  formatHeadToHead,
  formatTeamRecord,
  formatStandings,
  formatStatistics,
  formatPlayerList,
} from "./format.js";

export interface ToolDef {
  name: string;
  description: string;
  schema: z.ZodTypeAny;
  jsonSchema: Record<string, unknown>;
  handler: (args: any) => string;
}

function def<S extends z.ZodTypeAny>(
  name: string,
  description: string,
  schema: S,
  handler: (args: z.infer<S>) => string
): ToolDef {
  return {
    name,
    description,
    schema,
    jsonSchema: zodToJsonSchema(schema, name) as Record<string, unknown>,
    handler,
  };
}

const teamField = z.string().describe("Team name (any common variation)");
const optDate = z
  .string()
  .optional()
  .describe("Date as YYYY-MM-DD or DD/MM/YYYY");

/** Build the full tool set bound to a database instance. */
export function createTools(db: SoccerDatabase): ToolDef[] {
  const findMatches = def(
    "find_matches",
    "Find matches by team, opponent, competition, season, or date range. " +
      "When two teams are given, also reports their head-to-head record.",
    z.object({
      team: z.string().optional().describe("A team that must be involved"),
      team2: z
        .string()
        .optional()
        .describe("Restrict to matches between team and team2"),
      homeTeam: z.string().optional().describe("Team that played at home"),
      awayTeam: z.string().optional().describe("Team that played away"),
      competition: z
        .string()
        .optional()
        .describe("Competition name or fragment, e.g. 'Libertadores'"),
      season: z.number().int().optional().describe("Season year"),
      from: optDate.describe("Start of date range"),
      to: optDate.describe("End of date range"),
      limit: z.number().int().positive().optional(),
    }),
    (a) => {
      const matches = db.findMatches({
        team: a.team,
        team2: a.team2,
        homeTeam: a.homeTeam,
        awayTeam: a.awayTeam,
        competition: a.competition,
        season: a.season,
        from: a.from ? parseDate(a.from) ?? undefined : undefined,
        to: a.to ? parseDate(a.to) ?? undefined : undefined,
        limit: a.limit,
      });
      const labelParts = [a.team, a.team2].filter(Boolean).join(" vs ");
      const header = labelParts
        ? `Matches: ${labelParts}`
        : "Matches found";
      let out = formatMatchList(matches, header);
      if (a.team && a.team2) {
        out += "\n\n" + formatHeadToHead(db.headToHead(a.team, a.team2));
      }
      return out;
    }
  );

  const teamRecord = def(
    "team_record",
    "Get a team's win/draw/loss record, goals and points, optionally filtered " +
      "by season, competition, and home/away venue.",
    z.object({
      team: teamField,
      season: z.number().int().optional(),
      competition: z.string().optional(),
      venue: z.enum(["home", "away", "all"]).optional(),
    }),
    (a) => {
      const rec = db.teamRecord(a.team, {
        season: a.season,
        competition: a.competition,
        venue: a.venue,
      });
      const ctx = [
        a.team,
        a.venue && a.venue !== "all" ? `${a.venue} record` : "record",
        a.season ? `(${a.season})` : "",
        a.competition ? `[${a.competition}]` : "",
      ]
        .filter(Boolean)
        .join(" ");
      return formatTeamRecord(rec, ctx);
    }
  );

  const headToHead = def(
    "head_to_head",
    "Compare two teams head-to-head: total meetings, wins for each side, draws, " +
      "and the list of matches.",
    z.object({
      teamA: teamField,
      teamB: teamField,
      limit: z.number().int().positive().optional(),
    }),
    (a) => {
      const h = db.headToHead(a.teamA, a.teamB);
      const list = formatMatchList(
        a.limit ? h.games.slice(0, a.limit) : h.games,
        `${a.teamA} vs ${a.teamB}`
      );
      return list + "\n\n" + formatHeadToHead(h);
    }
  );

  const standings = def(
    "standings",
    "Compute the final standings (points table) for a competition and season " +
      "from match results.",
    z.object({
      competition: z
        .string()
        .describe("Competition name or fragment, e.g. 'Brasileirão'"),
      season: z.number().int().describe("Season year"),
    }),
    (a) => {
      const table = db.standings(a.competition, a.season);
      return formatStandings(table, `${a.season} ${a.competition} standings`);
    }
  );

  const matchStatistics = def(
    "match_statistics",
    "Aggregate statistics (average goals, home/away win rates, draw rate) over " +
      "matches, optionally filtered by competition, season, or team.",
    z.object({
      competition: z.string().optional(),
      season: z.number().int().optional(),
      team: z.string().optional(),
    }),
    (a) => {
      const stats = db.statistics({
        competition: a.competition,
        season: a.season,
        team: a.team,
      });
      const ctx = [
        a.team,
        a.competition,
        a.season ? `${a.season}` : "",
      ]
        .filter(Boolean)
        .join(" ");
      return formatStatistics(stats, ctx ? `Statistics: ${ctx}` : "Statistics");
    }
  );

  const biggestWins = def(
    "biggest_wins",
    "List the matches with the largest goal margins, optionally filtered by " +
      "competition, season, or team.",
    z.object({
      competition: z.string().optional(),
      season: z.number().int().optional(),
      team: z.string().optional(),
      limit: z.number().int().positive().optional().default(10),
    }),
    (a) => {
      const matches = db.biggestWins({
        competition: a.competition,
        season: a.season,
        team: a.team,
        limit: a.limit,
      });
      return formatMatchList(matches, "Biggest victories", a.limit);
    }
  );

  const searchPlayers = def(
    "search_players",
    "Search FIFA player data by name, nationality, club, or position. Results " +
      "are sorted by overall rating (highest first).",
    z.object({
      name: z.string().optional(),
      nationality: z
        .string()
        .optional()
        .describe("e.g. 'Brazil' for Brazilian players"),
      club: z.string().optional(),
      position: z.string().optional().describe("e.g. 'ST', 'GK', 'LW'"),
      minOverall: z.number().int().optional(),
      limit: z.number().int().positive().optional().default(25),
    }),
    (a) => {
      const players = db.findPlayers({
        name: a.name,
        nationality: a.nationality,
        club: a.club,
        position: a.position,
        minOverall: a.minOverall,
        limit: a.limit,
      });
      const ctx = [a.nationality, a.position, a.club ? `at ${a.club}` : "", a.name]
        .filter(Boolean)
        .join(" ");
      return formatPlayerList(players, ctx ? `Players: ${ctx}` : "Players");
    }
  );

  const brazilianByClub = def(
    "brazilian_players_by_club",
    "Group Brazilian players who play at Brazilian clubs, with per-club counts " +
      "and average ratings.",
    z.object({
      limit: z.number().int().positive().optional().default(25),
    }),
    (a) => {
      const groups = db.brazilianPlayersByClub().slice(0, a.limit);
      if (groups.length === 0) {
        return "Brazilian players at Brazilian clubs\nNo players found.";
      }
      const lines = groups.map(
        (g) =>
          `- ${g.club}: ${g.count} players (avg rating: ${g.averageOverall.toFixed(0)})`
      );
      return `Brazilian players at Brazilian clubs:\n${lines.join("\n")}`;
    }
  );

  return [
    findMatches,
    teamRecord,
    headToHead,
    standings,
    matchStatistics,
    biggestWins,
    searchPlayers,
    brazilianByClub,
  ];
}
