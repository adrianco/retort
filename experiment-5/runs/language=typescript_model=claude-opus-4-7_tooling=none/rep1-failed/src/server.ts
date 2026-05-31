#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { loadAll } from './dataLoader.js';
import {
  findMatches,
  headToHead,
  teamStats,
  standings,
  findPlayers,
  aggregateStats,
  biggestWins,
  listCompetitions,
  listSeasons,
} from './queries.js';
import {
  formatMatches,
  formatTeamRecord,
  formatStandings,
  formatPlayers,
  formatHeadToHead,
  formatAggregate,
} from './format.js';

const competitionSchema = z
  .enum(['Brasileirao', 'Copa do Brasil', 'Libertadores', 'BR-Football', 'Historical Brasileirao'])
  .optional()
  .describe('Competition to restrict the query to');

export function buildServer() {
  const store = loadAll();
  const server = new McpServer({
    name: 'brazilian-soccer-mcp',
    version: '1.0.0',
  });

  server.registerTool(
    'find_matches',
    {
      description:
        'Find matches by team, competition, season, date range. Filters can be combined.',
      inputSchema: {
        team: z.string().optional().describe('Team name (matches home or away)'),
        opponent: z.string().optional().describe('Opponent team name'),
        homeTeam: z.string().optional(),
        awayTeam: z.string().optional(),
        season: z.number().int().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
        dateFrom: z.string().optional().describe('ISO date YYYY-MM-DD'),
        dateTo: z.string().optional().describe('ISO date YYYY-MM-DD'),
        competition: competitionSchema,
        limit: z.number().int().positive().optional().default(50),
      },
    },
    async (args) => {
      const matches = findMatches(store, args);
      return {
        content: [
          {
            type: 'text',
            text:
              `Found ${matches.length} match(es).\n` + formatMatches(matches),
          },
        ],
      };
    }
  );

  server.registerTool(
    'head_to_head',
    {
      description:
        'Get head-to-head record and matches between two teams across all competitions.',
      inputSchema: {
        teamA: z.string(),
        teamB: z.string(),
      },
    },
    async ({ teamA, teamB }) => {
      const h = headToHead(store, teamA, teamB);
      return {
        content: [{ type: 'text', text: formatHeadToHead(h) }],
      };
    }
  );

  server.registerTool(
    'team_stats',
    {
      description:
        'Get win/draw/loss/goals statistics for a team, optionally filtered by season, competition, and home/away venue.',
      inputSchema: {
        team: z.string(),
        season: z.number().int().optional(),
        competition: competitionSchema,
        venue: z.enum(['home', 'away', 'all']).optional().default('all'),
      },
    },
    async (args) => {
      const r = teamStats(store, args);
      return {
        content: [{ type: 'text', text: formatTeamRecord(r) }],
      };
    }
  );

  server.registerTool(
    'standings',
    {
      description:
        'Compute final-standings table for a competition+season from match results.',
      inputSchema: {
        season: z.number().int(),
        competition: competitionSchema,
      },
    },
    async ({ season, competition }) => {
      const table = standings(store, { season, competition });
      return {
        content: [{ type: 'text', text: formatStandings(table) }],
      };
    }
  );

  server.registerTool(
    'find_players',
    {
      description:
        'Search FIFA player database by name, nationality, club, position, or rating range.',
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        minOverall: z.number().int().optional(),
        maxOverall: z.number().int().optional(),
        sortBy: z.enum(['overall', 'potential', 'age', 'name']).optional(),
        limit: z.number().int().positive().optional().default(20),
      },
    },
    async (args) => {
      const players = findPlayers(store, args);
      return {
        content: [
          {
            type: 'text',
            text: `Found ${players.length} player(s).\n` + formatPlayers(players),
          },
        ],
      };
    }
  );

  server.registerTool(
    'aggregate_stats',
    {
      description:
        'Compute aggregate statistics (avg goals/match, home win rate, etc.) for a filtered set of matches.',
      inputSchema: {
        team: z.string().optional(),
        competition: competitionSchema,
        season: z.number().int().optional(),
        seasonFrom: z.number().int().optional(),
        seasonTo: z.number().int().optional(),
      },
    },
    async (args) => {
      const stats = aggregateStats(store, args);
      return {
        content: [{ type: 'text', text: formatAggregate(stats) }],
      };
    }
  );

  server.registerTool(
    'biggest_wins',
    {
      description: 'Show the biggest victories by goal margin in the dataset (optionally filtered).',
      inputSchema: {
        competition: competitionSchema,
        season: z.number().int().optional(),
        team: z.string().optional(),
        limit: z.number().int().positive().optional().default(10),
      },
    },
    async (args) => {
      const matches = biggestWins(store, args);
      return {
        content: [{ type: 'text', text: formatMatches(matches) }],
      };
    }
  );

  server.registerTool(
    'list_competitions',
    {
      description: 'List all available competitions in the dataset.',
      inputSchema: {},
    },
    async () => ({
      content: [{ type: 'text', text: listCompetitions(store).join('\n') }],
    })
  );

  server.registerTool(
    'list_seasons',
    {
      description: 'List all available seasons (optionally for a competition).',
      inputSchema: {
        competition: competitionSchema,
      },
    },
    async ({ competition }) => ({
      content: [
        {
          type: 'text',
          text: listSeasons(store, competition).join(', '),
        },
      ],
    })
  );

  return { server, store };
}

async function main() {
  const { server, store } = buildServer();
  process.stderr.write(
    `Brazilian Soccer MCP loaded ${store.matches.length} matches, ${store.players.length} players from ${store.dataDir}\n`
  );
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

const isDirectInvocation = (() => {
  try {
    const invoked = process.argv[1] ? new URL(`file://${process.argv[1]}`).href : '';
    return invoked === import.meta.url;
  } catch {
    return false;
  }
})();

if (isDirectInvocation) {
  main().catch((err) => {
    process.stderr.write(`Fatal: ${err instanceof Error ? err.stack : String(err)}\n`);
    process.exit(1);
  });
}
