import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import {
  findMatches,
  findPlayers,
  headToHead,
  teamStats,
  standings,
  aggregateStats,
  biggestWins,
  topScoringTeams,
  listCompetitions,
  listSeasons,
} from './queries.js';
import type { DataStore } from './types.js';

function ok(payload: unknown) {
  return {
    content: [
      {
        type: 'text' as const,
        text: JSON.stringify(payload, null, 2),
      },
    ],
  };
}

export function createServer(store: DataStore): McpServer {
  const server = new McpServer(
    { name: 'brazilian-soccer-mcp', version: '1.0.0' },
    { capabilities: { tools: {} } },
  );

  server.registerTool(
    'find_matches',
    {
      description:
        'Find matches by team, opponent, season, date range, or competition. Returns matches sorted by date (most recent first).',
      inputSchema: {
        team: z.string().optional().describe('Team name (matches home or away)'),
        homeTeam: z.string().optional().describe('Restrict to matches where this team played at home'),
        awayTeam: z.string().optional().describe('Restrict to matches where this team played away'),
        opponent: z.string().optional().describe('Opponent team name'),
        season: z.number().int().optional().describe('Season/year filter'),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
        dateFrom: z.string().optional().describe('ISO date YYYY-MM-DD inclusive lower bound'),
        dateTo: z.string().optional().describe('ISO date YYYY-MM-DD inclusive upper bound'),
        competition: z.string().optional().describe('Competition filter (substring match)'),
        limit: z.number().int().positive().max(500).optional().describe('Max results (default 50)'),
      },
    },
    async (args) => {
      const limit = args.limit ?? 50;
      const matches = findMatches(store, { ...args, limit });
      return ok({ count: matches.length, matches });
    },
  );

  server.registerTool(
    'head_to_head',
    {
      description: 'Head-to-head record between two teams across all competitions in the dataset.',
      inputSchema: {
        teamA: z.string().describe('First team name'),
        teamB: z.string().describe('Second team name'),
        limit: z.number().int().positive().max(200).optional().describe('Max matches returned'),
      },
    },
    async ({ teamA, teamB, limit }) => ok(headToHead(store, teamA, teamB, limit ?? 25)),
  );

  server.registerTool(
    'team_stats',
    {
      description:
        'Aggregate stats for a team: matches played, wins, draws, losses, goals for/against, points, win rate.',
      inputSchema: {
        team: z.string().describe('Team name'),
        season: z.number().int().optional().describe('Filter to a single season'),
        competition: z
          .string()
          .optional()
          .describe('Competition name substring (e.g., "Brasileirão", "Libertadores")'),
        venue: z.enum(['home', 'away', 'all']).optional().describe('Limit to home or away matches'),
      },
    },
    async (args) => ok(teamStats(store, args)),
  );

  server.registerTool(
    'standings',
    {
      description:
        'Compute a league table from match results. Defaults to Brasileirão (Serie A or historical). Pass competition to switch.',
      inputSchema: {
        season: z.number().int().describe('Season year'),
        competition: z.string().optional(),
      },
    },
    async ({ season, competition }) => ok(standings(store, { season, competition })),
  );

  server.registerTool(
    'find_players',
    {
      description:
        'Search FIFA player data by name, nationality, club, position, and overall rating.',
      inputSchema: {
        name: z.string().optional().describe('Name substring (accent-insensitive)'),
        nationality: z.string().optional().describe('Nationality substring, e.g., "Brazil"'),
        club: z.string().optional().describe('Club substring, e.g., "Flamengo"'),
        position: z.string().optional().describe('Exact position code, e.g., "ST", "LW", "GK"'),
        minOverall: z.number().int().min(0).max(99).optional(),
        maxOverall: z.number().int().min(0).max(99).optional(),
        limit: z.number().int().positive().max(500).optional(),
      },
    },
    async (args) => {
      const limit = args.limit ?? 50;
      const players = findPlayers(store, { ...args, limit });
      return ok({ count: players.length, players });
    },
  );

  server.registerTool(
    'aggregate_stats',
    {
      description:
        'Aggregate match statistics (total goals, avg goals/match, home win rate, etc.) filtered by competition/season/team.',
      inputSchema: {
        team: z.string().optional(),
        opponent: z.string().optional(),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
        dateFrom: z.string().optional(),
        dateTo: z.string().optional(),
      },
    },
    async (args) => ok(aggregateStats(store, args)),
  );

  server.registerTool(
    'biggest_wins',
    {
      description: 'Return the matches with the largest goal differences, filtered by criteria.',
      inputSchema: {
        team: z.string().optional(),
        competition: z.string().optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(100).optional(),
      },
    },
    async ({ limit, ...filter }) => ok(biggestWins(store, filter, limit ?? 10)),
  );

  server.registerTool(
    'top_scoring_teams',
    {
      description: 'Rank teams by total goals scored across matches matching the filter.',
      inputSchema: {
        competition: z.string().optional(),
        season: z.number().int().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
        limit: z.number().int().positive().max(100).optional(),
      },
    },
    async ({ limit, ...filter }) => ok(topScoringTeams(store, filter, limit ?? 10)),
  );

  server.registerTool(
    'list_competitions',
    {
      description: 'List all competitions present in the loaded data.',
      inputSchema: {},
    },
    async () => ok({ competitions: listCompetitions(store) }),
  );

  server.registerTool(
    'list_seasons',
    {
      description: 'List all season years present in the data, optionally restricted to one competition.',
      inputSchema: {
        competition: z.string().optional(),
      },
    },
    async ({ competition }) => ok({ seasons: listSeasons(store, competition) }),
  );

  return server;
}
