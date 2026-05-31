import { DataStore, Match, Competition } from '../data/types.js';

export interface OverallStats {
  totalMatches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

function compute(matches: Match[]): OverallStats {
  let goals = 0, homeWins = 0, awayWins = 0, draws = 0;
  for (const m of matches) {
    goals += m.homeGoals + m.awayGoals;
    if (m.winner === 'home') homeWins++;
    else if (m.winner === 'away') awayWins++;
    else draws++;
  }
  const n = matches.length || 1;
  return {
    totalMatches: matches.length,
    totalGoals: goals,
    avgGoalsPerMatch: goals / n,
    homeWinRate: homeWins / n,
    awayWinRate: awayWins / n,
    drawRate: draws / n,
  };
}

export function overallStats(
  store: DataStore,
  filters: { competition?: Competition; season?: number } = {},
): OverallStats {
  let matches = store.matches;
  if (filters.competition) matches = matches.filter((m) => m.competition === filters.competition);
  if (filters.season !== undefined) matches = matches.filter((m) => m.season === filters.season);
  return compute(matches);
}

export interface RankedMatch {
  match: Match;
  margin: number;
  totalGoals: number;
}

export function biggestWins(
  store: DataStore,
  options: { competition?: Competition; season?: number; limit?: number } = {},
): RankedMatch[] {
  let matches = store.matches;
  if (options.competition) matches = matches.filter((m) => m.competition === options.competition);
  if (options.season !== undefined) matches = matches.filter((m) => m.season === options.season);

  const ranked = matches
    .map((m) => ({
      match: m,
      margin: Math.abs(m.homeGoals - m.awayGoals),
      totalGoals: m.homeGoals + m.awayGoals,
    }))
    .sort((a, b) => b.margin - a.margin || b.totalGoals - a.totalGoals);

  return options.limit ? ranked.slice(0, options.limit) : ranked.slice(0, 10);
}

export function highestScoringMatches(
  store: DataStore,
  options: { competition?: Competition; season?: number; limit?: number } = {},
): RankedMatch[] {
  let matches = store.matches;
  if (options.competition) matches = matches.filter((m) => m.competition === options.competition);
  if (options.season !== undefined) matches = matches.filter((m) => m.season === options.season);

  const ranked = matches
    .map((m) => ({
      match: m,
      margin: Math.abs(m.homeGoals - m.awayGoals),
      totalGoals: m.homeGoals + m.awayGoals,
    }))
    .sort((a, b) => b.totalGoals - a.totalGoals);

  return options.limit ? ranked.slice(0, options.limit) : ranked.slice(0, 10);
}
