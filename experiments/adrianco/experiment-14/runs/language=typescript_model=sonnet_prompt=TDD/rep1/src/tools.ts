import type { DataLoader } from './loader.js';
import type { NormalizedMatch } from './types.js';
import {
  searchMatches,
  getTeamStats,
  headToHead,
  getStandings,
  getStatistics,
  type SearchMatchesParams,
} from './queries.js';
import { searchPlayers } from './players.js';

function formatMatch(m: NormalizedMatch): string {
  const score = `${m.home_goals}-${m.away_goals}`;
  const round = m.round ? ` (Round ${m.round})` : m.stage ? ` (${m.stage})` : '';
  return `${m.date}: ${m.home_team} ${score} ${m.away_team} [${m.competition}${round}]`;
}

export async function handleTool(
  loader: DataLoader,
  toolName: string,
  args: Record<string, unknown>,
): Promise<string> {
  switch (toolName) {
    case 'search_matches':
      return handleSearchMatches(loader, args);
    case 'get_team_stats':
      return handleGetTeamStats(loader, args);
    case 'search_players':
      return handleSearchPlayers(loader, args);
    case 'get_standings':
      return handleGetStandings(loader, args);
    case 'get_statistics':
      return handleGetStatistics(loader, args);
    case 'head_to_head':
      return handleHeadToHead(loader, args);
    default:
      return `Unknown tool: ${toolName}`;
  }
}

function handleSearchMatches(loader: DataLoader, args: Record<string, unknown>): string {
  const params: SearchMatchesParams = {
    team: args['team'] as string | undefined,
    team1: args['team1'] as string | undefined,
    team2: args['team2'] as string | undefined,
    competition: args['competition'] as string | undefined,
    season: args['season'] as number | undefined,
    dateFrom: args['date_from'] as string | undefined,
    dateTo: args['date_to'] as string | undefined,
    limit: (args['limit'] as number | undefined) ?? 20,
  };

  const matches = searchMatches(loader, params);
  if (matches.length === 0) {
    return 'No matches found for the given criteria.';
  }

  const lines: string[] = [];

  if (params.team1 && params.team2) {
    const h2h = headToHead(loader, params.team1, params.team2, params.competition, params.season);
    lines.push(`Head-to-head: ${params.team1} vs ${params.team2}`);
    lines.push(`Total: ${h2h.matches.length} matches | ${params.team1} wins: ${h2h.team1_wins} | ${params.team2} wins: ${h2h.team2_wins} | Draws: ${h2h.draws}`);
    lines.push('');
  }

  lines.push(`Found ${matches.length} match(es):`);
  matches.slice(0, params.limit ?? 20).forEach((m) => lines.push(`  ${formatMatch(m)}`));

  return lines.join('\n');
}

function handleGetTeamStats(loader: DataLoader, args: Record<string, unknown>): string {
  const team = args['team'] as string;
  const season = args['season'] as number | undefined;
  const competition = args['competition'] as string | undefined;
  const homeOnly = args['home_only'] as boolean | undefined;
  const awayOnly = args['away_only'] as boolean | undefined;

  const stats = getTeamStats(loader, { team, season, competition, homeOnly, awayOnly });
  if (!stats) {
    return `No data found for team: ${team}`;
  }

  const winRate = stats.matches > 0 ? ((stats.wins / stats.matches) * 100).toFixed(1) : '0.0';
  const gd = stats.goals_for - stats.goals_against;
  const context = [competition, season ? String(season) : undefined].filter(Boolean).join(' ');

  const lines = [
    `${team} Statistics${context ? ` (${context})` : ''}:`,
    `  Matches: ${stats.matches}`,
    `  Wins: ${stats.wins} | Draws: ${stats.draws} | Losses: ${stats.losses}`,
    `  Goals For: ${stats.goals_for} | Goals Against: ${stats.goals_against} | GD: ${gd > 0 ? '+' : ''}${gd}`,
    `  Points: ${stats.points}`,
    `  Win rate: ${winRate}%`,
  ];

  return lines.join('\n');
}

function handleSearchPlayers(loader: DataLoader, args: Record<string, unknown>): string {
  const name = args['name'] as string | undefined;
  const nationality = args['nationality'] as string | undefined;
  const club = args['club'] as string | undefined;
  const position = args['position'] as string | undefined;
  const minOverall = args['min_overall'] as number | undefined;
  const limit = (args['limit'] as number | undefined) ?? 20;

  const players = searchPlayers(loader, { name, nationality, club, position, minOverall, limit });
  if (players.length === 0) {
    return 'No players found for the given criteria.';
  }

  const lines: string[] = [`Found ${players.length} player(s):`];
  players.forEach((p, i) => {
    lines.push(`  ${i + 1}. ${p.name} | Overall: ${p.overall} | Position: ${p.position} | Club: ${p.club} | Nationality: ${p.nationality}`);
  });

  return lines.join('\n');
}

function handleGetStandings(loader: DataLoader, args: Record<string, unknown>): string {
  const season = args['season'] as number;
  const competition = (args['competition'] as string | undefined) ?? 'Brasileirão';

  const standings = getStandings(loader, { season, competition });
  if (standings.length === 0) {
    return `No standings data found for ${competition} ${season}`;
  }

  const lines: string[] = [`${competition} ${season} Standings (Top ${Math.min(standings.length, 20)}):`];
  standings.slice(0, 20).forEach((s) => {
    const gd = s.goal_difference >= 0 ? `+${s.goal_difference}` : String(s.goal_difference);
    lines.push(`  ${s.position}. ${s.team} - ${s.points} pts (${s.wins}W ${s.draws}D ${s.losses}L) GD: ${gd}`);
  });

  return lines.join('\n');
}

function handleGetStatistics(loader: DataLoader, args: Record<string, unknown>): string {
  const type = args['type'] as string;
  const competition = args['competition'] as string | undefined;
  const season = args['season'] as number | undefined;
  const limit = (args['limit'] as number | undefined) ?? 10;

  if (!['biggest_wins', 'avg_goals', 'home_win_rate', 'top_scorers'].includes(type)) {
    return `Invalid statistics type. Use: biggest_wins, avg_goals, home_win_rate, top_scorers`;
  }

  const stats = getStatistics(loader, {
    type: type as 'biggest_wins' | 'avg_goals' | 'home_win_rate' | 'top_scorers',
    competition,
    season,
    limit,
  });

  const context = [competition, season ? String(season) : undefined].filter(Boolean).join(' ');
  const lines: string[] = [];

  if (type === 'biggest_wins' && stats.biggest_wins) {
    lines.push(`Biggest Wins${context ? ` (${context})` : ''}:`);
    stats.biggest_wins.forEach((m, i) => {
      const margin = Math.abs(m.home_goals - m.away_goals);
      lines.push(`  ${i + 1}. ${formatMatch(m)} (margin: ${margin})`);
    });
  } else if (type === 'avg_goals') {
    lines.push(`Average goals per match${context ? ` (${context})` : ''}: ${stats.avg_goals}`);
    lines.push(`Total matches: ${stats.total_matches}`);
  } else if (type === 'home_win_rate') {
    const pct = ((stats.home_win_rate ?? 0) * 100).toFixed(1);
    lines.push(`Home win rate${context ? ` (${context})` : ''}: ${pct}%`);
    lines.push(`Total matches: ${stats.total_matches}`);
  } else if (type === 'top_scorers' && stats.top_scorers) {
    lines.push(`Top scoring teams${context ? ` (${context})` : ''}:`);
    stats.top_scorers.forEach((t, i) => {
      lines.push(`  ${i + 1}. ${t.team}: ${t.goals} goals`);
    });
  }

  return lines.join('\n');
}

function handleHeadToHead(loader: DataLoader, args: Record<string, unknown>): string {
  const team1 = args['team1'] as string;
  const team2 = args['team2'] as string;
  const competition = args['competition'] as string | undefined;
  const season = args['season'] as number | undefined;

  const result = headToHead(loader, team1, team2, competition, season);
  const limit = (args['limit'] as number | undefined) ?? 10;

  const lines: string[] = [
    `Head-to-head: ${team1} vs ${team2}`,
    `Total matches: ${result.matches.length}`,
    `${team1} wins: ${result.team1_wins} | ${team2} wins: ${result.team2_wins} | Draws: ${result.draws}`,
    '',
    `Recent matches:`,
  ];

  result.matches.slice(0, limit).forEach((m) => {
    lines.push(`  ${formatMatch(m)}`);
  });

  return lines.join('\n');
}
