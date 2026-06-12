/**
 * MCP server definition: the public interface of the Brazilian Soccer knowledge
 * base. Each tool maps a natural-language query category from TASK.md onto a
 * DataStore query and returns a structured JSON result (plus a human-readable
 * `summary`) so an LLM client can both reason over and present the answer.
 *
 * The server is intentionally a thin adapter — all querying/aggregation lives in
 * DataStore — which keeps the tools easy to reason about and test.
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import type { DataStore } from './data/store.js';
import type { Match } from './domain/types.js';

function matchView(m: Match) {
  return {
    date: m.date,
    competition: m.competition,
    season: m.season,
    round: m.round ?? null,
    homeTeam: m.homeTeam,
    awayTeam: m.awayTeam,
    homeGoals: m.homeGoals,
    awayGoals: m.awayGoals,
    stadium: m.stadium ?? null,
    score: `${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam}`,
  };
}

/** Wrap a structured payload as an MCP tool result (text + structuredContent). */
function ok(payload: unknown) {
  return {
    content: [{ type: 'text' as const, text: JSON.stringify(payload, null, 2) }],
    structuredContent: payload as Record<string, unknown>,
  };
}

export function createSoccerServer(store: DataStore): McpServer {
  const server = new McpServer(
    { name: 'brazilian-soccer-mcp', version: '1.0.0' },
    {
      instructions:
        'Knowledge base of Brazilian soccer matches (Brasileirão, Copa do Brasil, ' +
        'Libertadores and more) and FIFA player data. Use the tools to find matches, ' +
        'team records, head-to-head histories, players, league standings and statistics.',
    },
  );

  // 1. Match queries -------------------------------------------------------
  server.registerTool(
    'find_matches',
    {
      title: 'Find matches',
      description:
        'Find matches by team (home/away/either), opponent, competition, season or date range. ' +
        'Team names are matched ignoring state suffixes ("Palmeiras-SP" = "Palmeiras") and accents.',
      inputSchema: {
        team: z.string().optional().describe('A team that played in the match (home or away).'),
        opponent: z.string().optional().describe('Restrict to matches against this opponent.'),
        homeTeam: z.string().optional().describe('Only matches with this team at home.'),
        awayTeam: z.string().optional().describe('Only matches with this team away.'),
        competition: z.string().optional().describe('e.g. "Brasileirão", "Copa do Brasil", "Libertadores".'),
        stage: z.string().optional().describe('Round/stage, e.g. "final", "group stage" (whole-word match).'),
        season: z.number().int().optional().describe('Season year, e.g. 2023.'),
        dateFrom: z.string().optional().describe('Inclusive start date (YYYY-MM-DD).'),
        dateTo: z.string().optional().describe('Inclusive end date (YYYY-MM-DD).'),
        limit: z.number().int().positive().optional().describe('Max matches to return (default 50).'),
      },
    },
    async (args) => {
      const limit = args.limit ?? 50;
      const found = store.findMatches(args);
      const matches = found.slice(0, limit).map(matchView);
      return ok({
        count: found.length,
        returned: matches.length,
        matches,
        summary:
          found.length === 0
            ? 'No matches found for the given criteria.'
            : `Found ${found.length} match(es)${found.length > matches.length ? `, showing ${matches.length}` : ''}.`,
      });
    },
  );

  // 2. Head-to-head --------------------------------------------------------
  server.registerTool(
    'head_to_head',
    {
      title: 'Head-to-head record',
      description: 'Summarise the head-to-head record (wins/draws/goals) between two teams.',
      inputSchema: {
        team1: z.string().describe('First team.'),
        team2: z.string().describe('Second team.'),
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const h = store.headToHead(args);
      return ok({
        team1: h.team1,
        team2: h.team2,
        totalMatches: h.totalMatches,
        team1Wins: h.team1Wins,
        team2Wins: h.team2Wins,
        draws: h.draws,
        team1Goals: h.team1Goals,
        team2Goals: h.team2Goals,
        matches: h.matches.map(matchView),
        summary: `${h.team1} vs ${h.team2}: ${h.team1Wins} wins, ${h.team2Wins} wins, ${h.draws} draws over ${h.totalMatches} matches.`,
      });
    },
  );

  // 3. Team record ---------------------------------------------------------
  server.registerTool(
    'team_record',
    {
      title: 'Team record',
      description:
        'Compute a team\'s record (wins, draws, losses, goals for/against, points, win rate). ' +
        'Optionally restrict by season, competition and venue (home/away/all).',
      inputSchema: {
        team: z.string().describe('The team to report on.'),
        season: z.number().int().optional(),
        competition: z.string().optional(),
        venue: z.enum(['home', 'away', 'all']).optional().describe('Default "all".'),
      },
    },
    async (args) => {
      const r = store.teamRecord(args);
      return ok({
        ...r,
        summary: `${r.team}: ${r.matches} matches, ${r.wins}W ${r.draws}D ${r.losses}L, ` +
          `GF ${r.goalsFor} GA ${r.goalsAgainst}, ${r.points} pts, win rate ${r.winRate}%.`,
      });
    },
  );

  // 4. Player queries ------------------------------------------------------
  server.registerTool(
    'find_players',
    {
      title: 'Find players',
      description:
        'Search FIFA player data by name, nationality, club or position, with optional minimum ' +
        'rating. Sort by overall/potential/age/name. Accent-insensitive.',
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional().describe('e.g. "Brazil".'),
        club: z.string().optional(),
        position: z.string().optional().describe('e.g. "ST", "GK", "CDM".'),
        minOverall: z.number().int().optional(),
        sortBy: z.enum(['overall', 'potential', 'age', 'name']).optional().describe('Default "overall".'),
        limit: z.number().int().positive().optional().describe('Max players to return (default 25).'),
      },
    },
    async (args) => {
      const limit = args.limit ?? 25;
      const all = store.findPlayers({ ...args, limit: undefined });
      const players = all.slice(0, limit).map((p) => ({
        id: p.id,
        name: p.name,
        age: p.age ?? null,
        nationality: p.nationality ?? null,
        overall: p.overall ?? null,
        potential: p.potential ?? null,
        club: p.club ?? null,
        position: p.position ?? null,
        jerseyNumber: p.jerseyNumber ?? null,
      }));
      return ok({
        count: all.length,
        returned: players.length,
        players,
        summary:
          all.length === 0
            ? 'No players matched the given criteria.'
            : `Found ${all.length} player(s)${all.length > players.length ? `, showing ${players.length}` : ''}.`,
      });
    },
  );

  // 5. Competition standings ----------------------------------------------
  server.registerTool(
    'competition_standings',
    {
      title: 'Competition standings',
      description:
        'Calculate the final league table for a competition and season from match results ' +
        '(3 points for a win, 1 for a draw). Returns ordered standings and the champion.',
      inputSchema: {
        competition: z.string().describe('e.g. "Brasileirão".'),
        season: z.number().int().describe('Season year, e.g. 2019.'),
      },
    },
    async (args) => {
      const standings = store.standings(args);
      return ok({
        competition: args.competition,
        season: args.season,
        teams: standings.length,
        champion: standings[0]?.team ?? null,
        standings,
        summary:
          standings.length === 0
            ? `No matches found for ${args.competition} ${args.season}.`
            : `${standings[0].team} finished top of ${args.competition} ${args.season} with ${standings[0].points} points.`,
      });
    },
  );

  // 6. Competition / statistical analysis ---------------------------------
  server.registerTool(
    'competition_statistics',
    {
      title: 'Competition statistics',
      description:
        'Aggregate statistics across matches: average goals per match, home/away win rates, ' +
        'draw rate, and the biggest victories. Optionally scope by competition and/or season.',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const s = store.competitionStatistics(args);
      return ok({
        ...s,
        summary: `${s.matches} matches, ${s.averageGoalsPerMatch} goals/match, ` +
          `home win rate ${s.homeWinRate}%, away ${s.awayWinRate}%, draws ${s.drawRate}%.`,
      });
    },
  );

  // Dataset summary (coverage / introspection) ----------------------------
  server.registerTool(
    'dataset_summary',
    {
      title: 'Dataset summary',
      description: 'Report what data is loaded: total matches, players, competitions and seasons covered.',
      inputSchema: {},
    },
    async () => {
      const seasons = store.seasons();
      return ok({
        totalMatches: store.matchCount,
        totalPlayers: store.playerCount,
        competitions: store.competitions(),
        seasonsFrom: seasons[0] ?? null,
        seasonsTo: seasons[seasons.length - 1] ?? null,
        summary: `${store.matchCount} matches and ${store.playerCount} players loaded across ${store.competitions().length} competitions.`,
      });
    },
  );

  return server;
}
