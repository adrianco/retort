#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { getData } from './loader.js';
import {
  filterMatches,
  teamRecord,
  headToHead,
  competitionStandings,
  filterPlayers,
  topScoringTeams,
  biggestWins,
  aggregateStats,
  brazilianPlayersByClub,
  competitionsForTeam,
} from './queries.js';
import {
  formatMatchList,
  formatTeamRecord,
  formatHeadToHead,
  formatStandings,
  formatPlayers,
  formatScoringStats,
  formatAggregate,
  formatPlayerClubSummary,
} from './format.js';

const competitionEnum = z.enum(['Brasileirão', 'Copa do Brasil', 'Copa Libertadores', 'Other', 'all']);

export function buildServer() {
  const server = new McpServer({
    name: 'brazilian-soccer-mcp',
    version: '1.0.0',
  });

  server.registerTool(
    'find_matches',
    {
      title: 'Find matches',
      description:
        'Find matches by team, opponent, competition, season, or date range. Returns a list of matches sorted by date (most recent first).',
      inputSchema: {
        team: z.string().optional().describe('Team name (matches as home or away)'),
        opponent: z.string().optional().describe('Restrict to matches against this opponent'),
        homeTeam: z.string().optional(),
        awayTeam: z.string().optional(),
        competition: competitionEnum.optional(),
        season: z.number().int().optional(),
        fromDate: z.string().optional().describe('ISO date YYYY-MM-DD'),
        toDate: z.string().optional().describe('ISO date YYYY-MM-DD'),
        stage: z.string().optional(),
        round: z.union([z.string(), z.number()]).optional(),
        limit: z.number().int().positive().max(500).optional(),
      },
    },
    async (args) => {
      const data = getData();
      const matches = filterMatches(data.matches, args);
      return { content: [{ type: 'text', text: formatMatchList(matches, args.limit ?? 25) }] };
    },
  );

  server.registerTool(
    'team_record',
    {
      title: 'Team record',
      description: 'Compute a team\'s win/draw/loss record, with optional season, competition, and venue filters.',
      inputSchema: {
        team: z.string().describe('Team name'),
        season: z.number().int().optional(),
        competition: competitionEnum.optional(),
        venue: z.enum(['home', 'away', 'all']).optional(),
      },
    },
    async (args) => {
      const data = getData();
      const rec = teamRecord(data.matches, args.team, {
        season: args.season,
        competition: args.competition,
        venue: args.venue,
      });
      const filters = [
        args.competition && args.competition !== 'all' ? args.competition : undefined,
        args.season ? String(args.season) : undefined,
        args.venue && args.venue !== 'all' ? `${args.venue} only` : undefined,
      ].filter(Boolean).join(', ');
      const heading = `Record for ${args.team}${filters ? ` (${filters})` : ''}`;
      return { content: [{ type: 'text', text: formatTeamRecord(rec, heading) }] };
    },
  );

  server.registerTool(
    'head_to_head',
    {
      title: 'Head-to-head',
      description: 'Compute the head-to-head record between two teams.',
      inputSchema: {
        teamA: z.string(),
        teamB: z.string(),
        competition: competitionEnum.optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const data = getData();
      const h = headToHead(data.matches, args.teamA, args.teamB, {
        competition: args.competition,
        season: args.season,
      });
      return { content: [{ type: 'text', text: formatHeadToHead(h) }] };
    },
  );

  server.registerTool(
    'competition_standings',
    {
      title: 'Competition standings',
      description: 'Compute final standings for a competition in a given season, derived from match results.',
      inputSchema: {
        competition: z.enum(['Brasileirão', 'Copa do Brasil', 'Copa Libertadores', 'Other']),
        season: z.number().int(),
        limit: z.number().int().positive().max(40).optional(),
      },
    },
    async (args) => {
      const data = getData();
      const rows = competitionStandings(data.matches, args.competition, args.season);
      const heading = `${args.season} ${args.competition} standings (calculated from matches):`;
      return { content: [{ type: 'text', text: `${heading}\n${formatStandings(rows, args.limit ?? 30)}` }] };
    },
  );

  server.registerTool(
    'find_players',
    {
      title: 'Find players',
      description: 'Search the FIFA player database by name, club, nationality, or position.',
      inputSchema: {
        name: z.string().optional(),
        club: z.string().optional(),
        nationality: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().optional(),
        maxOverall: z.number().int().optional(),
        sortBy: z.enum(['overall', 'potential', 'age', 'name']).optional(),
        order: z.enum(['asc', 'desc']).optional(),
        limit: z.number().int().positive().max(200).optional(),
      },
    },
    async (args) => {
      const data = getData();
      const players = filterPlayers(data.players, args);
      return { content: [{ type: 'text', text: formatPlayers(players, args.limit ?? 25) }] };
    },
  );

  server.registerTool(
    'top_scoring_teams',
    {
      title: 'Top scoring teams',
      description: 'Rank teams by goals scored, optionally limited to a competition, season, or venue.',
      inputSchema: {
        competition: competitionEnum.optional(),
        season: z.number().int().optional(),
        venue: z.enum(['home', 'away', 'all']).optional(),
        limit: z.number().int().positive().max(50).optional(),
      },
    },
    async (args) => {
      const data = getData();
      const rows = topScoringTeams(data.matches, args);
      return { content: [{ type: 'text', text: formatScoringStats(rows, args.limit ?? 15) }] };
    },
  );

  server.registerTool(
    'biggest_wins',
    {
      title: 'Biggest wins',
      description: 'Find the biggest victories in the dataset, optionally filtered by competition or season.',
      inputSchema: {
        competition: competitionEnum.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(50).optional(),
      },
    },
    async (args) => {
      const data = getData();
      const matches = biggestWins(data.matches, args);
      return { content: [{ type: 'text', text: formatMatchList(matches, args.limit ?? 10) }] };
    },
  );

  server.registerTool(
    'aggregate_stats',
    {
      title: 'Aggregate statistics',
      description: 'Compute aggregate statistics (averages, win rates) for a competition / season / overall.',
      inputSchema: {
        competition: competitionEnum.optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const data = getData();
      const stats = aggregateStats(data.matches, args);
      return { content: [{ type: 'text', text: formatAggregate(stats) }] };
    },
  );

  server.registerTool(
    'brazilian_players_by_club',
    {
      title: 'Brazilian players grouped by club',
      description: 'Group Brazilian players in the FIFA dataset by club, with player counts and average overall rating.',
      inputSchema: {
        limit: z.number().int().positive().max(100).optional(),
      },
    },
    async (args) => {
      const data = getData();
      const rows = brazilianPlayersByClub(data.players);
      return { content: [{ type: 'text', text: formatPlayerClubSummary(rows, args.limit ?? 25) }] };
    },
  );

  server.registerTool(
    'competitions_for_team',
    {
      title: 'Competitions for team',
      description: 'List the competitions in which a given team appears in the dataset.',
      inputSchema: {
        team: z.string(),
      },
    },
    async (args) => {
      const data = getData();
      const comps = competitionsForTeam(data.matches, args.team);
      const text = comps.length
        ? `${args.team} appears in: ${comps.join(', ')}`
        : `No matches found for ${args.team}`;
      return { content: [{ type: 'text', text }] };
    },
  );

  return server;
}

async function main() {
  const server = buildServer();
  // Eager-load data on startup so first tool call isn't slow.
  getData();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  main().catch((err) => {
    console.error('Server failed:', err);
    process.exit(1);
  });
}
