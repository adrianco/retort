/**
 * Context: registers the MCP tools on a server. Each tool validates its
 * arguments with zod, calls a pure query, and returns formatted text. The
 * dataset is injected so tests can run against fixtures.
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import * as f from './format.js';
import * as q from './queries.js';
import { normalizeCompetition } from './normalize.js';
import type { Dataset, MatchFilter } from './types.js';

const SERVER_NAME = 'brazilian-soccer';
const SERVER_VERSION = '1.0.0';
const DEFAULT_COMPETITION = 'Brasileirão Série A';

const competitionSchema = z.string().describe(
  'Competition: "Brasileirão Série A", "Série B", "Série C", "Copa do Brasil", or "Copa Libertadores".',
);
const seasonSchema = z.number().int().describe('Season year, e.g. 2023.');
const venueSchema = z.enum(['home', 'away', 'any']).optional().describe('Where the team played. Default: any.');
const limitSchema = (max: number, def: number) =>
  z.number().int().min(1).max(max).optional().describe(`Maximum results to return (default ${def}).`);

function text(body: string) {
  return { content: [{ type: 'text' as const, text: body }] };
}

function requireCompetition(raw: string | undefined): string | undefined {
  if (raw === undefined) return undefined;
  const canonical = normalizeCompetition(raw);
  if (!canonical) throw new Error(`Unknown competition "${raw}".`);
  return canonical;
}

function scopeLabel(season: number | undefined, competition: string | undefined): string {
  return [competition, season !== undefined ? String(season) : undefined].filter(Boolean).join(' ');
}

export function createServer(dataset: Dataset): McpServer {
  const server = new McpServer({ name: SERVER_NAME, version: SERVER_VERSION });

  server.registerTool(
    'search_matches',
    {
      description:
        'Find matches across Brasileirão, Copa do Brasil and Copa Libertadores. Filter by team, opponent, venue, competition, season range, date range, or finals only.',
      inputSchema: {
        team: z.string().optional().describe('Team name, e.g. "Flamengo" or "Palmeiras-SP".'),
        opponent: z.string().optional().describe('Second team; returns only meetings between team and opponent.'),
        venue: venueSchema,
        competition: competitionSchema.optional(),
        season: seasonSchema.optional(),
        season_from: seasonSchema.optional(),
        season_to: seasonSchema.optional(),
        date_from: z.string().optional().describe('Earliest date, YYYY-MM-DD.'),
        date_to: z.string().optional().describe('Latest date, YYYY-MM-DD.'),
        finals_only: z.boolean().optional().describe('Only final matches (last cup round of each season, or Libertadores "final" stage).'),
        limit: limitSchema(100, 20),
      },
    },
    async (args) => {
      const filter: MatchFilter = {
        team: args.team,
        opponent: args.opponent,
        venue: args.venue,
        competition: requireCompetition(args.competition),
        season: args.season,
        seasonFrom: args.season_from,
        seasonTo: args.season_to,
        dateFrom: args.date_from,
        dateTo: args.date_to,
        finalOnly: args.finals_only,
      };
      const matches = q.filterMatches(dataset, filter);
      const title = `Matches${args.team ? ` for ${args.team}` : ''}${args.opponent ? ` vs ${args.opponent}` : ''}:`;
      return text(f.formatMatches(title, matches, matches.length, args.limit ?? 20));
    },
  );

  server.registerTool(
    'team_record',
    {
      description: 'Win/draw/loss record and goals for a team, optionally by season, competition, and venue.',
      inputSchema: {
        team: z.string().describe('Team name.'),
        competition: competitionSchema.optional(),
        season: seasonSchema.optional(),
        venue: venueSchema,
      },
    },
    async (args) => {
      const competition = requireCompetition(args.competition);
      const record = q.teamRecord(dataset, args.team, {
        competition,
        season: args.season,
        venue: args.venue,
      });
      const venueLabel = args.venue && args.venue !== 'any' ? `${args.venue} ` : '';
      const label = `${venueLabel}record${scopeLabel(args.season, competition) ? ` (${scopeLabel(args.season, competition)})` : ''}`;
      return text(f.formatTeamRecord(record, label));
    },
  );

  server.registerTool(
    'head_to_head',
    {
      description: 'Head-to-head record between two teams with every meeting in the dataset.',
      inputSchema: {
        team_a: z.string().describe('First team.'),
        team_b: z.string().describe('Second team.'),
        competition: competitionSchema.optional(),
        season: seasonSchema.optional(),
        limit: limitSchema(100, 20),
      },
    },
    async (args) => {
      const result = q.headToHead(dataset, args.team_a, args.team_b, {
        competition: requireCompetition(args.competition),
        season: args.season,
      });
      return text(f.formatHeadToHead(result, args.limit ?? 20));
    },
  );

  server.registerTool(
    'standings',
    {
      description: 'Points table for a Brasileirão (or other) competition and season, calculated from match results.',
      inputSchema: {
        season: seasonSchema,
        competition: competitionSchema.optional().describe('Default: Brasileirão Série A.'),
      },
    },
    async (args) => {
      const competition = requireCompetition(args.competition) ?? DEFAULT_COMPETITION;
      const rows = q.standings(dataset, competition, args.season);
      return text(f.formatStandings(`${args.season} ${competition} standings (calculated from matches):`, rows));
    },
  );

  server.registerTool(
    'rank_teams',
    {
      description:
        'Rank teams by a metric: win_rate, wins, goals_for, goal_difference, or points_per_match. Use venue for home or away records.',
      inputSchema: {
        metric: z.enum(['win_rate', 'wins', 'goals_for', 'goal_difference', 'points_per_match']),
        competition: competitionSchema.optional(),
        season: seasonSchema.optional(),
        venue: venueSchema,
        min_matches: z.number().int().min(1).optional().describe('Minimum matches played to qualify (default 1).'),
        limit: limitSchema(50, 10),
      },
    },
    async (args) => {
      const competition = requireCompetition(args.competition);
      const rows = q.rankTeams(
        dataset,
        args.metric,
        { competition, season: args.season, venue: args.venue },
        args.min_matches ?? 1,
        args.limit ?? 10,
      );
      const scope = [args.venue && args.venue !== 'any' ? `${args.venue} matches` : undefined, scopeLabel(args.season, competition)]
        .filter(Boolean)
        .join(', ');
      return text(f.formatRanking(`Teams ranked by ${args.metric}${scope ? ` (${scope})` : ''}:`, args.metric, rows));
    },
  );

  server.registerTool(
    'league_stats',
    {
      description: 'Aggregate statistics: average goals per match, home/draw/away rates.',
      inputSchema: {
        competition: competitionSchema.optional(),
        season: seasonSchema.optional(),
        season_from: seasonSchema.optional(),
        season_to: seasonSchema.optional(),
      },
    },
    async (args) => {
      const competition = requireCompetition(args.competition);
      const stats = q.leagueStats(dataset, {
        competition,
        season: args.season,
        seasonFrom: args.season_from,
        seasonTo: args.season_to,
      });
      const scope = scopeLabel(args.season, competition) || 'all competitions';
      return text(f.formatLeagueStats(`Statistics (${scope}):`, stats));
    },
  );

  server.registerTool(
    'biggest_wins',
    {
      description: 'Largest winning margins in the dataset, optionally filtered by competition or season.',
      inputSchema: {
        competition: competitionSchema.optional(),
        season: seasonSchema.optional(),
        limit: limitSchema(50, 5),
      },
    },
    async (args) => {
      const competition = requireCompetition(args.competition);
      const matches = q.biggestWins(dataset, { competition, season: args.season }, args.limit ?? 5);
      return text(f.formatMatches(`Biggest wins (${scopeLabel(args.season, competition) || 'all competitions'}):`, matches, matches.length, matches.length));
    },
  );

  server.registerTool(
    'search_players',
    {
      description:
        'Search FIFA player data by name, nationality, club, position, or minimum overall rating. Club and name matching ignore accents and case.',
      inputSchema: {
        name: z.string().optional().describe('Full or partial name, e.g. "Neymar" or "Gabriel Barbosa".'),
        nationality: z.string().optional().describe('Country, e.g. "Brazil".'),
        club: z.string().optional().describe('Club name, matched as a substring, e.g. "Flamengo".'),
        position: z.string().optional().describe('Position code, e.g. "ST", "GK", "CDM".'),
        min_overall: z.number().int().optional(),
        sort_by: z.enum(['overall', 'potential', 'age']).optional().describe('Default: overall (descending; age ascending).'),
        limit: limitSchema(100, 10),
      },
    },
    async (args) => {
      const players = q.searchPlayers(dataset, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.min_overall,
        sortBy: args.sort_by,
        limit: args.limit ?? 10,
      });
      return text(f.formatPlayers('Players:', players));
    },
  );

  server.registerTool(
    'team_profile',
    {
      description: 'Combined view of a team: its match record in the dataset plus squad members listed in the FIFA data.',
      inputSchema: {
        team: z.string().describe('Team name, e.g. "Flamengo".'),
        player_limit: limitSchema(100, 10),
      },
    },
    async (args) => {
      const { record, players } = q.teamProfile(dataset, args.team);
      const limit = args.player_limit ?? 10;
      const body = [
        f.formatTeamRecord(record, 'match record (all competitions)'),
        '',
        f.formatPlayers(`Players at ${args.team} (${players.length} in FIFA data, top ${Math.min(limit, players.length)}):`, players.slice(0, limit)),
      ];
      return text(body.join('\n'));
    },
  );

  server.registerTool(
    'club_summary',
    {
      description: 'Player counts and average overall rating per club, optionally for one nationality (e.g. "Brazil").',
      inputSchema: {
        nationality: z.string().optional(),
        limit: limitSchema(200, 20),
      },
    },
    async (args) => {
      const rows = q.clubSummary(dataset, args.nationality).slice(0, args.limit ?? 20);
      const title = args.nationality ? `${args.nationality} players by club:` : 'Players by club:';
      return text(f.formatClubSummary(title, rows));
    },
  );

  server.registerTool(
    'dataset_info',
    {
      description: 'Describe the loaded datasets: rows read and matches or players loaded per file.',
      inputSchema: {},
    },
    async () => {
      const lines = dataset.sources.map((s) => `- ${s.file}: ${s.loaded} of ${s.rows} rows loaded`);
      const matchCount = dataset.matches.length;
      const seasons = dataset.matches.map((m) => m.season);
      const body = [
        'Loaded datasets:',
        ...lines,
        `Unique matches (after cross-file dedupe): ${matchCount}`,
        `Seasons: ${Math.min(...seasons)}-${Math.max(...seasons)}`,
        `Players: ${dataset.players.length}`,
      ];
      return text(body.join('\n'));
    },
  );

  return server;
}
