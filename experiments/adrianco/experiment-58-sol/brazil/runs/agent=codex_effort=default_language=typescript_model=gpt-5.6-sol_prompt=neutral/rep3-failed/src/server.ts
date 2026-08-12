import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { SoccerDataStore, type DataStoreOptions } from "./data-store.js";
import { formatMatches, formatPlayers, formatStandings, formatTeamStats } from "./format.js";
import { NaturalLanguageQuery } from "./query.js";
import { SoccerService } from "./service.js";

function result(text: string, data: unknown) {
  return {
    content: [{ type: "text" as const, text }],
    structuredContent: JSON.parse(JSON.stringify(data)) as Record<string, unknown>
  };
}

const matchFilterShape = {
  team: z.string().optional().describe("Team playing either home or away; accents and state suffixes are optional"),
  opponent: z.string().optional().describe("Second team for a head-to-head pairing; requires team"),
  homeTeam: z.string().optional(),
  awayTeam: z.string().optional(),
  competition: z.string().optional().describe("Brasileirão, Copa do Brasil, Libertadores, or another dataset competition"),
  season: z.number().int().optional(),
  from: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  to: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  round: z.string().optional(),
  stage: z.string().optional(),
  finals: z.boolean().optional().describe("Select final-stage matches or the highest numbered cup round per season"),
  limit: z.number().int().min(1).max(200).default(25),
  offset: z.number().int().min(0).default(0),
  newestFirst: z.boolean().default(true)
};

export async function createServer(options: DataStoreOptions = {}): Promise<McpServer> {
  const store = await SoccerDataStore.load(options);
  const service = new SoccerService(store);
  const naturalLanguage = new NaturalLanguageQuery(service);
  const server = new McpServer(
    { name: "brazilian-soccer", version: "1.0.0" },
    { instructions: "Use answer_question for natural-language requests or a focused tool when the desired operation is known. All answers come from the bundled historical datasets, not live results." }
  );

  server.registerTool("dataset_summary", {
    title: "Brazilian soccer dataset summary",
    description: "Report loaded row counts, seasons, sources, and competitions",
    inputSchema: z.object({}),
    annotations: { readOnlyHint: true, idempotentHint: true }
  }, async () => result(`Loaded ${store.summary.matches} unique matches and ${store.summary.players} players from all six CSV files.`, store.summary));

  server.registerTool("search_matches", {
    title: "Search matches",
    description: "Find matches by team, opponent, home/away team, competition, season, date range, round, or stage",
    inputSchema: z.object(matchFilterShape),
    annotations: { readOnlyHint: true, idempotentHint: true }
  }, async (args) => {
    const data = service.searchMatches(args);
    return result(formatMatches(data.items, data.total), data);
  });

  server.registerTool("team_statistics", {
    title: "Team statistics",
    description: "Calculate wins, draws, losses, goals, points, and win rate for a team",
    inputSchema: z.object({
      team: z.string(), competition: z.string().optional(), season: z.number().int().optional(),
      from: z.string().optional(), to: z.string().optional(), venue: z.enum(["home", "away", "all"]).default("all")
    }),
    annotations: { readOnlyHint: true, idempotentHint: true }
  }, async ({ team, ...filter }) => {
    const data = service.teamStats(team, filter);
    return result(formatTeamStats(data), data);
  });

  server.registerTool("head_to_head", {
    title: "Head-to-head comparison",
    description: "Compare two teams and return their meetings and win/draw totals",
    inputSchema: z.object({ teamA: z.string(), teamB: z.string(), competition: z.string().optional(), season: z.number().int().optional(), limit: z.number().int().min(1).max(200).default(50) }),
    annotations: { readOnlyHint: true, idempotentHint: true }
  }, async ({ teamA, teamB, ...filter }) => {
    const data = service.headToHead(teamA, teamB, filter);
    return result(`${teamA}: ${data.teamAWins} wins; ${teamB}: ${data.teamBWins} wins; draws: ${data.draws}.\n${formatMatches(data.results, data.matches)}`, data);
  });

  server.registerTool("search_players", {
    title: "Search FIFA players",
    description: "Search and rank players by name, nationality, club, position, overall, or potential",
    inputSchema: z.object({
      name: z.string().optional(), nationality: z.string().optional(), club: z.string().optional(), position: z.string().optional(),
      minOverall: z.number().min(0).max(100).optional(), minPotential: z.number().min(0).max(100).optional(),
      limit: z.number().int().min(1).max(200).default(25), offset: z.number().int().min(0).default(0)
    }),
    annotations: { readOnlyHint: true, idempotentHint: true }
  }, async (args) => {
    const data = service.searchPlayers(args);
    return result(formatPlayers(data.items, data.total), data);
  });

  server.registerTool("calculate_standings", {
    title: "Calculate standings",
    description: "Calculate a season table from match results using points, wins, goal difference, and goals scored",
    inputSchema: z.object({ season: z.number().int(), competition: z.string().default("Brasileirão Serie A"), limit: z.number().int().min(1).max(100).default(30) }),
    annotations: { readOnlyHint: true, idempotentHint: true }
  }, async ({ season, competition, limit }) => {
    const data = service.standings(season, competition).slice(0, limit);
    return result(formatStandings(data), data);
  });

  server.registerTool("competition_summary", {
    title: "Competition summary",
    description: "Summarize a competition, its teams, rounds or stages, date span, and calculated table",
    inputSchema: z.object({ competition: z.string(), season: z.number().int().optional() }),
    annotations: { readOnlyHint: true, idempotentHint: true }
  }, async ({ competition, season }) => {
    const data = service.competitionSummary(competition, season);
    return result(`${data.competition}${season ? ` ${season}` : ""}: ${data.matches} matches, ${data.teams} teams.${data.champion ? ` Calculated leader: ${data.champion}.` : ""}`, data);
  });

  server.registerTool("analyze_statistics", {
    title: "Analyze match statistics",
    description: "Calculate goal averages, home/away outcomes, and biggest victories",
    inputSchema: z.object({ competition: z.string().optional(), season: z.number().int().optional(), team: z.string().optional(), from: z.string().optional(), to: z.string().optional(), limit: z.number().int().min(1).max(50).default(10) }),
    annotations: { readOnlyHint: true, idempotentHint: true }
  }, async (args) => {
    const data = service.statistics(args);
    return result(`${data.matches} matches; ${data.averageGoals} goals per match; home wins ${data.homeWinRate}%, away wins ${data.awayWinRate}%, draws ${data.drawRate}%.\n${formatMatches(data.biggestVictories)}`, data);
  });

  server.registerTool("explore_relationships", {
    title: "Explore soccer relationships",
    description: "Return graph-shaped nodes and edges linking a team to competitions, opponents, and FIFA players",
    inputSchema: z.object({ team: z.string(), season: z.number().int().optional() }),
    annotations: { readOnlyHint: true, idempotentHint: true }
  }, async ({ team, season }) => {
    const data = service.relationships(team, season);
    return result(`${team}: ${data.counts.matches} matches, ${data.counts.opponents} opponents, ${data.counts.competitions} competitions, and ${data.counts.players} linked FIFA players.`, data);
  });

  server.registerTool("answer_question", {
    title: "Answer a Brazilian soccer question",
    description: "Interpret a natural-language question and answer it from the bundled match and FIFA datasets",
    inputSchema: z.object({ question: z.string().min(2) }),
    annotations: { readOnlyHint: true, idempotentHint: true }
  }, async ({ question }) => {
    const data = naturalLanguage.answer(question);
    return result(data.note ? `${data.answer}\n\nNote: ${data.note}` : data.answer, data as unknown as Record<string, unknown>);
  });

  return server;
}
