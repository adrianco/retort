/**
 * ============================================================================
 * Context: Brazilian Soccer MCP Server — MCP Tool Surface
 * ----------------------------------------------------------------------------
 * Purpose : Wires the query engine (queries.ts) and formatters (format.ts) to
 *           the Model Context Protocol. Exposes one tool per capability area
 *           defined in the spec (match / team / player / competition queries
 *           and statistical analysis) so an LLM client can answer natural
 *           language questions about Brazilian soccer.
 * Design  : `createServer()` builds and returns a configured McpServer but does
 *           NOT connect a transport — that is index.ts's job (stdio). This
 *           separation keeps the server unit-testable.
 * Consumers: index.ts (entry point), tests (tool registration smoke test).
 * ============================================================================
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import { loadDataset, type Dataset } from "./dataLoader.js";
import {
  aggregateStats,
  biggestWins,
  competitionsForTeam,
  headToHead,
  rankTeams,
  searchMatches,
  searchPlayers,
  standings,
  teamStats,
} from "./queries.js";
import {
  formatAggregate,
  formatHeadToHead,
  formatMatch,
  formatMatchList,
  formatPlayerList,
  formatStandings,
  formatTeamRankings,
  formatTeamRecord,
} from "./format.js";

const text = (s: string) => ({ content: [{ type: "text" as const, text: s }] });

/**
 * Build a fully configured MCP server. The dataset is loaded eagerly (cached)
 * so the first tool call is fast. Pass an explicit dataset for testing.
 */
export function createServer(dataset: Dataset = loadDataset()): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  const { matches, players, competitions } = dataset;

  // --- 1. Match queries ---------------------------------------------------
  server.tool(
    "search_matches",
    "Search Brazilian soccer matches by team, opponent, competition, season and/or date range. " +
      "Returns a date-sorted list with scores and competition context. " +
      `Known competitions: ${competitions.join(", ")}.`,
    {
      team: z.string().optional().describe("Team name (e.g. 'Flamengo'). Matches home or away."),
      opponent: z
        .string()
        .optional()
        .describe("Second team — when set with `team`, only fixtures between the two are returned."),
      venue: z
        .enum(["home", "away", "any"])
        .optional()
        .describe("Restrict `team` to home or away fixtures (default: any)."),
      competition: z.string().optional().describe("Competition name or fragment, e.g. 'Libertadores'."),
      season: z.number().int().optional().describe("Season year, e.g. 2019."),
      fromDate: z.string().optional().describe("Inclusive start date, ISO YYYY-MM-DD."),
      toDate: z.string().optional().describe("Inclusive end date, ISO YYYY-MM-DD."),
      limit: z.number().int().positive().max(200).optional().describe("Max matches to show (default 25)."),
    },
    async (args) => {
      const result = searchMatches(matches, {
        team: args.team,
        opponent: args.opponent,
        homeOnly: args.venue === "home",
        awayOnly: args.venue === "away",
        competition: args.competition,
        season: args.season,
        fromDate: args.fromDate,
        toDate: args.toDate,
      });
      return text(formatMatchList(result, args.limit ?? 25));
    }
  );

  // --- 2. Team queries ----------------------------------------------------
  server.tool(
    "team_stats",
    "Get a team's win/draw/loss and goal record, optionally filtered by season, competition and home/away.",
    {
      team: z.string().describe("Team name, e.g. 'Corinthians'."),
      season: z.number().int().optional().describe("Season year."),
      competition: z.string().optional().describe("Competition name or fragment."),
      venue: z.enum(["home", "away", "all"]).optional().describe("Home/away/all (default all)."),
    },
    async (args) => {
      const record = teamStats(matches, {
        team: args.team,
        season: args.season,
        competition: args.competition,
        venue: args.venue ?? "all",
      });
      const headingParts = [args.team];
      if (args.venue && args.venue !== "all") headingParts.push(`${args.venue} record`);
      else headingParts.push("record");
      const scope: string[] = [];
      if (args.season !== undefined) scope.push(String(args.season));
      if (args.competition) scope.push(args.competition);
      const heading = `${headingParts.join(" ")}${scope.length ? ` (${scope.join(" ")})` : ""}`;
      return text(formatTeamRecord(record, heading));
    }
  );

  server.tool(
    "head_to_head",
    "Compare two teams head-to-head across all competitions: meetings, wins, draws and goals.",
    {
      teamA: z.string().describe("First team."),
      teamB: z.string().describe("Second team."),
    },
    async (args) => text(formatHeadToHead(headToHead(matches, args.teamA, args.teamB)))
  );

  server.tool(
    "team_competitions",
    "List the competitions a team has appeared in within the dataset.",
    { team: z.string().describe("Team name.") },
    async (args) => {
      const comps = competitionsForTeam(matches, args.team);
      if (comps.length === 0) return text(`No matches found for "${args.team}".`);
      return text(`${args.team} appears in:\n${comps.map((c) => `- ${c}`).join("\n")}`);
    }
  );

  // --- 3. Player queries --------------------------------------------------
  server.tool(
    "search_players",
    "Search the FIFA player database by name, nationality, club and/or position. " +
      "Use nationality='Brazil' for Brazilian players. Results are sorted by Overall rating.",
    {
      name: z.string().optional().describe("Player name fragment, e.g. 'Gabriel Barbosa'."),
      nationality: z.string().optional().describe("Nationality, e.g. 'Brazil'."),
      club: z.string().optional().describe("Club name fragment, e.g. 'Flamengo'."),
      position: z.string().optional().describe("Position code, e.g. 'ST', 'GK', 'CB'."),
      minOverall: z.number().int().optional().describe("Minimum Overall rating."),
      limit: z.number().int().positive().max(200).optional().describe("Max players (default 25)."),
    },
    async (args) => {
      const limit = args.limit ?? 25;
      const all = searchPlayers(players, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
        limit: Number.MAX_SAFE_INTEGER,
      });
      return text(formatPlayerList(all.slice(0, limit), all.length));
    }
  );

  // --- 4. Competition queries ---------------------------------------------
  server.tool(
    "competition_standings",
    "Calculate the final league table for a competition and season from match results (3-1-0 points).",
    {
      competition: z.string().describe("Competition name or fragment, e.g. 'Série A' or 'Brasileirão'."),
      season: z.number().int().describe("Season year, e.g. 2019."),
      limit: z.number().int().positive().max(50).optional().describe("Rows to show (default 30)."),
    },
    async (args) => {
      const rows = standings(matches, args.competition, args.season);
      return text(formatStandings(rows, `${args.season} ${args.competition} Final Standings`, args.limit ?? 30));
    }
  );

  server.tool(
    "list_competitions",
    "List all competitions available in the dataset and the seasons covered.",
    {},
    async () => {
      const seasons = new Map<string, Set<number>>();
      for (const m of matches) {
        if (m.season === null) continue;
        if (!seasons.has(m.competition)) seasons.set(m.competition, new Set());
        seasons.get(m.competition)!.add(m.season);
      }
      const lines = competitions.map((c) => {
        const ys = Array.from(seasons.get(c) ?? []).sort((a, b) => a - b);
        const range = ys.length ? ` (${ys[0]}–${ys[ys.length - 1]})` : "";
        return `- ${c}${range}`;
      });
      return text(`Competitions in dataset:\n${lines.join("\n")}`);
    }
  );

  // --- 5. Statistical analysis --------------------------------------------
  server.tool(
    "match_statistics",
    "Aggregate statistics over a slice of matches: average goals per match, home/away win rates, " +
      "biggest victories, and team rankings (best record / most goals). Filter by competition and season.",
    {
      competition: z.string().optional().describe("Competition name or fragment."),
      season: z.number().int().optional().describe("Season year."),
      mode: z
        .enum(["summary", "biggest_wins", "best_home", "best_away", "top_scorers", "most_wins"])
        .optional()
        .describe(
          "summary (default): goals/win-rate aggregates. biggest_wins: largest margins. " +
            "best_home/best_away: top win-rate by venue. top_scorers: most goals. most_wins: most wins."
        ),
      limit: z.number().int().positive().max(50).optional().describe("Rows for ranking modes (default 10)."),
      minMatches: z.number().int().optional().describe("Minimum matches for rate-based rankings (default 5)."),
    },
    async (args) => {
      const mode = args.mode ?? "summary";
      const limit = args.limit ?? 10;
      const scopeLabel = [args.competition, args.season ? String(args.season) : null]
        .filter(Boolean)
        .join(" ");

      // Pre-filter by competition/season for summary & biggest_wins.
      const scoped = searchMatches(matches, {
        competition: args.competition,
        season: args.season,
      });

      if (mode === "summary") {
        return text(formatAggregate(aggregateStats(scoped), `Match statistics${scopeLabel ? ` — ${scopeLabel}` : ""}`));
      }
      if (mode === "biggest_wins") {
        const wins = biggestWins(scoped, limit);
        const header = `Biggest victories${scopeLabel ? ` — ${scopeLabel}` : ""}:`;
        return text([header, ...wins.map((m, i) => `${i + 1}. ${formatMatch(m)}`)].join("\n"));
      }

      const venue = mode === "best_home" ? "home" : mode === "best_away" ? "away" : "all";
      const metric =
        mode === "top_scorers" ? "goalsFor" : mode === "most_wins" ? "wins" : "winRate";
      const rankings = rankTeams(matches, {
        competition: args.competition,
        season: args.season,
        venue,
        metric,
        minMatches: args.minMatches ?? (metric === "winRate" ? 5 : 1),
        limit,
      });
      const labels: Record<string, string> = {
        best_home: `Best home records${scopeLabel ? ` — ${scopeLabel}` : ""}`,
        best_away: `Best away records${scopeLabel ? ` — ${scopeLabel}` : ""}`,
        top_scorers: `Most goals scored${scopeLabel ? ` — ${scopeLabel}` : ""}`,
        most_wins: `Most wins${scopeLabel ? ` — ${scopeLabel}` : ""}`,
      };
      return text(formatTeamRankings(rankings, labels[mode], metric === "winRate"));
    }
  );

  return server;
}
