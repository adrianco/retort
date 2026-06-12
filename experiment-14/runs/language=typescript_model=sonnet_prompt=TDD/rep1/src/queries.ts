import type { DataLoader } from './loader.js';
import type { NormalizedMatch, TeamStats, HeadToHeadResult } from './types.js';
import { teamsMatch } from './normalizer.js';

export interface SearchMatchesParams {
  team?: string;
  team1?: string;
  team2?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}

export function searchMatches(
  loader: DataLoader,
  params: SearchMatchesParams,
): NormalizedMatch[] {
  let matches = loader.getAllNormalizedMatches();

  if (params.team1 && params.team2) {
    matches = matches.filter((m) => {
      const h1a2 = teamsMatch(params.team1!, m.home_team) && teamsMatch(params.team2!, m.away_team);
      const h2a1 = teamsMatch(params.team2!, m.home_team) && teamsMatch(params.team1!, m.away_team);
      return h1a2 || h2a1;
    });
  } else if (params.team) {
    matches = matches.filter(
      (m) => teamsMatch(params.team!, m.home_team) || teamsMatch(params.team!, m.away_team),
    );
  }

  if (params.competition) {
    const comp = params.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (params.season) {
    matches = matches.filter((m) => m.season === params.season);
  }

  if (params.dateFrom) {
    matches = matches.filter((m) => m.date >= params.dateFrom!);
  }

  if (params.dateTo) {
    matches = matches.filter((m) => m.date <= params.dateTo!);
  }

  matches = matches.sort((a, b) => b.date.localeCompare(a.date));

  if (params.limit) {
    matches = matches.slice(0, params.limit);
  }

  return matches;
}

export interface GetTeamStatsParams {
  team: string;
  competition?: string;
  season?: number;
  homeOnly?: boolean;
  awayOnly?: boolean;
}

export function getTeamStats(
  loader: DataLoader,
  params: GetTeamStatsParams,
): TeamStats | null {
  let matches = loader.getAllNormalizedMatches();

  if (params.competition) {
    const comp = params.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (params.season) {
    matches = matches.filter((m) => m.season === params.season);
  }

  const teamMatches = matches.filter(
    (m) => teamsMatch(params.team, m.home_team) || teamsMatch(params.team, m.away_team),
  );

  if (teamMatches.length === 0) return null;

  let filteredMatches = teamMatches;
  if (params.homeOnly) {
    filteredMatches = teamMatches.filter((m) => teamsMatch(params.team, m.home_team));
  } else if (params.awayOnly) {
    filteredMatches = teamMatches.filter((m) => teamsMatch(params.team, m.away_team));
  }

  if (filteredMatches.length === 0) return null;

  const stats: TeamStats = {
    team: params.team,
    matches: filteredMatches.length,
    wins: 0,
    draws: 0,
    losses: 0,
    goals_for: 0,
    goals_against: 0,
    points: 0,
  };

  for (const m of filteredMatches) {
    const isHome = teamsMatch(params.team, m.home_team);
    const goalsFor = isHome ? m.home_goals : m.away_goals;
    const goalsAgainst = isHome ? m.away_goals : m.home_goals;
    stats.goals_for += goalsFor;
    stats.goals_against += goalsAgainst;
    if (goalsFor > goalsAgainst) stats.wins++;
    else if (goalsFor === goalsAgainst) stats.draws++;
    else stats.losses++;
  }

  stats.points = stats.wins * 3 + stats.draws;
  return stats;
}

export function headToHead(
  loader: DataLoader,
  team1: string,
  team2: string,
  competition?: string,
  season?: number,
): HeadToHeadResult {
  const params: SearchMatchesParams = { team1, team2 };
  if (competition) params.competition = competition;
  if (season) params.season = season;
  const matches = searchMatches(loader, params);

  let t1wins = 0, t2wins = 0, draws = 0;
  for (const m of matches) {
    const t1home = teamsMatch(team1, m.home_team);
    const goalsT1 = t1home ? m.home_goals : m.away_goals;
    const goalsT2 = t1home ? m.away_goals : m.home_goals;
    if (goalsT1 > goalsT2) t1wins++;
    else if (goalsT2 > goalsT1) t2wins++;
    else draws++;
  }

  return { team1, team2, matches, team1_wins: t1wins, team2_wins: t2wins, draws };
}

export interface GetStandingsParams {
  season: number;
  competition?: string;
}

export interface StandingsEntry extends TeamStats {
  position: number;
  goal_difference: number;
}

export function getStandings(
  loader: DataLoader,
  params: GetStandingsParams,
): StandingsEntry[] {
  let matches = loader.getAllNormalizedMatches().filter((m) => m.season === params.season);

  if (params.competition) {
    const comp = params.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  const teamMap = new Map<string, TeamStats>();

  const getOrCreate = (team: string): TeamStats => {
    const key = team.toLowerCase();
    if (!teamMap.has(key)) {
      teamMap.set(key, {
        team,
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0,
        points: 0,
      });
    }
    return teamMap.get(key)!;
  };

  for (const m of matches) {
    const home = getOrCreate(m.home_team);
    const away = getOrCreate(m.away_team);
    home.matches++;
    away.matches++;
    home.goals_for += m.home_goals;
    home.goals_against += m.away_goals;
    away.goals_for += m.away_goals;
    away.goals_against += m.home_goals;
    if (m.home_goals > m.away_goals) {
      home.wins++;
      away.losses++;
    } else if (m.away_goals > m.home_goals) {
      away.wins++;
      home.losses++;
    } else {
      home.draws++;
      away.draws++;
    }
    home.points = home.wins * 3 + home.draws;
    away.points = away.wins * 3 + away.draws;
  }

  const entries = Array.from(teamMap.values()).sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    const gdA = a.goals_for - a.goals_against;
    const gdB = b.goals_for - b.goals_against;
    if (gdB !== gdA) return gdB - gdA;
    return b.goals_for - a.goals_for;
  });

  return entries.map((s, i) => ({
    ...s,
    position: i + 1,
    goal_difference: s.goals_for - s.goals_against,
  }));
}

export interface GetStatisticsParams {
  type: 'biggest_wins' | 'avg_goals' | 'home_win_rate' | 'top_scorers';
  competition?: string;
  season?: number;
  limit?: number;
}

export interface StatisticsResult {
  biggest_wins?: NormalizedMatch[];
  avg_goals?: number;
  home_win_rate?: number;
  total_matches?: number;
  top_scorers?: Array<{ team: string; goals: number }>;
}

export function getStatistics(
  loader: DataLoader,
  params: GetStatisticsParams,
): StatisticsResult {
  let matches = loader.getAllNormalizedMatches();

  if (params.competition) {
    const comp = params.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (params.season) {
    matches = matches.filter((m) => m.season === params.season);
  }

  const limit = params.limit ?? 10;

  if (params.type === 'biggest_wins') {
    const sorted = [...matches].sort((a, b) => {
      const marginA = Math.abs(a.home_goals - a.away_goals);
      const marginB = Math.abs(b.home_goals - b.away_goals);
      return marginB - marginA;
    });
    return { biggest_wins: sorted.slice(0, limit) };
  }

  if (params.type === 'avg_goals') {
    if (matches.length === 0) return { avg_goals: 0, total_matches: 0 };
    const total = matches.reduce((s, m) => s + m.home_goals + m.away_goals, 0);
    return {
      avg_goals: Math.round((total / matches.length) * 100) / 100,
      total_matches: matches.length,
    };
  }

  if (params.type === 'home_win_rate') {
    if (matches.length === 0) return { home_win_rate: 0, total_matches: 0 };
    const homeWins = matches.filter((m) => m.home_goals > m.away_goals).length;
    return {
      home_win_rate: Math.round((homeWins / matches.length) * 1000) / 1000,
      total_matches: matches.length,
    };
  }

  if (params.type === 'top_scorers') {
    const goalsMap = new Map<string, number>();
    for (const m of matches) {
      goalsMap.set(m.home_team, (goalsMap.get(m.home_team) ?? 0) + m.home_goals);
      goalsMap.set(m.away_team, (goalsMap.get(m.away_team) ?? 0) + m.away_goals);
    }
    const sorted = Array.from(goalsMap.entries())
      .map(([team, goals]) => ({ team, goals }))
      .sort((a, b) => b.goals - a.goals)
      .slice(0, limit);
    return { top_scorers: sorted };
  }

  return {};
}
