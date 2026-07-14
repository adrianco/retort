import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { loadAll } from './dataLoader.js';
import { DataStore, Competition } from './types.js';
import {
  findMatches,
  headToHead,
  biggestWins,
} from './queries/matches.js';
import {
  teamRecord,
  standings,
  topScoringTeams,
} from './queries/teams.js';
import {
  findPlayers,
  playersByClub,
} from './queries/players.js';
import { overallStats, seasonsAvailable } from './queries/stats.js';
import { seasonChampion, knockoutBracket } from './queries/competitions.js';
import {
  formatMatches,
  formatTeamRecord,
  formatStandings,
  formatHeadToHead,
  formatPlayers,
  formatClubSummaries,
  formatOverallStats,
  formatMatchLine,
} from './formatters.js';

const competitionSchema = z
  .enum(['Brasileirão', 'Copa do Brasil', 'Libertadores', 'Other'])
  .describe(
    "Competition name. One of: 'Brasileirão', 'Copa do Brasil', 'Libertadores', 'Other'.",
  );

function text(s: string) {
  return { content: [{ type: 'text' as const, text: s }] };
}

/**
 * Build the MCP server and register all tools.
 *
 * Accepts an optional pre-loaded DataStore so tests can inject fixtures.
 */
export async function buildServer(opts: {
  store?: DataStore;
  dataDir?: string;
} = {}): Promise<McpServer> {
  const store = opts.store ?? (await loadAll({ dataDir: opts.dataDir }));

  const server = new McpServer(
    {
      name: 'brazilian-soccer-mcp',
      version: '1.0.0',
    },
    {
      capabilities: { tools: {} },
    },
  );

  server.registerTool(
    'find_matches',
    {
      title: 'Find matches',
      description:
        'Find matches with optional filters on team, opponent, competition, season, dates, and round/stage.',
      inputSchema: {
        team: z.string().optional().describe('Team name (any spelling).'),
        opponent: z.string().optional().describe('Opponent team name.'),
        competition: competitionSchema.optional(),
        season: z.number().int().optional().describe('Season year (e.g. 2019).'),
        dateFrom: z.string().optional().describe('ISO date lower bound (YYYY-MM-DD).'),
        dateTo: z.string().optional().describe('ISO date upper bound (YYYY-MM-DD).'),
        homeOnly: z.boolean().optional(),
        awayOnly: z.boolean().optional(),
        round: z
          .string()
          .optional()
          .describe('Round or stage substring (e.g. "final", "22").'),
        limit: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      const ms = findMatches(store.matches, {
        team: args.team,
        opponent: args.opponent,
        competition: args.competition as Competition | undefined,
        season: args.season,
        dateFrom: args.dateFrom,
        dateTo: args.dateTo,
        homeOnly: args.homeOnly,
        awayOnly: args.awayOnly,
        round: args.round,
        limit: args.limit,
      });
      return text(formatMatches(ms, args.limit ?? 20));
    },
  );

  server.registerTool(
    'head_to_head',
    {
      title: 'Head-to-head record',
      description:
        'Aggregate head-to-head record between two teams across all competitions in the dataset.',
      inputSchema: {
        teamA: z.string(),
        teamB: z.string(),
      },
    },
    async ({ teamA, teamB }) => {
      const h = headToHead(store.matches, teamA, teamB);
      return text(formatHeadToHead(h));
    },
  );

  server.registerTool(
    'team_record',
    {
      title: 'Team record',
      description:
        'Compute wins, draws, losses, goals for/against, points for a team. Optionally restrict to competition/season and home/away only.',
      inputSchema: {
        team: z.string(),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        homeOnly: z.boolean().optional(),
        awayOnly: z.boolean().optional(),
      },
    },
    async (args) => {
      const r = teamRecord(store.matches, args.team, {
        competition: args.competition as Competition | undefined,
        season: args.season,
        homeOnly: args.homeOnly,
        awayOnly: args.awayOnly,
      });
      return text(formatTeamRecord(r));
    },
  );

  server.registerTool(
    'standings',
    {
      title: 'Calculated standings',
      description:
        'Compute final standings for a competition/season from match results.',
      inputSchema: {
        competition: competitionSchema,
        season: z.number().int(),
        limit: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      const rows = standings(store.matches, {
        competition: args.competition as Competition,
        season: args.season,
      });
      return text(formatStandings(rows, args.limit ?? 20));
    },
  );

  server.registerTool(
    'top_scoring_teams',
    {
      title: 'Top scoring teams',
      description: 'Top teams ranked by goals scored.',
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      const rows = topScoringTeams(store.matches, {
        competition: args.competition as Competition | undefined,
        season: args.season,
        limit: args.limit ?? 10,
      });
      if (rows.length === 0) return text('No matches found.');
      const lines = rows.map(
        (r, i) =>
          `${i + 1}. ${r.team} - ${r.goalsFor} goals in ${r.matches} matches`,
      );
      return text(lines.join('\n'));
    },
  );

  server.registerTool(
    'season_champion',
    {
      title: 'Season champion',
      description:
        'Compute the champion and runners-up for a given competition and season.',
      inputSchema: {
        competition: competitionSchema,
        season: z.number().int(),
      },
    },
    async (args) => {
      const sc = seasonChampion(
        store.matches,
        args.competition as Competition,
        args.season,
      );
      if (!sc) return text('No data for this competition/season.');
      const lines: string[] = [];
      lines.push(
        `${args.season} ${args.competition} Champion: ${sc.champion.team} (${sc.champion.points} pts, ${sc.champion.wins}W ${sc.champion.draws}D ${sc.champion.losses}L)`,
      );
      if (sc.runnersUp.length) {
        lines.push('Runners-up:');
        for (const r of sc.runnersUp) {
          lines.push(`- ${r.team} (${r.points} pts)`);
        }
      }
      return text(lines.join('\n'));
    },
  );

  server.registerTool(
    'knockout_bracket',
    {
      title: 'Knockout bracket',
      description:
        'Return matches grouped by stage for a knockout competition season (Libertadores, Copa do Brasil).',
      inputSchema: {
        competition: competitionSchema,
        season: z.number().int(),
      },
    },
    async (args) => {
      const groups = knockoutBracket(
        store.matches,
        args.competition as Competition,
        args.season,
      );
      const stages = Object.keys(groups);
      if (stages.length === 0) return text('No data for this competition/season.');
      const out: string[] = [];
      for (const stage of stages) {
        out.push(`== ${stage} ==`);
        for (const m of groups[stage]) {
          out.push('- ' + formatMatchLine(m));
        }
        out.push('');
      }
      return text(out.join('\n').trim());
    },
  );

  server.registerTool(
    'find_players',
    {
      title: 'Find players',
      description:
        'Search the FIFA player dataset by name, nationality, club, position, age, and rating.',
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().optional(),
        minAge: z.number().int().optional(),
        maxAge: z.number().int().optional(),
        limit: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      const ps = findPlayers(store.players, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
        minAge: args.minAge,
        maxAge: args.maxAge,
        limit: args.limit,
      });
      return text(formatPlayers(ps, args.limit ?? 25));
    },
  );

  server.registerTool(
    'players_by_club',
    {
      title: 'Players grouped by club',
      description:
        'Summarize players by club. Optionally restrict to a nationality.',
      inputSchema: {
        nationality: z.string().optional(),
        limit: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      let ps = store.players;
      if (args.nationality) {
        ps = findPlayers(ps, { nationality: args.nationality });
      }
      const summaries = playersByClub(ps);
      return text(formatClubSummaries(summaries, args.limit ?? 20));
    },
  );

  server.registerTool(
    'biggest_wins',
    {
      title: 'Biggest victories',
      description: 'Largest goal-margin victories across the dataset.',
      inputSchema: {
        competition: competitionSchema.optional(),
        limit: z.number().int().positive().optional(),
      },
    },
    async (args) => {
      const ms = biggestWins(store.matches, {
        competition: args.competition as Competition | undefined,
        limit: args.limit ?? 10,
      });
      return text(formatMatches(ms, args.limit ?? 10));
    },
  );

  server.registerTool(
    'overall_stats',
    {
      title: 'Overall statistics',
      description: 'Aggregated stats: average goals per match, home win rate, etc.',
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const s = overallStats(store.matches, {
        competition: args.competition as Competition | undefined,
        season: args.season,
      });
      return text(formatOverallStats(s));
    },
  );

  server.registerTool(
    'seasons_available',
    {
      title: 'Seasons available',
      description: 'List seasons present in the dataset.',
      inputSchema: {
        competition: competitionSchema.optional(),
      },
    },
    async (args) => {
      const rows = seasonsAvailable(
        store.matches,
        args.competition as Competition | undefined,
      );
      if (rows.length === 0) return text('No seasons found.');
      const lines = rows.map((r) => `- ${r.season}: ${r.matches} matches`);
      return text(lines.join('\n'));
    },
  );

  return server;
}
