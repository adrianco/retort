/*
 * Context: MCP server wiring. Registers the query tools with zod-validated inputs, lazily
 * loads the dataset on first call, and turns QueryError into tool errors so the LLM sees a
 * readable message (e.g. "ambiguous team name, did you mean ...").
 * Tools: search_matches, team_stats, head_to_head, standings, biggest_wins,
 * aggregate_stats, search_players, club_squad_summary.
 * Related: queries.ts, format.ts, dataset.ts, index.ts (stdio transport).
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { loadDataset } from './dataset.js';
import * as q from './queries.js';
import * as f from './format.js';
import { COMPETITION } from './dataset.js';
import type { Dataset } from './types.js';

type TextResult = { content: { type: 'text'; text: string }[]; isError?: boolean };

const text = (t: string): TextResult => ({ content: [{ type: 'text', text: t }] });

/** Run a query against the loaded dataset, mapping user errors to MCP tool errors. */
async function run(fn: (ds: Dataset) => string): Promise<TextResult> {
  try {
    return text(fn(await loadDataset()));
  } catch (err) {
    if (err instanceof q.QueryError) return { ...text(err.message), isError: true };
    throw err;
  }
}

const competitionSchema = z
  .string()
  .optional()
  .describe(`Competition, e.g. "Brasileirão Série A", "Copa do Brasil", "Copa Libertadores" (partial names ok)`);
const seasonSchema = z.number().int().optional().describe('Season year, e.g. 2023');
const dateSchema = z.string().optional().describe('ISO date YYYY-MM-DD');

export function createServer(): McpServer {
  const server = new McpServer({ name: 'brazilian-soccer', version: '1.0.0' });

  server.registerTool(
    'search_matches',
    {
      description: 'Find matches by team (home/away/either), opponent, competition, season and date range. Most recent first.',
      inputSchema: {
        team: z.string().optional().describe('Team name, e.g. "Flamengo" or "Palmeiras-SP"'),
        opponent: z.string().optional().describe('Opponent team name'),
        venue: z.enum(['home', 'away', 'any']).optional().describe('Whether team plays at home, away, or either'),
        competition: competitionSchema,
        season: seasonSchema,
        dateFrom: dateSchema,
        dateTo: dateSchema,
        limit: z.number().int().min(1).max(100).optional().describe('Max matches to return (default 20)'),
      },
    },
    (a) => run((ds) => {
      const r = q.searchMatches(ds, {
        team: a.team,
        opponent: a.opponent,
        venue: a.venue,
        limit: a.limit,
        filter: { competition: a.competition, season: a.season, dateFrom: a.dateFrom, dateTo: a.dateTo },
      });
      const title = [a.team, a.opponent && `vs ${a.opponent}`, a.competition, a.season].filter(Boolean).join(' ') || 'Matches';
      return f.formatMatches(title, r.total, r.matches);
    }),
  );

  server.registerTool(
    'team_stats',
    {
      description: 'Team record: wins/draws/losses, goals for/against and win rate, optionally by competition, season and venue.',
      inputSchema: {
        team: z.string().describe('Team name'),
        competition: competitionSchema,
        season: seasonSchema,
        venue: z.enum(['home', 'away', 'any']).optional(),
      },
    },
    (a) => run((ds) => f.formatTeamStats(q.teamStats(ds, a.team, {
      venue: a.venue,
      filter: { competition: a.competition, season: a.season },
    }))),
  );

  server.registerTool(
    'head_to_head',
    {
      description: 'Head-to-head record between two teams, with recent meetings.',
      inputSchema: {
        teamA: z.string().describe('First team'),
        teamB: z.string().describe('Second team'),
        competition: competitionSchema,
        season: seasonSchema,
      },
    },
    (a) => run((ds) => f.formatHeadToHead(q.headToHead(ds, a.teamA, a.teamB, {
      competition: a.competition,
      season: a.season,
    }))),
  );

  server.registerTool(
    'standings',
    {
      description: 'League table for a season calculated from match results (3 points per win, 1 per draw). Defaults to Brasileirão Série A.',
      inputSchema: {
        season: z.number().int().describe('Season year, e.g. 2019'),
        competition: z.string().optional().describe(`Default "${COMPETITION.SERIE_A}"`),
      },
    },
    (a) => run((ds) => {
      const competition = a.competition ?? COMPETITION.SERIE_A;
      return f.formatStandings(`${competition} ${a.season}`, q.standings(ds, a.season, competition));
    }),
  );

  server.registerTool(
    'biggest_wins',
    {
      description: 'Largest margins of victory in the dataset, optionally filtered by competition and season.',
      inputSchema: {
        competition: competitionSchema,
        season: seasonSchema,
        limit: z.number().int().min(1).max(100).optional().describe('Default 10'),
      },
    },
    (a) => run((ds) => {
      const wins = q.biggestWins(ds, { competition: a.competition, season: a.season }, a.limit ?? 10);
      return f.formatMatches('Biggest wins', wins.length, wins);
    }),
  );

  server.registerTool(
    'aggregate_stats',
    {
      description: 'League-wide statistics: average goals per match, home/draw/away win rates. Use seasonFrom/seasonTo for ranges; call twice to compare seasons.',
      inputSchema: {
        competition: competitionSchema,
        season: seasonSchema,
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
      },
    },
    (a) => run((ds) => {
      const title = ['Statistics', a.competition, a.season ?? (a.seasonFrom || a.seasonTo ? `${a.seasonFrom ?? ''}-${a.seasonTo ?? ''}` : undefined)]
        .filter(Boolean).join(' ');
      return f.formatAggregate(title, q.aggregateStats(ds, {
        competition: a.competition,
        season: a.season,
        seasonFrom: a.seasonFrom,
        seasonTo: a.seasonTo,
      }));
    }),
  );

  server.registerTool(
    'search_players',
    {
      description: 'Search FIFA player data by name, nationality, club, position and minimum overall rating.',
      inputSchema: {
        name: z.string().optional().describe('Full or partial player name'),
        nationality: z.string().optional().describe('e.g. "Brazil"'),
        club: z.string().optional().describe('Club name, e.g. "Flamengo"'),
        position: z.string().optional().describe('Position code, e.g. "ST", "GK", "CDM"'),
        minOverall: z.number().int().optional(),
        sortBy: z.enum(['overall', 'potential', 'age']).optional().describe('Default overall (desc); age ascending'),
        limit: z.number().int().min(1).max(100).optional().describe('Default 20'),
      },
    },
    (a) => run((ds) => {
      const r = q.searchPlayers(ds, a);
      return f.formatPlayers('Players', r.total, r.players);
    }),
  );

  server.registerTool(
    'club_squad_summary',
    {
      description: 'Squad summary per club: player count and average overall rating. Optionally filter by nationality (e.g. "Brazil") and limit to clubs that appear in the match datasets.',
      inputSchema: {
        nationality: z.string().optional(),
        brazilianClubsOnly: z.boolean().optional().describe('Only clubs that appear in the Brazilian match data'),
        limit: z.number().int().min(1).max(100).optional().describe('Default 20'),
      },
    },
    (a) => run((ds) => {
      const label = [a.nationality, a.brazilianClubsOnly ? 'at Brazilian clubs' : undefined].filter(Boolean).join(' ');
      return f.formatClubSummaries(`Clubs${label ? ` (${label})` : ''} by average overall`, q.clubSummaries(ds, a));
    }),
  );

  return server;
}
