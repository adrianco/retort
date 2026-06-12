import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { DataLoader } from './loader.js';
import { handleTool } from './tools.js';

export function createServer(loader: DataLoader): McpServer {
  const server = new McpServer({
    name: 'brazilian-soccer-mcp',
    version: '1.0.0',
  });

  server.tool(
    'search_matches',
    'Search for soccer matches by team, competition, season, or date range',
    {
      team: z.string().optional().describe('Search for matches involving this team (home or away)'),
      team1: z.string().optional().describe('First team for head-to-head search'),
      team2: z.string().optional().describe('Second team for head-to-head search'),
      competition: z.string().optional().describe('Competition name: Brasileirão, Copa do Brasil, Copa Libertadores'),
      season: z.number().optional().describe('Season year (e.g. 2019, 2023)'),
      date_from: z.string().optional().describe('Start date (YYYY-MM-DD)'),
      date_to: z.string().optional().describe('End date (YYYY-MM-DD)'),
      limit: z.number().optional().default(20).describe('Maximum number of results'),
    },
    async (args) => {
      const text = await handleTool(loader, 'search_matches', args);
      return { content: [{ type: 'text', text }] };
    },
  );

  server.tool(
    'get_team_stats',
    'Get statistics for a team: wins, losses, draws, goals, win rate',
    {
      team: z.string().describe('Team name'),
      competition: z.string().optional().describe('Filter by competition'),
      season: z.number().optional().describe('Filter by season year'),
      home_only: z.boolean().optional().describe('Only count home matches'),
      away_only: z.boolean().optional().describe('Only count away matches'),
    },
    async (args) => {
      const text = await handleTool(loader, 'get_team_stats', args);
      return { content: [{ type: 'text', text }] };
    },
  );

  server.tool(
    'search_players',
    'Search FIFA player database by name, nationality, club, or position',
    {
      name: z.string().optional().describe('Player name (partial match)'),
      nationality: z.string().optional().describe('Player nationality (e.g. Brazil, Argentina)'),
      club: z.string().optional().describe('Club name (partial match)'),
      position: z.string().optional().describe('Position (GK, CB, LB, RB, CM, CDM, CAM, LW, RW, ST, CF)'),
      min_overall: z.number().optional().describe('Minimum FIFA overall rating'),
      limit: z.number().optional().default(20).describe('Maximum results'),
    },
    async (args) => {
      const text = await handleTool(loader, 'search_players', args);
      return { content: [{ type: 'text', text }] };
    },
  );

  server.tool(
    'get_standings',
    'Calculate league standings for a given season and competition',
    {
      season: z.number().describe('Season year'),
      competition: z.string().optional().default('Brasileirão').describe('Competition name'),
    },
    async (args) => {
      const text = await handleTool(loader, 'get_standings', args);
      return { content: [{ type: 'text', text }] };
    },
  );

  server.tool(
    'get_statistics',
    'Get aggregated statistics: biggest wins, average goals, home win rate, top scoring teams',
    {
      type: z.enum(['biggest_wins', 'avg_goals', 'home_win_rate', 'top_scorers']).describe('Type of statistics'),
      competition: z.string().optional().describe('Filter by competition'),
      season: z.number().optional().describe('Filter by season'),
      limit: z.number().optional().default(10).describe('Number of results'),
    },
    async (args) => {
      const text = await handleTool(loader, 'get_statistics', args);
      return { content: [{ type: 'text', text }] };
    },
  );

  server.tool(
    'head_to_head',
    'Compare two teams head-to-head with full match history and record',
    {
      team1: z.string().describe('First team name'),
      team2: z.string().describe('Second team name'),
      competition: z.string().optional().describe('Filter by competition'),
      season: z.number().optional().describe('Filter by season'),
      limit: z.number().optional().default(10).describe('Number of recent matches to show'),
    },
    async (args) => {
      const text = await handleTool(loader, 'head_to_head', args);
      return { content: [{ type: 'text', text }] };
    },
  );

  return server;
}
