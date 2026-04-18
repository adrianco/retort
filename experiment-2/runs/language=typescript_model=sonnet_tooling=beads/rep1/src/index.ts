import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { loadAllData } from './dataLoader.js';
import {
  searchMatches,
  getHeadToHead,
  getTeamStats,
  getStandings,
  searchPlayers,
  getStatistics,
  getBestTeams,
} from './queries.js';

// Load data at startup
const data = loadAllData();

const server = new Server(
  { name: 'brazilian-soccer-mcp', version: '1.0.0' },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'search_matches',
      description:
        'Search for matches by team, competition, season, or date range across all datasets (Brasileirão, Copa do Brasil, Libertadores, etc.)',
      inputSchema: {
        type: 'object',
        properties: {
          team: { type: 'string', description: 'Team name (home or away)' },
          homeTeam: { type: 'string', description: 'Home team name' },
          awayTeam: { type: 'string', description: 'Away team name' },
          competition: {
            type: 'string',
            description: 'Competition name (e.g., "Brasileirão", "Copa do Brasil", "Libertadores")',
          },
          season: { type: 'number', description: 'Season year (e.g., 2023)' },
          dateFrom: { type: 'string', description: 'Start date (YYYY-MM-DD)' },
          dateTo: { type: 'string', description: 'End date (YYYY-MM-DD)' },
          limit: { type: 'number', description: 'Max results (default 50)' },
        },
      },
    },
    {
      name: 'head_to_head',
      description: 'Get head-to-head record between two teams across all competitions',
      inputSchema: {
        type: 'object',
        properties: {
          team1: { type: 'string', description: 'First team name' },
          team2: { type: 'string', description: 'Second team name' },
        },
        required: ['team1', 'team2'],
      },
    },
    {
      name: 'get_team_stats',
      description: 'Get win/loss/draw statistics for a team, optionally filtered by competition or season',
      inputSchema: {
        type: 'object',
        properties: {
          team: { type: 'string', description: 'Team name' },
          competition: { type: 'string', description: 'Competition filter' },
          season: { type: 'number', description: 'Season year' },
          homeOnly: { type: 'boolean', description: 'Only home matches' },
          awayOnly: { type: 'boolean', description: 'Only away matches' },
        },
        required: ['team'],
      },
    },
    {
      name: 'get_standings',
      description: 'Calculate league standings for a competition and season',
      inputSchema: {
        type: 'object',
        properties: {
          competition: {
            type: 'string',
            description: 'Competition name (e.g., "Brasileirão")',
          },
          season: { type: 'number', description: 'Season year' },
        },
        required: ['competition', 'season'],
      },
    },
    {
      name: 'search_players',
      description: 'Search FIFA player database by name, nationality, club, or position',
      inputSchema: {
        type: 'object',
        properties: {
          name: { type: 'string', description: 'Player name (partial match)' },
          nationality: { type: 'string', description: 'Player nationality (e.g., "Brazil")' },
          club: { type: 'string', description: 'Club name (e.g., "Flamengo")' },
          position: { type: 'string', description: 'Playing position (e.g., "GK", "ST", "LW")' },
          minOverall: { type: 'number', description: 'Minimum overall rating' },
          limit: { type: 'number', description: 'Max results (default 50)' },
        },
      },
    },
    {
      name: 'get_statistics',
      description: 'Get aggregate statistics for a competition or all matches (goals per match, home win rate, biggest wins, etc.)',
      inputSchema: {
        type: 'object',
        properties: {
          competition: { type: 'string', description: 'Competition filter (optional)' },
          season: { type: 'number', description: 'Season filter (optional)' },
        },
      },
    },
    {
      name: 'get_best_teams',
      description: 'Get the best teams ranked by win rate for home, away, or overall performance',
      inputSchema: {
        type: 'object',
        properties: {
          metric: {
            type: 'string',
            enum: ['home', 'away', 'overall'],
            description: 'Performance metric to rank by',
          },
          competition: { type: 'string', description: 'Competition filter (optional)' },
          season: { type: 'number', description: 'Season filter (optional)' },
          limit: { type: 'number', description: 'Max results (default 10)' },
        },
        required: ['metric'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'search_matches': {
        const matches = searchMatches(data.matches, args as Parameters<typeof searchMatches>[1]);
        if (matches.length === 0) {
          return { content: [{ type: 'text', text: 'No matches found for the given criteria.' }] };
        }
        const lines = matches.map(
          (m) =>
            `${m.date} | ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} | ${m.competition} ${m.season}${m.round ? ` Round ${m.round}` : ''}${m.stage ? ` (${m.stage})` : ''}`,
        );
        return {
          content: [
            {
              type: 'text',
              text: `Found ${matches.length} match(es):\n\n${lines.join('\n')}`,
            },
          ],
        };
      }

      case 'head_to_head': {
        const { team1, team2 } = args as { team1: string; team2: string };
        const h2h = getHeadToHead(data.matches, team1, team2);
        const lines = h2h.matches.slice(0, 20).map(
          (m) =>
            `${m.date} | ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} | ${m.competition} ${m.season}`,
        );
        const summary = `Head-to-head: ${team1} ${h2h.team1Wins} wins | Draws ${h2h.draws} | ${team2} ${h2h.team2Wins} wins\nTotal matches: ${h2h.matches.length}`;
        const matchList = lines.length > 0 ? `\n\nRecent matches (up to 20):\n${lines.join('\n')}` : '';
        return {
          content: [{ type: 'text', text: summary + matchList }],
        };
      }

      case 'get_team_stats': {
        const stats = getTeamStats(data.matches, args as unknown as Parameters<typeof getTeamStats>[1]);
        const gd = stats.goalsFor - stats.goalsAgainst;
        const text = [
          `Team: ${stats.team}`,
          `Matches: ${stats.matches}`,
          `Wins: ${stats.wins} | Draws: ${stats.draws} | Losses: ${stats.losses}`,
          `Goals For: ${stats.goalsFor} | Goals Against: ${stats.goalsAgainst} | GD: ${gd > 0 ? '+' : ''}${gd}`,
          `Points: ${stats.points}`,
          `Win Rate: ${stats.winRate.toFixed(1)}%`,
        ].join('\n');
        return { content: [{ type: 'text', text }] };
      }

      case 'get_standings': {
        const { competition, season } = args as { competition: string; season: number };
        const standings = getStandings(data.matches, competition, season);
        if (standings.length === 0) {
          return {
            content: [{ type: 'text', text: `No data found for ${competition} ${season}` }],
          };
        }
        const lines = standings.map((s, i) => {
          const gd = s.goalsFor - s.goalsAgainst;
          return `${i + 1}. ${s.team} | Pts: ${s.points} | W${s.wins} D${s.draws} L${s.losses} | GF:${s.goalsFor} GA:${s.goalsAgainst} GD:${gd > 0 ? '+' : ''}${gd}`;
        });
        return {
          content: [
            {
              type: 'text',
              text: `${competition} ${season} Standings:\n\n${lines.join('\n')}`,
            },
          ],
        };
      }

      case 'search_players': {
        const players = searchPlayers(data.players, args as Parameters<typeof searchPlayers>[1]);
        if (players.length === 0) {
          return { content: [{ type: 'text', text: 'No players found.' }] };
        }
        const lines = players.map(
          (p) =>
            `${p.name} | ${p.nationality} | ${p.position} | Club: ${p.club} | Overall: ${p.overall} | Potential: ${p.potential} | Age: ${p.age}`,
        );
        return {
          content: [
            {
              type: 'text',
              text: `Found ${players.length} player(s):\n\n${lines.join('\n')}`,
            },
          ],
        };
      }

      case 'get_statistics': {
        const { competition, season } = (args ?? {}) as { competition?: string; season?: number };
        const stats = getStatistics(data.matches, competition, season);
        const topWins = stats.biggestWins
          .slice(0, 5)
          .map(
            ({ match: m, goalDiff }) =>
              `${m.date} ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (diff: ${goalDiff}) [${m.competition} ${m.season}]`,
          );
        const text = [
          competition || season
            ? `Statistics${competition ? ' for ' + competition : ''}${season ? ' ' + season : ''}:`
            : 'Overall statistics across all datasets:',
          `Total Matches: ${stats.totalMatches}`,
          `Total Goals: ${stats.totalGoals}`,
          `Avg Goals/Match: ${stats.avgGoalsPerMatch}`,
          `Home Wins: ${stats.homeWins} (${stats.homeWinRate}%)`,
          `Away Wins: ${stats.awayWins} (${((stats.awayWins / stats.totalMatches) * 100).toFixed(1)}%)`,
          `Draws: ${stats.draws} (${((stats.draws / stats.totalMatches) * 100).toFixed(1)}%)`,
          '',
          'Biggest wins:',
          ...topWins,
        ].join('\n');
        return { content: [{ type: 'text', text }] };
      }

      case 'get_best_teams': {
        const { metric, competition, season, limit } = args as {
          metric: 'home' | 'away' | 'overall';
          competition?: string;
          season?: number;
          limit?: number;
        };
        const teams = getBestTeams(data.matches, metric, competition, season, limit ?? 10);
        if (teams.length === 0) {
          return { content: [{ type: 'text', text: 'No data found.' }] };
        }
        const lines = teams.map(
          (s, i) =>
            `${i + 1}. ${s.team} | Win Rate: ${s.winRate.toFixed(1)}% | W${s.wins} D${s.draws} L${s.losses} | GF:${s.goalsFor} GA:${s.goalsAgainst} | Matches: ${s.matches}`,
        );
        const label = metric === 'home' ? 'Home' : metric === 'away' ? 'Away' : 'Overall';
        return {
          content: [
            {
              type: 'text',
              text: `Best teams by ${label} win rate${competition ? ' in ' + competition : ''}${season ? ' ' + season : ''}:\n\n${lines.join('\n')}`,
            },
          ],
        };
      }

      default:
        return { content: [{ type: 'text', text: `Unknown tool: ${name}` }], isError: true };
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { content: [{ type: 'text', text: `Error: ${msg}` }], isError: true };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
