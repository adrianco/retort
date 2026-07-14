#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { getDataStore } from "./dataStore.js";
import { findMatches, headToHead, lastMatchBetween } from "./queries/matches.js";
import { teamStats, teamCompetitions, teamRecentMatches, listTeams } from "./queries/teams.js";
import { findPlayers, topBrazilianPlayers } from "./queries/players.js";
import { standings, champion, relegated, listCompetitions, listSeasons } from "./queries/competitions.js";
import { aggregateStats, biggestWins, topScoringTeams, bestRecord } from "./queries/stats.js";
import {
  formatMatches, formatMatch, formatTeamRecord, formatHeadToHead,
  formatStandings, formatPlayers,
} from "./formatters.js";

function textResult(text: string) {
  return { content: [{ type: "text" as const, text }] };
}

export function buildServer(): McpServer {
  const ds = getDataStore();
  const server = new McpServer(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    { capabilities: { tools: {} } },
  );

  server.registerTool(
    "find_matches",
    {
      title: "Find matches",
      description:
        "Find matches by team, opponent, competition, season, or date range. " +
        "Searches Brasileirão, Copa do Brasil, Copa Libertadores, BR-Football extended stats, and historical Brasileirão.",
      inputSchema: {
        team: z.string().optional(),
        opponent: z.string().optional(),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
        dateFrom: z.string().optional(),
        dateTo: z.string().optional(),
        round: z.string().optional(),
        stage: z.string().optional(),
        limit: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      const ms = findMatches(ds.matches, { ...args, limit: args.limit ?? 50 });
      const header = `Found ${ms.length} match(es).`;
      return textResult(header + (ms.length ? "\n" + formatMatches(ms, 50) : ""));
    },
  );

  server.registerTool(
    "team_stats",
    {
      title: "Team statistics",
      description: "Aggregate wins/draws/losses/goals for a team across competitions, seasons, and home/away.",
      inputSchema: {
        team: z.string(),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
        venue: z.enum(["home", "away", "any"]).optional(),
      },
    },
    async (args) => {
      const stats = teamStats(ds.matches, args);
      const ctx: string[] = [];
      if (args.competition) ctx.push(args.competition);
      if (args.season !== undefined) ctx.push(String(args.season));
      if (args.venue && args.venue !== "any") ctx.push(`${args.venue} only`);
      const title = `${args.team}${ctx.length ? " (" + ctx.join(", ") + ")" : ""}`;
      return textResult(formatTeamRecord(stats, title));
    },
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head",
      description: "Head-to-head record and matches between two teams.",
      inputSchema: {
        teamA: z.string(),
        teamB: z.string(),
        competition: z.string().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
        showMatches: z.boolean().optional(),
      },
    },
    async (args) => {
      const { matches, summary } = headToHead(ds.matches, args.teamA, args.teamB, args);
      let text = formatHeadToHead(summary);
      if (args.showMatches) text += "\n\nMatches:\n" + formatMatches(matches, 20);
      return textResult(text);
    },
  );

  server.registerTool(
    "last_match_between",
    {
      title: "Last match between two teams",
      description: "Returns the most recent match between two teams (any competition).",
      inputSchema: { teamA: z.string(), teamB: z.string() },
    },
    async ({ teamA, teamB }) => {
      const m = lastMatchBetween(ds.matches, teamA, teamB);
      if (!m) return textResult(`No matches between ${teamA} and ${teamB} found.`);
      return textResult(formatMatch(m));
    },
  );

  server.registerTool(
    "team_competitions",
    {
      title: "Competitions a team played",
      description: "List the competitions that contain matches involving the team.",
      inputSchema: { team: z.string() },
    },
    async ({ team }) => {
      const comps = teamCompetitions(ds.matches, team);
      if (comps.length === 0) return textResult(`No competitions found for ${team}.`);
      return textResult(`${team} has played in:\n- ${comps.join("\n- ")}`);
    },
  );

  server.registerTool(
    "team_recent_matches",
    {
      title: "Recent matches",
      description: "Most recent N matches involving a team.",
      inputSchema: {
        team: z.string(),
        limit: z.number().int().positive().optional(),
      },
    },
    async ({ team, limit }) => {
      const ms = teamRecentMatches(ds.matches, team, limit ?? 10);
      return textResult(`Recent matches for ${team}:\n` + formatMatches(ms));
    },
  );

  server.registerTool(
    "list_teams",
    {
      title: "List teams",
      description: "List all distinct team names across the loaded match data.",
      inputSchema: { contains: z.string().optional() },
    },
    async ({ contains }) => {
      let teams = listTeams(ds.matches);
      if (contains) {
        const q = contains.toLowerCase();
        teams = teams.filter((t) => t.toLowerCase().includes(q));
      }
      return textResult(`Teams (${teams.length}):\n` + teams.slice(0, 200).join("\n"));
    },
  );

  server.registerTool(
    "find_players",
    {
      title: "Find FIFA players",
      description: "Search FIFA player database by name, nationality, club, or position.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().optional(),
        maxAge: z.number().int().optional(),
        sortBy: z.enum(["overall", "potential", "age", "name"]).optional(),
        sortDir: z.enum(["asc", "desc"]).optional(),
        limit: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      const players = findPlayers(ds.players, { ...args, limit: args.limit ?? 25 });
      return textResult(`Found ${players.length} player(s):\n` + formatPlayers(players, 25));
    },
  );

  server.registerTool(
    "top_brazilian_players",
    {
      title: "Top Brazilian players",
      description: "Top-N Brazilian players in the FIFA database sorted by Overall rating.",
      inputSchema: { limit: z.number().int().positive().optional() },
    },
    async ({ limit }) => {
      const players = topBrazilianPlayers(ds.players, limit ?? 10);
      return textResult(`Top Brazilian players:\n` + formatPlayers(players));
    },
  );

  server.registerTool(
    "standings",
    {
      title: "Competition standings",
      description: "Compute final-table standings for a competition + season from match results.",
      inputSchema: {
        competition: z.string(),
        season: z.number().int(),
        limit: z.number().int().positive().optional(),
      },
    },
    async ({ competition, season, limit }) => {
      const rows = standings(ds.matches, { competition, season });
      const sliced = limit ? rows.slice(0, limit) : rows;
      return textResult(
        `${competition} ${season} standings (computed from matches):\n` +
          formatStandings(sliced),
      );
    },
  );

  server.registerTool(
    "champion",
    {
      title: "Season champion",
      description: "Returns the top team of a competition/season by points.",
      inputSchema: { competition: z.string(), season: z.number().int() },
    },
    async ({ competition, season }) => {
      const c = champion(ds.matches, { competition, season });
      if (!c) return textResult(`No matches found for ${competition} ${season}.`);
      return textResult(`${competition} ${season} champion: ${c.team} (${c.points} pts, ${c.wins}W ${c.draws}D ${c.losses}L)`);
    },
  );

  server.registerTool(
    "relegated",
    {
      title: "Relegated teams",
      description: "Bottom-N teams of a season's standings (default 4).",
      inputSchema: {
        competition: z.string(),
        season: z.number().int(),
        count: z.number().int().positive().optional(),
      },
    },
    async ({ competition, season, count }) => {
      const rows = relegated(ds.matches, { competition, season }, count ?? 4);
      if (rows.length === 0) return textResult(`No standings found for ${competition} ${season}.`);
      return textResult(
        `${competition} ${season} bottom ${rows.length} teams:\n` + formatStandings(rows),
      );
    },
  );

  server.registerTool(
    "list_competitions",
    {
      title: "List competitions",
      description: "Distinct competition labels across the loaded match data.",
      inputSchema: {},
    },
    async () => textResult(listCompetitions(ds.matches).join("\n")),
  );

  server.registerTool(
    "list_seasons",
    {
      title: "List seasons",
      description: "Seasons present in the data (optionally for a given competition).",
      inputSchema: { competition: z.string().optional() },
    },
    async ({ competition }) => textResult(listSeasons(ds.matches, competition).join(", ")),
  );

  server.registerTool(
    "aggregate_stats",
    {
      title: "Aggregate stats",
      description: "Average goals/match, home win rate, etc.",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
      },
    },
    async (args) => {
      const s = aggregateStats(ds.matches, args);
      return textResult([
        `Matches analyzed: ${s.matches}`,
        `Total goals: ${s.totalGoals}`,
        `Average goals/match: ${s.averageGoalsPerMatch.toFixed(2)}`,
        `Home wins: ${s.homeWins} (${(s.homeWinRate * 100).toFixed(1)}%)`,
        `Away wins: ${s.awayWins} (${(s.awayWinRate * 100).toFixed(1)}%)`,
        `Draws: ${s.draws} (${(s.drawRate * 100).toFixed(1)}%)`,
      ].join("\n"));
    },
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description: "Largest goal-margin matches (optionally filtered by competition/season).",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      const ms = biggestWins(ds.matches, { ...args, limit: args.limit ?? 10 });
      return textResult("Biggest victories:\n" + formatMatches(ms));
    },
  );

  server.registerTool(
    "top_scoring_teams",
    {
      title: "Top scoring teams",
      description: "Teams with most goals scored (filterable by competition/season).",
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      const rows = topScoringTeams(ds.matches, { ...args, limit: args.limit ?? 10 });
      return textResult(rows.map((r, i) =>
        `${i + 1}. ${r.team} — ${r.goalsFor} goals in ${r.matches} matches`
      ).join("\n"));
    },
  );

  server.registerTool(
    "best_record",
    {
      title: "Best home/away record",
      description: "Teams with best home or away win rate.",
      inputSchema: {
        venue: z.enum(["home", "away"]),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().optional(),
        minMatches: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      const rows = bestRecord(ds.matches, args.venue, args);
      return textResult(`Best ${args.venue} records:\n` +
        rows.map((r, i) =>
          `${i + 1}. ${r.team} — ${r.wins}W ${r.draws}D ${r.losses}L (${(r.winRate * 100).toFixed(1)}%)`
        ).join("\n"));
    },
  );

  return server;
}

async function main(): Promise<void> {
  const server = buildServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

// Run only when invoked directly.
const isMain =
  // ESM check: argv[1] is the launched file.
  typeof process !== "undefined" &&
  process.argv[1] &&
  import.meta.url === new URL("file://" + process.argv[1]).href;

if (isMain) {
  main().catch((err) => {
    console.error("[brazilian-soccer-mcp] fatal:", err);
    process.exit(1);
  });
}
