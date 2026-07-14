import { DataStore, Competition } from '../data/types.js';
import { TeamStats } from './teams.js';

export interface StandingRow extends TeamStats {
  rank: number;
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

export function standings(
  store: DataStore,
  competition: Competition,
  season: number,
): StandingRow[] {
  const map = new Map<string, TeamStats>();
  function get(key: string, display: string): TeamStats {
    let s = map.get(key);
    if (!s) {
      s = emptyStats(display);
      map.set(key, s);
    }
    return s;
  }
  for (const m of store.matches) {
    if (m.competition !== competition) continue;
    if (m.season !== season) continue;
    const home = get(m.homeTeam, m.homeTeamRaw);
    const away = get(m.awayTeam, m.awayTeamRaw);
    applyMatch(home, m.homeGoals, m.awayGoals);
    applyMatch(away, m.awayGoals, m.homeGoals);
  }
  const rows = [...map.values()].sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.goalDifference !== a.goalDifference) return b.goalDifference - a.goalDifference;
    if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
    return a.team.localeCompare(b.team);
  });
  return rows.map((r, i) => ({ ...r, rank: i + 1 }));
}

export interface SeasonSummary {
  competition: Competition;
  season: number;
  totalMatches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

export function seasonSummary(
  store: DataStore,
  competition: Competition,
  season: number,
): SeasonSummary {
  const matches = store.matches.filter((m) => m.competition === competition && m.season === season);
  let goals = 0, homeWins = 0, awayWins = 0, draws = 0;
  for (const m of matches) {
    goals += m.homeGoals + m.awayGoals;
    if (m.winner === 'home') homeWins++;
    else if (m.winner === 'away') awayWins++;
    else draws++;
  }
  const n = matches.length || 1;
  return {
    competition,
    season,
    totalMatches: matches.length,
    totalGoals: goals,
    avgGoalsPerMatch: goals / n,
    homeWinRate: homeWins / n,
    awayWinRate: awayWins / n,
    drawRate: draws / n,
  };
}

export function availableSeasons(store: DataStore, competition?: Competition): number[] {
  const set = new Set<number>();
  for (const m of store.matches) {
    if (competition && m.competition !== competition) continue;
    set.add(m.season);
  }
  return [...set].sort((a, b) => a - b);
}
