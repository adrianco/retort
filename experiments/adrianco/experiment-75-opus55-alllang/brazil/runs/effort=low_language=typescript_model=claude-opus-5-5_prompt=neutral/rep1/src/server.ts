#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { loadDataset } from "./data.js";
import { createHandlers } from "./tools.js";

const team = z.string().describe("Team name; variations like 'Palmeiras-SP', 'São Paulo', 'Sao Paulo' are normalized");
const competition = z.string().optional().describe("Brasileirão / Série A, Série B, Série C, Copa do Brasil, Libertadores");
const season = z.number().int().optional();
const venue = z.enum(["home", "away", "any"]).optional();
const limit = z.number().int().positive().optional();

export const TOOL_SCHEMAS: Record<string, { description: string; shape: z.ZodRawShape }> = {
  search_matches: { description: "Find matches by team, opponent, venue, competition, season, date range or stage (e.g. 'final').", shape: { team: team.optional(), opponent: team.optional(), venue, competition, season, dateFrom: z.string().optional().describe("YYYY-MM-DD"), dateTo: z.string().optional().describe("YYYY-MM-DD"), stage: z.string().optional(), limit } },
  head_to_head: { description: "Head-to-head record and match list between two teams.", shape: { teamA: team, teamB: team, competition, limit } },
  team_stats: { description: "Win/draw/loss and goals record for a team, optionally by season, competition and home/away.", shape: { team, season, competition, venue } },
  standings: { description: "League table for a season calculated from match results (champion and relegation marked).", shape: { season: z.number().int(), competition, top: limit } },
  competition_stats: { description: "Aggregate stats: average goals per match, home/away win rates, top scoring teams.", shape: { competition, season } },
  biggest_wins: { description: "Largest victory margins.", shape: { competition, season, team: team.optional(), limit } },
  best_records: { description: "Teams with the best home or away record (points per game).", shape: { venue: z.enum(["home", "away"]), competition, season, minMatches: z.number().int().optional(), limit } },
  team_competitions: { description: "Which competitions and seasons a team appears in.", shape: { team } },
  derbies: { description: "Traditional derby matches (Fla-Flu, Grenal, Derby Paulista...).", shape: { season, competition, limit } },
  search_players: { description: "Search FIFA players by name, nationality, club, position (e.g. ST or 'forward'), minimum overall.", shape: { name: z.string().optional(), nationality: z.string().optional(), club: z.string().optional(), position: z.string().optional(), minOverall: z.number().optional(), limit } },
  get_player: { description: "Detailed profile of a player by name.", shape: { name: z.string() } },
  brazilian_club_players: { description: "Summary of FIFA players at Brazilian (Brasileirão) clubs.", shape: { brazilianOnly: z.boolean().optional() } },
  team_profile: { description: "Cross-dataset team profile: all-time record, competitions, and FIFA players.", shape: { team } },
  dataset_info: { description: "List loaded datasets and row counts.", shape: {} },
};

export function buildServer() {
  const handlers = createHandlers(loadDataset());
  const server = new McpServer({ name: "brazilian-soccer", version: "1.0.0" });
  for (const [name, { description, shape }] of Object.entries(TOOL_SCHEMAS)) {
    server.tool(name, description, shape, async (args: Record<string, unknown>) => {
      try {
        return { content: [{ type: "text" as const, text: handlers[name](args) }] };
      } catch (e) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    });
  }
  return server;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split("/").pop()!)) {
  await buildServer().connect(new StdioServerTransport());
}
