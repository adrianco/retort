import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

import { NaturalLanguageQueryRouter } from "./query-router.js";
import { SoccerService } from "./soccer-service.js";
import type { QueryResult } from "./types.js";

function toolResponse(result: QueryResult): CallToolResult {
  return {
    content: [{ type: "text" as const, text: result.formatted }],
    structuredContent: {
      kind: result.kind,
      summary: result.summary,
      data: result.data,
      ...(result.limitations ? { limitations: result.limitations } : {}),
    },
  };
}

function register(
  server: McpServer,
  name: string,
  description: string,
  shape: Record<string, z.ZodType>,
  handler: (input: Record<string, any>) => QueryResult | Promise<QueryResult>,
): void {
  server.tool(name, description, shape, async (input): Promise<CallToolResult> => {
    try {
      return toolResponse(await handler(input));
    } catch (error) {
      return {
        isError: true,
        content: [{ type: "text" as const, text: error instanceof Error ? error.message : String(error) }],
      };
    }
  });
}

export function createSoccerMcpServer(service: SoccerService): McpServer {
  const server = new McpServer({ name: "brazilian-soccer", version: "1.0.0" });
  const router = new NaturalLanguageQueryRouter(service);

  register(server, "ask_soccer", "Answer a natural-language question about Brazilian soccer matches, teams, players, competitions, standings, or statistics.", {
    question: z.string().min(2).describe("Natural-language soccer question"),
  }, ({ question }) => router.answer(question));

  register(server, "search_matches", "Find matches by team, opponent, competition, season, date range, stage, and home/away venue.", {
    team: z.string().optional(),
    opponent: z.string().optional(),
    competition: z.string().optional(),
    season: z.number().int().min(1900).max(2100).optional(),
    dateFrom: z.string().optional().describe("YYYY-MM-DD or DD/MM/YYYY"),
    dateTo: z.string().optional().describe("YYYY-MM-DD or DD/MM/YYYY"),
    stage: z.string().optional(),
    venue: z.enum(["home", "away", "either"]).optional(),
    limit: z.number().int().min(1).max(200).optional(),
  }, (input) => service.searchMatches(input));

  register(server, "get_head_to_head", "Compare two teams and return their win/draw record plus recent meetings.", {
    team1: z.string(),
    team2: z.string(),
    competition: z.string().optional(),
    season: z.number().int().optional(),
    limit: z.number().int().min(1).max(200).optional(),
  }, ({ team1, team2, ...options }) => service.headToHead(team1, team2, options));

  register(server, "get_team_statistics", "Calculate a team's wins, draws, losses, goals, points, and win rate for an optional season, competition, and venue.", {
    team: z.string(),
    competition: z.string().optional(),
    season: z.number().int().optional(),
    venue: z.enum(["home", "away", "either"]).optional(),
  }, ({ team, ...options }) => service.teamStatistics(team, options));

  register(server, "get_team_profile", "Traverse team relationships across match and FIFA player data, returning competitions, aggregate record, and club players.", {
    team: z.string(),
    season: z.number().int().optional(),
  }, ({ team, season }) => service.teamProfile(team, season));

  register(server, "search_players", "Search FIFA players by name, nationality, club, position group, and minimum overall rating.", {
    name: z.string().optional(),
    nationality: z.string().optional(),
    club: z.string().optional(),
    position: z.string().optional(),
    minOverall: z.number().min(0).max(100).optional(),
    limit: z.number().int().min(1).max(250).optional(),
  }, (input) => service.searchPlayers(input));

  register(server, "get_standings", "Calculate final standings from match results using points, wins, goal difference, and goals scored.", {
    season: z.number().int().min(1900).max(2100),
    competition: z.string().default("Brasileirão"),
  }, ({ season, competition }) => service.standings(season, competition));

  register(server, "get_competition_statistics", "Calculate goals per match, home/away results, home win rate, and biggest victories.", {
    competition: z.string().optional(),
    season: z.number().int().optional(),
    limit: z.number().int().min(1).max(50).optional(),
  }, (input) => service.competitionStatistics(input));

  register(server, "get_derbies", "Find matches between a curated set of traditional Brazilian rivals.", {
    season: z.number().int().optional(),
    limit: z.number().int().min(1).max(200).optional(),
  }, ({ season, limit }) => service.derbies(season, limit));

  register(server, "get_dataset_summary", "Report loaded match, player, team, competition, and source coverage.", {}, () => {
    const data = service.graph.summary();
    return {
      kind: "dataset-summary",
      summary: "Loaded soccer dataset coverage",
      data,
      formatted: `Loaded ${data.matches} deduplicated matches, ${data.players} players, ${data.teams} teams, and ${data.competitions} competitions from all six required CSV files.`,
    };
  });

  return server;
}
