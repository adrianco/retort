import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import path from 'path';
import { fileURLToPath } from 'url';
import { loadAllData } from './dataLoader.js';
import {
  handleFindMatches,
  handleHeadToHead,
  handleTeamRecord,
  handleStandings,
  handleSearchPlayers,
  handleTopPlayers,
  handleBiggestWins,
  handleAverageGoals,
} from './handlers.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data', 'kaggle');

const server = new Server(
  { name: 'brazilian-soccer-mcp', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

let dataLoaded = false;
let data: Awaited<ReturnType<typeof loadAllData>>;

async function ensureData() {
  if (!dataLoaded) {
    data = await loadAllData(DATA_DIR);
    dataLoaded = true;
  }
}

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'find_matches',
      description: 'Find soccer matches by team, competition, season, or opponent. Searches across Brasileirão, Copa do Brasil, and Libertadores datasets.',
      inputSchema: {
        type: 'object',
        properties: {
          team: { type: 'string', description: 'Team name to search for (partial match supported)' },
          opponent: { type: 'string', description: 'Opponent team name (use with team to find head-to-head matches)' },
          competition: {
            type: 'string',
            enum: ['Brasileirao', 'Copa do Brasil', 'Libertadores', 'Brasileirao-Historical'],
            description: 'Competition to filter by (Brasileirao: 2012-2022, Brasileirao-Historical: 2003-2019)',
          },
          season: { type: 'number', description: 'Season year (e.g., 2019)' },
          limit: { type: 'number', description: 'Maximum number of matches to return (default: 20)' },
        },
      },
    },
    {
      name: 'get_head_to_head',
      description: 'Get head-to-head record between two teams, including win/draw/loss counts and recent matches.',
      inputSchema: {
        type: 'object',
        required: ['teamA', 'teamB'],
        properties: {
          teamA: { type: 'string', description: 'First team name' },
          teamB: { type: 'string', description: 'Second team name' },
          competition: { type: 'string', description: 'Filter by competition' },
          season: { type: 'number', description: 'Filter by season' },
        },
      },
    },
    {
      name: 'get_team_record',
      description: 'Get a team\'s win/draw/loss record with goals scored and conceded. Can filter by season, competition, or home/away.',
      inputSchema: {
        type: 'object',
        required: ['team'],
        properties: {
          team: { type: 'string', description: 'Team name' },
          season: { type: 'number', description: 'Filter by season year' },
          competition: {
            type: 'string',
            enum: ['Brasileirao', 'Copa do Brasil', 'Libertadores', 'Brasileirao-Historical'],
            description: 'Filter by competition',
          },
          homeOnly: { type: 'boolean', description: 'Only include home matches' },
          awayOnly: { type: 'boolean', description: 'Only include away matches' },
        },
      },
    },
    {
      name: 'get_standings',
      description: 'Get competition standings/table for a given season, calculated from match results.',
      inputSchema: {
        type: 'object',
        required: ['season', 'competition'],
        properties: {
          season: { type: 'number', description: 'Season year (e.g., 2019)' },
          competition: {
            type: 'string',
            enum: ['Brasileirao', 'Copa do Brasil', 'Libertadores', 'Brasileirao-Historical'],
            description: 'Competition name',
          },
        },
      },
    },
    {
      name: 'search_players',
      description: 'Search FIFA player database by name, nationality, club, or position.',
      inputSchema: {
        type: 'object',
        properties: {
          name: { type: 'string', description: 'Player name (partial match)' },
          nationality: { type: 'string', description: 'Player nationality (e.g., "Brazil")' },
          club: { type: 'string', description: 'Club name (partial match)' },
          position: { type: 'string', description: 'Playing position (e.g., "ST", "GK", "CAM")' },
          minOverall: { type: 'number', description: 'Minimum FIFA overall rating' },
          limit: { type: 'number', description: 'Maximum results to return (default: 20)' },
        },
      },
    },
    {
      name: 'get_top_players',
      description: 'Get top-rated players, optionally filtered by nationality, club, or position.',
      inputSchema: {
        type: 'object',
        properties: {
          nationality: { type: 'string', description: 'Filter by nationality (e.g., "Brazil")' },
          club: { type: 'string', description: 'Filter by club name' },
          position: { type: 'string', description: 'Filter by position' },
          limit: { type: 'number', description: 'Number of top players to return (default: 10)' },
        },
      },
    },
    {
      name: 'get_biggest_wins',
      description: 'Get the biggest victories (by goal difference) across all matches or filtered by competition/team/season.',
      inputSchema: {
        type: 'object',
        properties: {
          competition: {
            type: 'string',
            enum: ['Brasileirao', 'Copa do Brasil', 'Libertadores', 'Brasileirao-Historical'],
            description: 'Filter by competition',
          },
          season: { type: 'number', description: 'Filter by season' },
          team: { type: 'string', description: 'Filter by team' },
          limit: { type: 'number', description: 'Number of results (default: 10)' },
        },
      },
    },
    {
      name: 'get_average_goals',
      description: 'Get average goals per match statistics, optionally filtered by competition or season.',
      inputSchema: {
        type: 'object',
        properties: {
          competition: {
            type: 'string',
            enum: ['Brasileirao', 'Copa do Brasil', 'Libertadores', 'Brasileirao-Historical'],
            description: 'Filter by competition',
          },
          season: { type: 'number', description: 'Filter by season' },
        },
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  await ensureData();

  const { name, arguments: args } = request.params;
  const params = (args ?? {}) as Record<string, unknown>;

  try {
    let result: unknown;

    switch (name) {
      case 'find_matches':
        result = handleFindMatches(data, {
          team: params['team'] as string | undefined,
          opponent: params['opponent'] as string | undefined,
          competition: params['competition'] as string | undefined,
          season: params['season'] as number | undefined,
          limit: params['limit'] as number | undefined,
        });
        break;

      case 'get_head_to_head':
        result = handleHeadToHead(data, {
          teamA: params['teamA'] as string,
          teamB: params['teamB'] as string,
          competition: params['competition'] as string | undefined,
          season: params['season'] as number | undefined,
        });
        break;

      case 'get_team_record':
        result = handleTeamRecord(data, {
          team: params['team'] as string,
          season: params['season'] as number | undefined,
          competition: params['competition'] as string | undefined,
          homeOnly: params['homeOnly'] as boolean | undefined,
          awayOnly: params['awayOnly'] as boolean | undefined,
        });
        break;

      case 'get_standings':
        result = handleStandings(data, {
          season: params['season'] as number,
          competition: params['competition'] as string,
        });
        break;

      case 'search_players':
        result = handleSearchPlayers(data, {
          name: params['name'] as string | undefined,
          nationality: params['nationality'] as string | undefined,
          club: params['club'] as string | undefined,
          position: params['position'] as string | undefined,
          minOverall: params['minOverall'] as number | undefined,
          limit: params['limit'] as number | undefined,
        });
        break;

      case 'get_top_players':
        result = handleTopPlayers(data, {
          nationality: params['nationality'] as string | undefined,
          club: params['club'] as string | undefined,
          position: params['position'] as string | undefined,
          limit: params['limit'] as number | undefined,
        });
        break;

      case 'get_biggest_wins':
        result = handleBiggestWins(data, {
          competition: params['competition'] as string | undefined,
          season: params['season'] as number | undefined,
          team: params['team'] as string | undefined,
          limit: params['limit'] as number | undefined,
        });
        break;

      case 'get_average_goals':
        result = handleAverageGoals(data, {
          competition: params['competition'] as string | undefined,
          season: params['season'] as number | undefined,
        });
        break;

      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
    };
  } catch (error) {
    return {
      content: [{ type: 'text', text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write('Brazilian Soccer MCP Server running on stdio\n');
}

main().catch(err => {
  process.stderr.write(`Fatal: ${err}\n`);
  process.exit(1);
});
