/**
 * ============================================================================
 * Context Block
 * ----------------------------------------------------------------------------
 * File:    src/createServer.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: Build the MCP `McpServer` and register every tool, given a ready
 *          `SoccerDatabase`. Kept separate from the stdio bootstrap in
 *          `server.ts` so the same server can be wired to an in-memory
 *          transport in tests (no process / stdio required).
 *
 * Tools registered (covering the five spec capability areas):
 *   search_matches, head_to_head        -> Match Queries
 *   team_stats                          -> Team Queries
 *   search_players, players_by_club     -> Player Queries
 *   standings, list_competitions        -> Competition Queries
 *   league_stats, biggest_wins          -> Statistical Analysis
 *   data_summary                        -> diagnostics
 * ============================================================================
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import type { SoccerDatabase } from './database.js';
import {
  formatMatches,
  formatHeadToHead,
  formatTeamRecord,
  formatStandings,
  formatPlayers,
  formatMatchLine,
} from './format.js';

/** Build a standard tool result with both text and structured content. */
function result(text: string, structured: unknown) {
  return {
    content: [{ type: 'text' as const, text }],
    structuredContent: { data: structured } as Record<string, unknown>,
  };
}

export function createServer(db: SoccerDatabase): McpServer {
  const server = new McpServer({
    name: 'brazilian-soccer-mcp',
    version: '1.0.0',
  });

  // ----- 1. Match queries -------------------------------------------------
  server.registerTool(
    'search_matches',
    {
      title: 'Search matches',
      description:
        'Find matches by team, opponent, competition, season, date range, or venue. ' +
        'Returns matches sorted most-recent first. Handles team-name variants ' +
        '(e.g. "Palmeiras", "Palmeiras-SP", "São Paulo"/"Sao Paulo").',
      inputSchema: {
        team: z.string().optional().describe('A team that must be involved (home or away).'),
        opponent: z.string().optional().describe('A second team, to find fixtures between the two.'),
        competition: z.string().optional().describe('Brasileirão, Copa do Brasil, Copa Libertadores, ...'),
        season: z.number().int().optional().describe('Season year, e.g. 2019.'),
        dateFrom: z.string().optional().describe('Inclusive ISO date lower bound (YYYY-MM-DD).'),
        dateTo: z.string().optional().describe('Inclusive ISO date upper bound (YYYY-MM-DD).'),
        venue: z.enum(['home', 'away']).optional().describe('Restrict `team` to home or away matches.'),
        limit: z.number().int().positive().max(500).optional().describe('Max matches to return (default 50).'),
      },
    },
    async (args) => {
      const matches = db.searchMatches({ ...args, limit: args.limit ?? 50 });
      return result(formatMatches(matches, buildMatchHeading(args)), matches);
    },
  );

  server.registerTool(
    'head_to_head',
    {
      title: 'Head-to-head record',
      description:
        'Compare two teams head-to-head: total meetings, wins for each, draws, ' +
        'goals, and the list of matches. Optionally restrict to a competition.',
      inputSchema: {
        team1: z.string().describe('First team.'),
        team2: z.string().describe('Second team.'),
        competition: z.string().optional().describe('Optional competition filter.'),
      },
    },
    async ({ team1, team2, competition }) => {
      const h2h = db.headToHead(team1, team2, competition);
      return result(formatHeadToHead(h2h), h2h);
    },
  );

  // ----- 2. Team queries --------------------------------------------------
  server.registerTool(
    'team_stats',
    {
      title: 'Team statistics',
      description:
        'Win/draw/loss record, goals for/against, points and win rate for a team, ' +
        'optionally filtered by season, competition and venue (home/away).',
      inputSchema: {
        team: z.string().describe('Team name (any common variant).'),
        season: z.number().int().optional(),
        competition: z.string().optional(),
        venue: z.enum(['home', 'away']).optional(),
      },
    },
    async ({ team, season, competition, venue }) => {
      const rec = db.teamStats(team, { season, competition, venue });
      return result(formatTeamRecord(rec, { season, competition, venue }), rec);
    },
  );

  // ----- 3. Player queries ------------------------------------------------
  server.registerTool(
    'search_players',
    {
      title: 'Search players',
      description:
        'Search the FIFA player database by name, nationality (e.g. "Brazil"), ' +
        'club, and/or position, with a minimum overall rating. Sorted by overall ' +
        'rating by default.',
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional().describe('e.g. GK, CB, CDM, CAM, LW, ST.'),
        minOverall: z.number().int().optional(),
        sortBy: z.enum(['overall', 'potential', 'age', 'name']).optional(),
        limit: z.number().int().positive().max(500).optional().describe('Default 25.'),
      },
    },
    async (args) => {
      const players = db.searchPlayers({ ...args, limit: args.limit ?? 25 });
      return result(formatPlayers(players, buildPlayerHeading(args)), players);
    },
  );

  server.registerTool(
    'players_by_club',
    {
      title: 'Players grouped by club',
      description:
        'Aggregate players by club (count and average overall rating). Optionally ' +
        'filter by nationality (e.g. Brazilian players at each club).',
      inputSchema: {
        nationality: z.string().optional(),
        minPlayers: z.number().int().optional().describe('Only clubs with at least this many players.'),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async ({ nationality, minPlayers, limit }) => {
      const rows = db.playersByClub({ nationality, minPlayers });
      const shown = rows.slice(0, limit ?? 25);
      const heading = nationality ? `${nationality} players by club:` : 'Players by club:';
      const text = [
        heading,
        ...shown.map((r) => `- ${r.club}: ${r.players} players (avg rating: ${r.avgRating})`),
      ].join('\n');
      return result(text, shown);
    },
  );

  // ----- 4. Competition queries ------------------------------------------
  server.registerTool(
    'standings',
    {
      title: 'Competition standings',
      description:
        'Compute a league table for a competition + season from match results ' +
        '(3 points per win, 1 per draw), ordered by points then goal difference.',
      inputSchema: {
        competition: z.string().describe('e.g. Brasileirão.'),
        season: z.number().int().describe('Season year, e.g. 2019.'),
        limit: z.number().int().positive().max(50).optional(),
      },
    },
    async ({ competition, season, limit }) => {
      const rows = db.standings(competition, season);
      return result(formatStandings(rows, competition, season, limit ?? 20), rows);
    },
  );

  server.registerTool(
    'list_competitions',
    {
      title: 'List competitions',
      description: 'List the competitions available in the loaded data, with season ranges and match counts.',
      inputSchema: {},
    },
    async () => {
      const comps = db.listCompetitions();
      const text = [
        'Available competitions:',
        ...comps.map((c) => `- ${c.name}: ${c.matches} matches (${c.firstSeason}–${c.lastSeason})`),
      ].join('\n');
      return result(text, comps);
    },
  );

  // ----- 5. Statistical analysis -----------------------------------------
  server.registerTool(
    'league_stats',
    {
      title: 'League statistics',
      description:
        'Aggregate statistics for a competition/season (or everything): average ' +
        'goals per match, home/away/draw rates and totals.',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
      },
    },
    async ({ competition, season }) => {
      const stats = db.leagueStats({ competition, season });
      const text = [
        `Statistics for ${stats.competition} (${stats.season}):`,
        `- Matches: ${stats.matches}`,
        `- Total goals: ${stats.totalGoals}`,
        `- Average goals per match: ${stats.avgGoalsPerMatch}`,
        `- Home win rate: ${stats.homeWinRate}%`,
        `- Away win rate: ${stats.awayWinRate}%`,
        `- Draw rate: ${stats.drawRate}%`,
      ].join('\n');
      return result(text, stats);
    },
  );

  server.registerTool(
    'biggest_wins',
    {
      title: 'Biggest wins',
      description:
        'The largest goal-margin victories, optionally filtered by competition ' +
        'and/or season.',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(100).optional().describe('Default 10.'),
      },
    },
    async ({ competition, season, limit }) => {
      const matches = db.biggestWins({ competition, season, limit: limit ?? 10 });
      const heading = `Biggest victories${competition ? ` in ${competition}` : ''}${
        season ? ` (${season})` : ''
      }:`;
      const text = [
        heading,
        ...matches.map(
          (m, i) => `${i + 1}. ${formatMatchLine(m)} (margin ${Math.abs(m.homeGoal - m.awayGoal)})`,
        ),
      ].join('\n');
      return result(text, matches);
    },
  );

  server.registerTool(
    'data_summary',
    {
      title: 'Data summary',
      description: 'Overview of the loaded datasets: total matches/players, season range, per-competition and per-source counts.',
      inputSchema: {},
    },
    async () => {
      const s = db.summary();
      const text = [
        `Loaded ${s.totalMatches} matches and ${s.totalPlayers} players.`,
        `Season range: ${s.seasonRange.join('–')}`,
        'Competitions:',
        ...s.competitions.map((c) => `- ${c.name}: ${c.count}`),
        'Sources:',
        ...Object.entries(s.sourceCounts).map(([f, n]) => `- ${f}: ${n}`),
      ].join('\n');
      return result(text, s);
    },
  );

  return server;
}

// --------------------------------------------------------------------------
// Heading helpers
// --------------------------------------------------------------------------

function buildMatchHeading(args: {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
}): string {
  const parts: string[] = [];
  if (args.team && args.opponent) parts.push(`${args.team} vs ${args.opponent}`);
  else if (args.team) parts.push(`${args.team} matches`);
  else parts.push('Matches');
  if (args.competition) parts.push(`in ${args.competition}`);
  if (args.season != null) parts.push(`(${args.season})`);
  return parts.join(' ') + ':';
}

function buildPlayerHeading(args: {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
}): string {
  const parts: string[] = ['Players'];
  if (args.position) parts.push(args.position);
  if (args.nationality) parts.push(`from ${args.nationality}`);
  if (args.club) parts.push(`at ${args.club}`);
  if (args.name) parts.push(`matching "${args.name}"`);
  return parts.join(' ') + ':';
}
