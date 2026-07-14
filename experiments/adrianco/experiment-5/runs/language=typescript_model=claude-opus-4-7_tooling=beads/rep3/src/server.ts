#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { loadAll, defaultDataDir } from './loader.js';
import {
  findMatches,
  headToHead,
  teamStats,
  computeStandings,
  findPlayers,
  biggestWins,
  aggregateStats,
  topScoringTeams,
  clubRoster,
} from './queries.js';
import {
  formatMatchList,
  formatTeamStats,
  formatHeadToHead,
  formatStandings,
  formatPlayerList,
  formatAggregate,
  formatMatch,
} from './format.js';
import { Competition, DataStore } from './types.js';

const competitionEnum = z.enum([
  'Brasileirao',
  'Copa do Brasil',
  'Libertadores',
  'BR-Football',
  'Historical',
]);

function textResult(text: string) {
  return { content: [{ type: 'text' as const, text }] };
}

export async function buildServer(dataDir?: string): Promise<{
  server: McpServer;
  store: DataStore;
}> {
  const store = await loadAll(dataDir ?? defaultDataDir());

  const server = new McpServer({
    name: 'brazilian-soccer-mcp',
    version: '1.0.0',
  });

  server.registerTool(
    'find_matches',
    {
      description:
        'Find matches by team, opponent, date range, season, or competition. Team names are normalized (e.g. "Palmeiras-SP" matches "Palmeiras").',
      inputSchema: {
        team: z.string().optional().describe('Team name (matches home or away)'),
        opponent: z
          .string()
          .optional()
          .describe('Opponent team name (combine with team for h2h listing)'),
        homeTeam: z.string().optional(),
        awayTeam: z.string().optional(),
        season: z.number().int().optional(),
        fromDate: z.string().optional().describe('ISO date YYYY-MM-DD inclusive'),
        toDate: z.string().optional().describe('ISO date YYYY-MM-DD inclusive'),
        competition: competitionEnum.optional(),
        limit: z.number().int().min(1).max(500).optional().default(50),
      },
    },
    async (args) => {
      const matches = findMatches(store, {
        team: args.team,
        opponent: args.opponent,
        homeTeam: args.homeTeam,
        awayTeam: args.awayTeam,
        season: args.season,
        fromDate: args.fromDate,
        toDate: args.toDate,
        competition: args.competition as Competition | undefined,
      });
      return textResult(formatMatchList(matches, args.limit ?? 50));
    }
  );

  server.registerTool(
    'head_to_head',
    {
      description:
        'Head-to-head record between two teams across the dataset (optionally filter by competition or season).',
      inputSchema: {
        teamA: z.string(),
        teamB: z.string(),
        competition: competitionEnum.optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const h = headToHead(store, args.teamA, args.teamB, {
        competition: args.competition as Competition | undefined,
        season: args.season,
      });
      return textResult(formatHeadToHead(h));
    }
  );

  server.registerTool(
    'team_stats',
    {
      description:
        'Aggregate W/D/L, goals and points for a team, optionally filtered by season, competition, or venue (home/away).',
      inputSchema: {
        team: z.string(),
        season: z.number().int().optional(),
        competition: competitionEnum.optional(),
        venue: z.enum(['home', 'away', 'all']).optional().default('all'),
      },
    },
    async (args) => {
      const stats = teamStats(store, args.team, {
        season: args.season,
        competition: args.competition as Competition | undefined,
        venue: args.venue ?? 'all',
      });
      const label =
        `Stats: ${args.team}` +
        (args.season ? ` (${args.season})` : '') +
        (args.competition ? ` ${args.competition}` : '') +
        (args.venue && args.venue !== 'all' ? ` [${args.venue}]` : '');
      return textResult(formatTeamStats(stats, label));
    }
  );

  server.registerTool(
    'standings',
    {
      description:
        'Compute league table for a competition and season from match results (3 pts win, 1 pt draw).',
      inputSchema: {
        competition: competitionEnum,
        season: z.number().int(),
        limit: z.number().int().min(1).max(40).optional().default(30),
      },
    },
    async (args) => {
      const standings = computeStandings(
        store,
        args.competition as Competition,
        args.season
      );
      const header = `${args.competition} ${args.season} standings:`;
      return textResult(`${header}\n${formatStandings(standings, args.limit ?? 30)}`);
    }
  );

  server.registerTool(
    'find_players',
    {
      description:
        'Search the FIFA player database by name, nationality, club, position, or rating range.',
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().optional(),
        maxOverall: z.number().int().optional(),
        limit: z.number().int().min(1).max(200).optional().default(25),
      },
    },
    async (args) => {
      const players = findPlayers(store, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
        maxOverall: args.maxOverall,
        limit: args.limit ?? 25,
      });
      return textResult(formatPlayerList(players, args.limit ?? 25));
    }
  );

  server.registerTool(
    'club_roster',
    {
      description: 'List all FIFA players for a given club, sorted by Overall rating.',
      inputSchema: {
        club: z.string(),
      },
    },
    async (args) => {
      const r = clubRoster(store, args.club);
      const head = `${args.club}: ${r.players.length} players (avg overall: ${r.averageOverall.toFixed(1)})`;
      return textResult(`${head}\n${formatPlayerList(r.players, 50)}`);
    }
  );

  server.registerTool(
    'biggest_wins',
    {
      description:
        'List the matches with the largest goal differential, optionally restricted by competition and season.',
      inputSchema: {
        competition: competitionEnum.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().min(1).max(50).optional().default(10),
      },
    },
    async (args) => {
      const wins = biggestWins(store, {
        competition: args.competition as Competition | undefined,
        season: args.season,
        limit: args.limit ?? 10,
      });
      if (wins.length === 0) return textResult('No matches found.');
      const lines = wins.map((m, i) => `${i + 1}. ${formatMatch(m)}`);
      return textResult(lines.join('\n'));
    }
  );

  server.registerTool(
    'aggregate_stats',
    {
      description:
        'Aggregate statistics (avg goals/match, home/away win rates) across a competition or season.',
      inputSchema: {
        competition: competitionEnum.optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) => {
      const agg = aggregateStats(store, {
        competition: args.competition as Competition | undefined,
        season: args.season,
      });
      const label = [args.competition, args.season].filter(Boolean).join(' ');
      return textResult(formatAggregate(agg, label || 'All data'));
    }
  );

  server.registerTool(
    'top_scoring_teams',
    {
      description: 'Rank teams by goals scored, optionally per competition/season.',
      inputSchema: {
        competition: competitionEnum.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().min(1).max(40).optional().default(10),
      },
    },
    async (args) => {
      const list = topScoringTeams(store, {
        competition: args.competition as Competition | undefined,
        season: args.season,
        limit: args.limit ?? 10,
      });
      if (list.length === 0) return textResult('No data.');
      const lines = list.map(
        (t, i) => `${i + 1}. ${t.team} — ${t.goalsFor} goals in ${t.played} matches`
      );
      return textResult(lines.join('\n'));
    }
  );

  server.registerTool(
    'dataset_overview',
    {
      description: 'Summary of the loaded datasets: counts per competition and player count.',
      inputSchema: {},
    },
    async () => {
      const counts: Record<string, number> = {};
      for (const m of store.matches) {
        counts[m.competition] = (counts[m.competition] ?? 0) + 1;
      }
      const seasons = new Set(store.matches.map((m) => m.season));
      const lines = [
        `Loaded ${store.matches.length} matches across ${seasons.size} seasons.`,
        ...Object.entries(counts)
          .sort((a, b) => b[1] - a[1])
          .map(([k, v]) => `- ${k}: ${v} matches`),
        `Loaded ${store.players.length} players.`,
      ];
      return textResult(lines.join('\n'));
    }
  );

  return { server, store };
}

async function main() {
  const { server } = await buildServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // eslint-disable-next-line no-console
  console.error('brazilian-soccer-mcp server ready on stdio');
}

const invokedDirectly = (() => {
  try {
    const argv1 = process.argv[1];
    if (!argv1) return false;
    return (
      import.meta.url === `file://${argv1}` ||
      import.meta.url.endsWith(argv1.replace(/^\//, ''))
    );
  } catch {
    return false;
  }
})();

if (invokedDirectly) {
  main().catch((err) => {
    // eslint-disable-next-line no-console
    console.error('Fatal:', err);
    process.exit(1);
  });
}
