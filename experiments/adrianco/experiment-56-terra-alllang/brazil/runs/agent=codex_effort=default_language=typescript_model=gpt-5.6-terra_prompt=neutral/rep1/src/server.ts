import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { SoccerData } from "./soccer-data.js";

const text = (value: unknown) => ({ content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }] });
const optionalFilters = {
  competition: z.string().optional().describe("Competition name, e.g. Brasileirão"),
  season: z.number().int().optional().describe("Season year"),
};

/** Creates a stdio-ready MCP server. Data is read once at startup for fast queries. */
export function createServer(dataDir: string): McpServer {
  const data = new SoccerData(dataDir);
  const server = new McpServer({ name: "brazilian-soccer", version: "1.0.0" });

  server.tool("search_matches", "Find matches by team, opponent, date, competition, season, or tournament stage.", {
    team: z.string().optional(), opponent: z.string().optional(), ...optionalFilters,
    from: z.string().optional().describe("Inclusive ISO date (YYYY-MM-DD)"),
    to: z.string().optional().describe("Inclusive ISO date (YYYY-MM-DD)"),
    stage: z.string().optional(), limit: z.number().int().min(1).max(500).optional()
  }, (input) => text(data.findMatches(input)));

  server.tool("team_statistics", "Calculate wins, draws, losses, goals, points and win rate for a team.", {
    team: z.string(), ...optionalFilters, homeOnly: z.boolean().optional().describe("Only count home matches")
  }, (input) => text(data.teamStatistics(input.team, input)));

  server.tool("head_to_head", "Compare two teams and return their meetings and win/draw totals.", {
    teamA: z.string(), teamB: z.string(), ...optionalFilters
  }, (input) => { const result = data.headToHead(input.teamA, input.teamB, input); return text({ ...result, matches: result.matches.slice(0, 100) }); });

  server.tool("search_players", "Search FIFA players by name, nationality, club, or position. Results are rating-sorted.", {
    name: z.string().optional(), nationality: z.string().optional(), club: z.string().optional(), position: z.string().optional(), limit: z.number().int().min(1).max(200).optional()
  }, (input) => text(data.searchPlayers(input)));

  server.tool("competition_standings", "Calculate a league table from match results for a season.", {
    season: z.number().int(), competition: z.string().optional().describe("Defaults to Brasileirão")
  }, (input) => text(data.standings(input.season, input.competition)));

  server.tool("dataset_summary", "Return source coverage and aggregate scoring statistics.", {}, () => {
    const byCompetition = new Map<string, number>();
    for (const match of data.matches) byCompetition.set(match.competition, (byCompetition.get(match.competition) ?? 0) + 1);
    const totalGoals = data.matches.reduce((sum, m) => sum + m.homeGoals + m.awayGoals, 0);
    return text({ matches: data.matches.length, players: data.players.length, sources: [...new Set(data.matches.map((m) => m.source)), "fifa_data.csv"], matchesByCompetition: Object.fromEntries(byCompetition), averageGoalsPerMatch: Number((totalGoals / data.matches.length).toFixed(2)) });
  });
  return server;
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  const dataDir = process.env.SOCCER_DATA_DIR ?? join(dirname(fileURLToPath(import.meta.url)), "../data/kaggle");
  const server = createServer(dataDir);
  await server.connect(new StdioServerTransport());
}
