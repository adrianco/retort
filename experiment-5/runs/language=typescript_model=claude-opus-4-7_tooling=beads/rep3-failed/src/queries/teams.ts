import { DataStore, Competition, Match } from '../data/types.js';
import { teamMatches } from '../data/normalize.js';
import { findMatches } from './matches.js';

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  winRate: number;
}

export interface TeamSplit {
  overall: TeamStats;
  home: TeamStats;
  away: TeamStats;
}

function emptyStats(team: string): TeamStats {
  return {
    team,
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    goalDifference: 0,
    points: 0,
    winRate: 0,
  };
}

function applyMatch(stats: TeamStats, gf: number, ga: number): void {
  stats.matches++;
  stats.goalsFor += gf;
  stats.goalsAgainst += ga;
  if (gf > ga) {
    stats.wins++;
    stats.points += 3;
  } else if (gf === ga) {
    stats.draws++;
    stats.points += 1;
  } else {
    stats.losses++;
  }
  stats.goalDifference = stats.goalsFor - stats.goalsAgainst;
  stats.winRate = stats.matches ? stats.wins / stats.matches : 0;
}

export function teamStats(
  store: DataStore,
  team: string,
  options: {
    competition?: Competition;
    season?: number;
    venue?: 'home' | 'away' | 'all';
  } = {},
): TeamStats {
  const matches = findMatches(store, {
    team,
    competition: options.competition,
    season: options.season,
  });
  const stats = emptyStats(team);
  for (const m of matches) {
    const isHome = teamMatches(m.homeTeam, team);
    if (options.venue === 'home' && !isHome) continue;
    if (options.venue === 'away' && isHome) continue;
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    applyMatch(stats, gf, ga);
  }
  return stats;
}

export function teamSplit(
  store: DataStore,
  team: string,
  options: { competition?: Competition; season?: number } = {},
): TeamSplit {
  return {
    overall: teamStats(store, team, { ...options, venue: 'all' }),
    home: teamStats(store, team, { ...options, venue: 'home' }),
    away: teamStats(store, team, { ...options, venue: 'away' }),
  };
}

export function teamCompetitions(store: DataStore, team: string): Map<Competition, number> {
  const counts = new Map<Competition, number>();
  for (const m of store.matches) {
    if (teamMatches(m.homeTeam, team) || teamMatches(m.awayTeam, team)) {
      counts.set(m.competition, (counts.get(m.competition) ?? 0) + 1);
    }
  }
  return counts;
}

export function topScoringTeams(
  store: DataStore,
  options: { competition?: Competition; season?: number; limit?: number } = {},
): TeamStats[] {
  let matches = store.matches;
  if (options.competition) matches = matches.filter((m) => m.competition === options.competition);
  if (options.season !== undefined) matches = matches.filter((m) => m.season === options.season);

  const map = new Map<string, TeamStats>();
  function get(key: string, display: string): TeamStats {
    let s = map.get(key);
    if (!s) {
      s = emptyStats(display);
      map.set(key, s);
    }
    return s;
  }
  for (const m of matches) {
    const home = get(m.homeTeam, m.homeTeamRaw);
    applyMatch(home, m.homeGoals, m.awayGoals);
    const away = get(m.awayTeam, m.awayTeamRaw);
    applyMatch(away, m.awayGoals, m.homeGoals);
  }
  const out = [...map.values()].sort((a, b) => b.goalsFor - a.goalsFor);
  if (options.limit) return out.slice(0, options.limit);
  return out;
}
