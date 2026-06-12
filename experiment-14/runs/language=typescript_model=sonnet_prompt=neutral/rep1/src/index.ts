import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { loadAllData } from './data-loader';
import {
  queryMatches,
  getTeamStats,
  getHeadToHead,
  getStandings,
  queryPlayers,
  getBiggestWins,
  getLeagueStats,
  getTopScoringTeams,
  UnifiedMatch,
  StandingsEntry,
} from './query-engine';

const server = new Server(
  { name: 'brazilian-soccer-mcp', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

// Load data once on startup
const store = loadAllData();

function formatMatch(m: UnifiedMatch): string {
  return `${m.date} | ${m.home_team} ${m.home_goal}-${m.away_goal} ${m.away_team} | ${m.competition}${m.extra ? ' | ' + m.extra : ''}`;
}

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'search_matches',
      description: 'Search for Brazilian soccer matches by team, season, date range, or competition. Returns recent matches sorted by date.',
      inputSchema: {
        type: 'object',
        properties: {
          team: { type: 'string', description: 'Team name (partial match OK). Finds matches where team played home or away.' },
          home_team: { type: 'string', description: 'Specifically search by home team name.' },
          away_team: { type: 'string', description: 'Specifically search by away team name. Use with home_team to find head-to-head.' },
          season: { type: 'number', description: 'Filter by season year (e.g. 2023).' },
          date_from: { type: 'string', description: 'Start date in YYYY-MM-DD format.' },
          date_to: { type: 'string', description: 'End date in YYYY-MM-DD format.' },
          competition: { type: 'string', description: 'Competition name: "brasileirao", "copa do brasil", "libertadores".' },
          limit: { type: 'number', description: 'Max results to return (default 50, max 200).' },
        },
      },
    },
    {
      name: 'get_team_stats',
      description: 'Get win/loss/draw statistics for a team, optionally filtered by season and competition.',
      inputSchema: {
        type: 'object',
        properties: {
          team: { type: 'string', description: 'Team name.' },
          season: { type: 'number', description: 'Season year (optional).' },
          competition: { type: 'string', description: 'Competition filter (optional).' },
        },
        required: ['team'],
      },
    },
    {
      name: 'get_head_to_head',
      description: 'Get head-to-head record between two teams across all competitions.',
      inputSchema: {
        type: 'object',
        properties: {
          team1: { type: 'string', description: 'First team name.' },
          team2: { type: 'string', description: 'Second team name.' },
          limit: { type: 'number', description: 'Number of recent matches to show (default 20).' },
        },
        required: ['team1', 'team2'],
      },
    },
    {
      name: 'get_standings',
      description: 'Get league standings for a season, calculated from match results.',
      inputSchema: {
        type: 'object',
        properties: {
          season: { type: 'number', description: 'Season year.' },
          competition: { type: 'string', description: 'Competition: "brasileirao" (default), "copa do brasil", "libertadores".' },
          limit: { type: 'number', description: 'Number of teams to show (default 20).' },
        },
        required: ['season'],
      },
    },
    {
      name: 'search_players',
      description: 'Search FIFA player database for Brazilian soccer players.',
      inputSchema: {
        type: 'object',
        properties: {
          name: { type: 'string', description: 'Player name (partial match OK).' },
          nationality: { type: 'string', description: 'Player nationality (e.g. "Brazilian").' },
          club: { type: 'string', description: 'Club name (e.g. "Flamengo").' },
          min_overall: { type: 'number', description: 'Minimum FIFA overall rating.' },
          position: { type: 'string', description: 'Position (e.g. "GK", "ST", "LW").' },
          limit: { type: 'number', description: 'Max results (default 20).' },
        },
      },
    },
    {
      name: 'get_biggest_wins',
      description: 'Find the biggest victories (largest goal differences) in the dataset.',
      inputSchema: {
        type: 'object',
        properties: {
          limit: { type: 'number', description: 'Number of results (default 10).' },
        },
      },
    },
    {
      name: 'get_league_stats',
      description: 'Get aggregate statistics for a competition: average goals, home win rates, etc.',
      inputSchema: {
        type: 'object',
        properties: {
          competition: { type: 'string', description: 'Competition name (optional, omit for all).' },
        },
      },
    },
    {
      name: 'get_top_scoring_teams',
      description: 'Find teams that scored the most goals in a season or competition.',
      inputSchema: {
        type: 'object',
        properties: {
          season: { type: 'number', description: 'Season year (optional).' },
          competition: { type: 'string', description: 'Competition filter (optional).' },
          limit: { type: 'number', description: 'Number of teams to return (default 10).' },
        },
      },
    },
    {
      name: 'get_dataset_info',
      description: 'Get information about the available datasets and their coverage.',
      inputSchema: { type: 'object', properties: {} },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'search_matches': {
        const params = args as {
          team?: string; home_team?: string; away_team?: string;
          season?: number; date_from?: string; date_to?: string;
          competition?: string; limit?: number;
        };
        const limit = Math.min(params.limit ?? 50, 200);
        const matches = queryMatches(store, { ...params, limit });

        if (matches.length === 0) {
          return { content: [{ type: 'text', text: 'No matches found for the given criteria.' }] };
        }

        const lines = matches.map(formatMatch);
        const summary = `Found ${matches.length} match(es):\n\n` + lines.join('\n');
        return { content: [{ type: 'text', text: summary }] };
      }

      case 'get_team_stats': {
        const { team, season, competition } = args as { team: string; season?: number; competition?: string };
        const stats = getTeamStats(store, team, season, competition);

        if (stats.matches === 0) {
          return { content: [{ type: 'text', text: `No matches found for team "${team}"${season ? ` in ${season}` : ''}.` }] };
        }

        const text = [
          `**${stats.team}${season ? ` (${season})` : ''}${competition ? ` — ${competition}` : ''}**`,
          `Matches: ${stats.matches}`,
          `Record: ${stats.wins}W / ${stats.draws}D / ${stats.losses}L`,
          `Points: ${stats.points}`,
          `Goals: ${stats.goals_for} scored, ${stats.goals_against} conceded (${stats.goals_for - stats.goals_against > 0 ? '+' : ''}${stats.goals_for - stats.goals_against})`,
          `Win rate: ${stats.win_rate}%`,
          `Home: ${stats.home_wins}W from ${stats.home_matches} games`,
          `Away: ${stats.away_wins}W from ${stats.away_matches} games`,
        ].join('\n');
        return { content: [{ type: 'text', text }] };
      }

      case 'get_head_to_head': {
        const { team1, team2, limit } = args as { team1: string; team2: string; limit?: number };
        const h2h = getHeadToHead(store, team1, team2, limit ?? 20);

        if (h2h.matches.length === 0) {
          return { content: [{ type: 'text', text: `No matches found between "${team1}" and "${team2}".` }] };
        }

        const lines = [
          `**${h2h.team1} vs ${h2h.team2}**`,
          `Total matches: ${h2h.team1_wins + h2h.team2_wins + h2h.draws}`,
          `${h2h.team1} wins: ${h2h.team1_wins}`,
          `${h2h.team2} wins: ${h2h.team2_wins}`,
          `Draws: ${h2h.draws}`,
          `Goals: ${h2h.team1} ${h2h.team1_goals} — ${h2h.team2_goals} ${h2h.team2}`,
          '',
          `Recent ${h2h.matches.length} matches:`,
          ...h2h.matches.map(formatMatch),
        ];
        return { content: [{ type: 'text', text: lines.join('\n') }] };
      }

      case 'get_standings': {
        const { season, competition, limit } = args as { season: number; competition?: string; limit?: number };
        const standings = getStandings(store, season, competition ?? 'brasileirao');
        const top = standings.slice(0, limit ?? 20);

        if (top.length === 0) {
          return { content: [{ type: 'text', text: `No standings data found for ${season}.` }] };
        }

        const header = `**${competition ?? 'Brasileirão'} ${season} Standings**\n`;
        const rows = top.map((t: StandingsEntry) =>
          `${String(t.position).padStart(2)}. ${t.team.padEnd(30)} ${String(t.points).padStart(3)}pts  ${t.wins}W ${t.draws}D ${t.losses}L  GD:${t.goal_diff > 0 ? '+' : ''}${t.goal_diff}`
        );
        return { content: [{ type: 'text', text: header + rows.join('\n') }] };
      }

      case 'search_players': {
        const params = args as {
          name?: string; nationality?: string; club?: string;
          min_overall?: number; position?: string; limit?: number;
        };
        const players = queryPlayers(store, params);

        if (players.length === 0) {
          return { content: [{ type: 'text', text: 'No players found for the given criteria.' }] };
        }

        const rows = players.map((p, i) =>
          `${i + 1}. ${p.name} | ${p.nationality} | ${p.club} | ${p.position} | OVR: ${p.overall} | POT: ${p.potential} | Age: ${p.age}`
        );
        return { content: [{ type: 'text', text: `Found ${players.length} player(s):\n\n` + rows.join('\n') }] };
      }

      case 'get_biggest_wins': {
        const { limit } = args as { limit?: number };
        const wins = getBiggestWins(store, limit ?? 10);
        const rows = wins.map((w, i) =>
          `${i + 1}. ${w.date} | ${w.home_team} ${w.home_goal}-${w.away_goal} ${w.away_team} (diff: ${w.goal_diff}) | ${w.competition}`
        );
        return { content: [{ type: 'text', text: `**Biggest Wins in Dataset:**\n\n` + rows.join('\n') }] };
      }

      case 'get_league_stats': {
        const { competition } = args as { competition?: string };
        const stats = getLeagueStats(store, competition);
        const text = [
          `**League Statistics${competition ? ': ' + competition : ' (All Competitions)'}**`,
          `Total matches: ${stats.total_matches}`,
          `Total goals: ${stats.total_goals}`,
          `Avg goals/match: ${stats.avg_goals_per_match}`,
          `Home wins: ${stats.home_wins} (${stats.home_win_rate}%)`,
          `Away wins: ${stats.away_wins}`,
          `Draws: ${stats.draws}`,
        ].join('\n');
        return { content: [{ type: 'text', text }] };
      }

      case 'get_top_scoring_teams': {
        const { season, competition, limit } = args as { season?: number; competition?: string; limit?: number };
        const teams = getTopScoringTeams(store, season, competition, limit ?? 10);
        const rows = teams.map((t, i) =>
          `${i + 1}. ${t.team} — ${t.goals} goals in ${t.matches} matches (avg: ${t.avg}/game)`
        );
        const title = `**Top Scoring Teams${season ? ' ' + season : ''}${competition ? ' — ' + competition : ''}:**\n\n`;
        return { content: [{ type: 'text', text: title + rows.join('\n') }] };
      }

      case 'get_dataset_info': {
        const text = [
          '**Brazilian Soccer MCP — Dataset Coverage**',
          '',
          `Brasileirão Serie A: ${store.brasileirao.length} matches (${Math.min(...store.brasileirao.map(m => m.season))}–${Math.max(...store.brasileirao.map(m => m.season))})`,
          `Copa do Brasil: ${store.copa.length} matches (${Math.min(...store.copa.map(m => m.season))}–${Math.max(...store.copa.map(m => m.season))})`,
          `Copa Libertadores: ${store.libertadores.length} matches (${Math.min(...store.libertadores.map(m => m.season))}–${Math.max(...store.libertadores.map(m => m.season))})`,
          `Extended Match Stats: ${store.extended.length} matches`,
          `Historical Brasileirão (2003–2019): ${store.historical.length} matches`,
          `FIFA Players: ${store.players.length} players`,
          '',
          '**Available Tools:**',
          '- search_matches: Find matches by team, date, season, competition',
          '- get_team_stats: Win/loss/draw records for any team',
          '- get_head_to_head: Head-to-head record between two teams',
          '- get_standings: League table for a given season',
          '- search_players: Search FIFA player database',
          '- get_biggest_wins: Largest winning margins in dataset',
          '- get_league_stats: Aggregate stats (avg goals, home win rate)',
          '- get_top_scoring_teams: Teams with most goals',
        ].join('\n');
        return { content: [{ type: 'text', text }] };
      }

      default:
        return { content: [{ type: 'text', text: `Unknown tool: ${name}` }], isError: true };
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { content: [{ type: 'text', text: `Error: ${message}` }], isError: true };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Brazilian Soccer MCP server running on stdio');
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
