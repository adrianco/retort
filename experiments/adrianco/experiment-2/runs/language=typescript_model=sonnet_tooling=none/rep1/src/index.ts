import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';

import {
  searchMatches,
  getTeamStats,
  getHeadToHead,
  getStandings,
  getBiggestWins,
  getCompetitionStats,
  searchPlayers,
  getBestTeams,
  getExtendedStats,
} from './queries';

const tools: Tool[] = [
  {
    name: 'search_matches',
    description:
      'Search for soccer matches across all competitions (Brasileirao, Copa do Brasil, Libertadores, Historical). ' +
      'Filter by team, competition, season, or date range.',
    inputSchema: {
      type: 'object',
      properties: {
        team: {
          type: 'string',
          description: 'Team name to search for (home or away)',
        },
        team1: {
          type: 'string',
          description: 'First team for head-to-head search',
        },
        team2: {
          type: 'string',
          description: 'Second team for head-to-head search',
        },
        competition: {
          type: 'string',
          description: 'Competition filter: "Brasileirao", "Copa do Brasil", "Libertadores"',
        },
        season: {
          type: 'number',
          description: 'Season year (e.g., 2023)',
        },
        date_from: {
          type: 'string',
          description: 'Start date filter (YYYY-MM-DD)',
        },
        date_to: {
          type: 'string',
          description: 'End date filter (YYYY-MM-DD)',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results to return (default 50)',
        },
      },
    },
  },
  {
    name: 'get_team_stats',
    description:
      'Get win/loss/draw statistics for a team. Optionally filter by competition, season, or home/away games.',
    inputSchema: {
      type: 'object',
      required: ['team'],
      properties: {
        team: { type: 'string', description: 'Team name' },
        competition: { type: 'string', description: 'Competition filter' },
        season: { type: 'number', description: 'Season year' },
        home_only: { type: 'boolean', description: 'Only include home matches' },
        away_only: { type: 'boolean', description: 'Only include away matches' },
      },
    },
  },
  {
    name: 'head_to_head',
    description: 'Get head-to-head record between two teams including all matches and aggregate stats.',
    inputSchema: {
      type: 'object',
      required: ['team1', 'team2'],
      properties: {
        team1: { type: 'string', description: 'First team name' },
        team2: { type: 'string', description: 'Second team name' },
        limit: { type: 'number', description: 'Max recent matches to show (default 20)' },
      },
    },
  },
  {
    name: 'get_standings',
    description:
      'Calculate league standings for a given season and competition from match results.',
    inputSchema: {
      type: 'object',
      required: ['season'],
      properties: {
        season: { type: 'number', description: 'Season year (e.g., 2019)' },
        competition: {
          type: 'string',
          description: 'Competition name (default: "Brasileirao")',
        },
      },
    },
  },
  {
    name: 'get_biggest_wins',
    description: 'Find the biggest winning margins in the dataset.',
    inputSchema: {
      type: 'object',
      properties: {
        competition: { type: 'string', description: 'Competition filter' },
        season: { type: 'number', description: 'Season filter' },
        limit: { type: 'number', description: 'Number of results (default 10)' },
      },
    },
  },
  {
    name: 'get_competition_stats',
    description:
      'Get aggregate statistics for a competition (total matches, goals, home win rate, etc.).',
    inputSchema: {
      type: 'object',
      properties: {
        competition: { type: 'string', description: 'Competition name' },
        season: { type: 'number', description: 'Season year' },
      },
    },
  },
  {
    name: 'search_players',
    description:
      'Search FIFA player database by name, nationality, club, or position.',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Player name (partial match)' },
        nationality: {
          type: 'string',
          description: 'Nationality filter (e.g., "Brazil")',
        },
        club: { type: 'string', description: 'Club name filter' },
        position: { type: 'string', description: 'Position filter (e.g., "ST", "GK")' },
        min_overall: {
          type: 'number',
          description: 'Minimum FIFA overall rating',
        },
        limit: {
          type: 'number',
          description: 'Maximum results (default 20)',
        },
      },
    },
  },
  {
    name: 'get_best_teams',
    description:
      'Get teams ranked by win rate for home, away, or overall performance.',
    inputSchema: {
      type: 'object',
      properties: {
        mode: {
          type: 'string',
          enum: ['home', 'away', 'overall'],
          description: 'Performance mode (default: "overall")',
        },
        competition: { type: 'string', description: 'Competition filter' },
        season: { type: 'number', description: 'Season filter' },
        limit: { type: 'number', description: 'Number of teams (default 10)' },
      },
    },
  },
  {
    name: 'get_extended_stats',
    description:
      'Get extended match statistics (corners, shots, attacks) from the BR-Football-Dataset.',
    inputSchema: {
      type: 'object',
      properties: {
        team: { type: 'string', description: 'Team name filter' },
        competition: { type: 'string', description: 'Tournament filter' },
        limit: { type: 'number', description: 'Number of matches (default 20)' },
      },
    },
  },
];

function formatMatch(m: any): string {
  const score = `${m.home_team} ${m.home_goal}-${m.away_goal} ${m.away_team}`;
  const round = m.round ? ` Round ${m.round}` : '';
  const stage = m.stage ? ` (${m.stage})` : '';
  return `${m.date}: ${score} [${m.competition}${round}${stage}]`;
}

function formatPlayer(p: any): string {
  return `${p.Name} | ${p.Nationality} | ${p.Club} | Pos: ${p.Position} | Overall: ${p.Overall} | Age: ${p.Age}`;
}

function formatStats(s: any): string {
  const gd = s.goals_for - s.goals_against;
  const wr = s.matches > 0 ? ((s.wins / s.matches) * 100).toFixed(1) : '0.0';
  return (
    `Team: ${s.team}\n` +
    `Matches: ${s.matches} | W: ${s.wins} D: ${s.draws} L: ${s.losses}\n` +
    `Goals For: ${s.goals_for} | Goals Against: ${s.goals_against} | GD: ${gd}\n` +
    `Points: ${s.points} | Win Rate: ${wr}%`
  );
}

const server = new Server(
  { name: 'brazilian-soccer-mcp', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'search_matches': {
        const results = searchMatches(args as any);
        if (results.length === 0) {
          return {
            content: [{ type: 'text', text: 'No matches found for the given criteria.' }],
          };
        }
        const lines = results.map(formatMatch);
        return {
          content: [
            {
              type: 'text',
              text: `Found ${results.length} match(es):\n\n${lines.join('\n')}`,
            },
          ],
        };
      }

      case 'get_team_stats': {
        const stats = getTeamStats(args as any);
        return {
          content: [{ type: 'text', text: formatStats(stats) }],
        };
      }

      case 'head_to_head': {
        const { team1, team2, limit } = args as any;
        const result = getHeadToHead(team1, team2, limit);
        const matchLines = result.matches.map(formatMatch).join('\n');
        const summary =
          `Head-to-Head: ${result.team1} vs ${result.team2}\n` +
          `Total Matches: ${result.total_matches}\n` +
          `${result.team1} Wins: ${result.team1_wins} | ${result.team2} Wins: ${result.team2_wins} | Draws: ${result.draws}\n` +
          `Goals: ${result.team1} ${result.team1_goals} - ${result.team2_goals} ${result.team2}\n\n` +
          `Recent Matches:\n${matchLines}`;
        return { content: [{ type: 'text', text: summary }] };
      }

      case 'get_standings': {
        const { season, competition } = args as any;
        const standings = getStandings(season, competition);
        if (standings.length === 0) {
          return {
            content: [{ type: 'text', text: `No data for ${competition ?? 'Brasileirao'} ${season}.` }],
          };
        }
        const lines = standings.map((t, i) => {
          const gd = t.goals_for - t.goals_against;
          return `${i + 1}. ${t.team} - ${t.points}pts (${t.wins}W ${t.draws}D ${t.losses}L) GD:${gd > 0 ? '+' : ''}${gd}`;
        });
        return {
          content: [
            {
              type: 'text',
              text: `${competition ?? 'Brasileirao'} ${season} Standings:\n\n${lines.join('\n')}`,
            },
          ],
        };
      }

      case 'get_biggest_wins': {
        const { competition, season, limit } = args as any;
        const results = getBiggestWins(competition, season, limit);
        const lines = results.map((m: any, i: number) => {
          const margin = Math.abs(m.home_goal - m.away_goal);
          return `${i + 1}. ${formatMatch(m)} (margin: ${margin})`;
        });
        return {
          content: [{ type: 'text', text: `Biggest Wins:\n\n${lines.join('\n')}` }],
        };
      }

      case 'get_competition_stats': {
        const { competition, season } = args as any;
        const stats = getCompetitionStats(competition, season);
        const text =
          `Competition: ${stats.competition}${season ? ` (${season})` : ''}\n` +
          `Total Matches: ${stats.total_matches}\n` +
          `Total Goals: ${stats.total_goals}\n` +
          `Avg Goals/Match: ${stats.avg_goals_per_match}\n` +
          `Home Wins: ${stats.home_wins} (${stats.home_win_rate}%)\n` +
          `Away Wins: ${stats.away_wins}\n` +
          `Draws: ${stats.draws}`;
        return { content: [{ type: 'text', text }] };
      }

      case 'search_players': {
        const players = searchPlayers(args as any);
        if (players.length === 0) {
          return { content: [{ type: 'text', text: 'No players found.' }] };
        }
        const lines = players.map((p, i) => `${i + 1}. ${formatPlayer(p)}`);
        return {
          content: [
            {
              type: 'text',
              text: `Found ${players.length} player(s):\n\n${lines.join('\n')}`,
            },
          ],
        };
      }

      case 'get_best_teams': {
        const { mode, competition, season, limit } = args as any;
        const teams = getBestTeams(mode ?? 'overall', competition, season, limit);
        const lines = teams.map((t, i) => {
          const wr = t.matches > 0 ? ((t.wins / t.matches) * 100).toFixed(1) : '0.0';
          return `${i + 1}. ${t.team} - Win Rate: ${wr}% (${t.wins}W/${t.draws}D/${t.losses}L in ${t.matches} games)`;
        });
        return {
          content: [
            {
              type: 'text',
              text: `Best Teams (${mode ?? 'overall'}):\n\n${lines.join('\n')}`,
            },
          ],
        };
      }

      case 'get_extended_stats': {
        const { team, competition, limit } = args as any;
        const result = getExtendedStats(team, competition, limit);
        const matchLines = result.matches.map(
          (m) =>
            `${m.date}: ${m.home} ${m.home_goal}-${m.away_goal} ${m.away} [${m.tournament}] ` +
            `Corners: ${m.total_corners}, Shots: ${m.home_shots + m.away_shots}`
        );
        const text =
          `Extended Stats (${result.matches.length} matches):\n` +
          `Avg Corners: ${result.avg_corners} | Avg Shots: ${result.avg_shots} | Avg Attacks: ${result.avg_attacks}\n\n` +
          matchLines.join('\n');
        return { content: [{ type: 'text', text }] };
      }

      default:
        return {
          content: [{ type: 'text', text: `Unknown tool: ${name}` }],
          isError: true,
        };
    }
  } catch (err: any) {
    return {
      content: [{ type: 'text', text: `Error: ${err.message}` }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Brazilian Soccer MCP Server running on stdio');
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
