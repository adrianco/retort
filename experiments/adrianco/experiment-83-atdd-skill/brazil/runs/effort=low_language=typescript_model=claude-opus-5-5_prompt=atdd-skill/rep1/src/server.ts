import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { Dataset } from "./data.js";
import * as q from "./queries.js";

const venue = z.enum(["home", "away", "all"]).optional();

export function createServer(ds: Dataset): McpServer {
  const server = new McpServer({ name: "brazilian-soccer", version: "1.0.0" });
  const tool = (name: string, description: string, shape: z.ZodRawShape, fn: (a: any) => string) =>
    server.tool(name, description, shape, async (args: any) => {
      try { return { content: [{ type: "text" as const, text: fn(args) }] }; }
      catch (e) { return { isError: true, content: [{ type: "text" as const, text: (e as Error).message }] }; }
    });

  tool("search_matches", "Find matches by team, opponent, venue, season, competition (Brasileirão, Copa do Brasil, Libertadores, Serie B, Serie C), stage (e.g. final) or date range (YYYY-MM-DD).",
    { team: z.string().optional(), opponent: z.string().optional(), venue, season: z.number().int().optional(), competition: z.string().optional(),
      stage: z.string().optional(), from: z.string().optional(), to: z.string().optional(), limit: z.number().int().optional() },
    a => q.searchMatches(ds, a));
  tool("last_meeting", "Most recent match between two teams, with score.", { team: z.string(), opponent: z.string() }, a => q.lastMeeting(ds, a.team, a.opponent));
  tool("head_to_head", "Head-to-head record between two teams across all competitions.", { team: z.string(), opponent: z.string() }, a => q.headToHead(ds, a.team, a.opponent));
  tool("team_record", "Win/draw/loss and goals record for a team, optionally by season, venue and competition.",
    { team: z.string(), season: z.number().int().optional(), venue, competition: z.string().optional() }, a => q.teamRecord(ds, a.team, a));
  tool("team_competitions", "Competitions a team has played in according to the datasets.", { team: z.string() }, a => q.teamCompetitions(ds, a.team));
  tool("standings", "Brasileirão league table for a season, calculated from match results, with champion and relegated teams.",
    { season: z.number().int() }, a => q.standings(ds, a.season));
  tool("top_scoring_teams", "Teams that scored the most goals in the Brasileirão (optionally per season).",
    { season: z.number().int().optional(), limit: z.number().int().optional() }, a => q.topScoringTeams(ds, a.season, a.limit));
  tool("competition_stats", "Aggregate statistics: average goals per match, home/draw/away rates.",
    { competition: z.string().optional(), season: z.number().int().optional() }, a => q.competitionStats(ds, a.competition, a.season));
  tool("compare_seasons", "Compare aggregate statistics between seasons.", { seasons: z.array(z.number().int()), competition: z.string().optional() },
    a => q.compareSeasons(ds, a.seasons, a.competition));
  tool("biggest_wins", "Largest margins of victory.", { competition: z.string().optional(), season: z.number().int().optional(), team: z.string().optional(),
    limit: z.number().int().optional() }, a => q.biggestWins(ds, a));
  tool("best_record", "Rank teams by home, away or overall win rate.", { venue, season: z.number().int().optional(), competition: z.string().optional(),
    minMatches: z.number().int().optional(), limit: z.number().int().optional() }, a => q.bestRecord(ds, a));
  tool("derbies", "Matches between traditional rivals (Fla-Flu, Derby Paulista, Gre-Nal, ...).", { season: z.number().int().optional() }, a => q.derbies(ds, a.season));
  tool("search_players", "Search FIFA player data by name, nationality, club, position (or 'forward') and minimum rating; sorted by overall rating.",
    { name: z.string().optional(), nationality: z.string().optional(), club: z.string().optional(), position: z.string().optional(),
      minOverall: z.number().int().optional(), limit: z.number().int().optional() }, a => q.searchPlayers(ds, a));
  tool("dataset_info", "Describe the loaded datasets.", {}, () => q.datasetInfo(ds));
  return server;
}
