import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { SoccerGraph } from './soccer.js';

const text = z.string().trim().min(1);
const team = text.describe('Club name, including common aliases such as Corinthians-SP.');
const competition = text.describe('Competition such as Brasileirão, Série B, Série C, Copa do Brasil or Libertadores.');
const season = z.number().int().describe('Competition season year, which may differ from the fixture calendar year.');
const matchFilters = {
  team: team.optional(),
  opponent: team.optional().describe('Second team in a head-to-head fixture search. Requires team.'),
  venue: z.enum(['home', 'away', 'either']).optional().describe('Venue from the selected team’s perspective.'),
  competition: competition.optional(),
  season: season.optional(),
  seasons: z.array(season).min(1).optional().describe('Multiple season years for comparison.'),
  from: text.optional().describe('Inclusive first match date, ISO or DD/MM/YYYY.'),
  to: text.optional().describe('Inclusive last match date, ISO or DD/MM/YYYY.'),
  round: z.number().int().positive().optional(),
  stage: text.optional().describe('Stage such as final, quarterfinals, group stage or knockout.'),
  derby: z.boolean().optional().describe('Restrict matches to the built-in list of traditional rivalries.'),
  source: z.enum(['league', 'historical', 'cup', 'libertadores', 'extended']).optional()
    .describe('Query the specified CSV directly. Omit for reconciled fixtures across sources.'),
  status: z.enum(['played', 'unscored']).optional(),
};
const pagination = {
  limit: z.number().int().min(1).max(100).optional().describe('Results per page. Defaults to 20.'),
  offset: z.number().int().nonnegative().optional().describe('Next offset returned by a previous page.'),
};
const playerFilters = {
  name: text.optional().describe('Case- and accent-insensitive FIFA display name substring.'),
  nationality: text.optional(),
  club: team.optional(),
  brazilianClub: z.boolean().optional().describe('Filter clubs identified from Brazilian domestic match data.'),
  position: text.optional().describe('FIFA position code or forward, midfielder, defender or goalkeeper.'),
  minOverall: z.number().int().min(0).max(100).optional(),
};

function format(result: unknown) {
  return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
}

export function createServer(graph = new SoccerGraph()) {
  const server = new McpServer({ name: 'brazilian-soccer', version: '1.0.0' }, {
    instructions: 'Answer natural-language Brazilian soccer questions using these tools. Cite dataset coverage for incomplete tables and empty results. Win rates are fractions. Player clubs and ratings reflect the FIFA snapshot.',
  });
  server.registerTool('data_coverage', {
    description: 'List the six local datasets, source keys, row counts, competitions and available seasons.',
    inputSchema: {},
  }, () => format(graph.coverage()));
  server.registerTool('search_matches', {
    description: 'Find results and unscored fixtures by team, opponent, date, competition, season, stage or rivalry. For the last meeting set limit to 1 and order to newest.',
    inputSchema: { ...matchFilters, ...pagination, order: z.enum(['newest', 'oldest']).optional() },
  }, input => format(graph.matches(input)));
  server.registerTool('team_stats', {
    description: 'Calculate a club’s wins, draws, losses, goals and venue splits with breakdowns by competition and season.',
    inputSchema: { ...matchFilters, team },
  }, input => format(graph.teamStats(input)));
  server.registerTool('head_to_head', {
    description: 'Compare two clubs’ results and records in either orientation, with optional season and competition filters.',
    inputSchema: { ...matchFilters, ...pagination, team, opponent: team },
  }, input => format(graph.headToHead(input)));
  server.registerTool('search_players', {
    description: 'Find FIFA snapshot players by name, nationality, club, position or rating. Results are ranked by rating and include physical attributes, skills and club aggregates.',
    inputSchema: { ...playerFilters, ...pagination },
  }, input => format(graph.players(input)));
  server.registerTool('standings', {
    description: 'Calculate a Série A or B season table from recorded scores, with coverage and Série A relegation places for complete 20-team seasons since 2006.',
    inputSchema: { competition, season },
  }, input => format(graph.standings(input.competition, input.season)));
  server.registerTool('competition_results', {
    description: 'Get a competition season’s fixtures by stage. Use stage knockout for a Libertadores bracket, or final for finals. Reports whether scorer data is available.',
    inputSchema: { ...matchFilters, ...pagination, competition, season },
  }, input => format(graph.competitionResults({ ...input, limit: input.limit ?? 30 })));
  server.registerTool('match_statistics', {
    description: 'Calculate goals per match, seasonal comparisons, home and away win rates, team rankings and biggest victories. Use minMatches when ranking teams by win rate.',
    inputSchema: { ...matchFilters, ...pagination,
      rankBy: z.enum(['wins', 'winRate', 'goalsFor', 'points']).optional(),
      rankVenue: z.enum(['home', 'away', 'overall']).optional(),
      minMatches: z.number().int().min(1).optional(),
    },
  }, input => format(graph.statistics(input)));
  server.registerTool('club_profile', {
    description: 'Join a club’s match history and performance with its FIFA snapshot roster, optionally filtered by player nationality and position.',
    inputSchema: { ...matchFilters, ...pagination, team,
      nationality: playerFilters.nationality, position: playerFilters.position },
  }, input => format(graph.clubProfile(input)));
  return server;
}

