import type { SoccerDataStore } from "../data/store.js";
import type { Competition, Match } from "../types.js";
import { filterMatches } from "./helpers.js";

export interface GoalStats {
  matchesConsidered: number;
  averageGoalsPerMatch: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

/** Computes goals-per-match and outcome-rate statistics (Statistical Analysis §5). */
export function calculateGoalStats(store: SoccerDataStore, options: { competition?: Competition; season?: number } = {}): GoalStats {
  const matches = filterMatches(store.matches, options).filter((m) => m.homeGoals !== null && m.awayGoals !== null);
  if (matches.length === 0) {
    return { matchesConsidered: 0, averageGoalsPerMatch: 0, homeWinRate: 0, awayWinRate: 0, drawRate: 0 };
  }

  let totalGoals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;
  for (const match of matches) {
    const homeGoals = match.homeGoals as number;
    const awayGoals = match.awayGoals as number;
    totalGoals += homeGoals + awayGoals;
    if (homeGoals > awayGoals) homeWins += 1;
    else if (awayGoals > homeGoals) awayWins += 1;
    else draws += 1;
  }

  return {
    matchesConsidered: matches.length,
    averageGoalsPerMatch: round2(totalGoals / matches.length),
    homeWinRate: round2(homeWins / matches.length),
    awayWinRate: round2(awayWins / matches.length),
    drawRate: round2(draws / matches.length),
  };
}

/** Finds the biggest victories (largest goal difference) in the dataset, optionally scoped to a competition/season. */
export function biggestWins(store: SoccerDataStore, options: { competition?: Competition; season?: number; limit?: number } = {}): Match[] {
  const matches = filterMatches(store.matches, options).filter((m) => m.homeGoals !== null && m.awayGoals !== null);
  const sorted = [...matches].sort((a, b) => {
    const marginA = Math.abs((a.homeGoals as number) - (a.awayGoals as number));
    const marginB = Math.abs((b.homeGoals as number) - (b.awayGoals as number));
    return marginB - marginA;
  });
  return sorted.slice(0, options.limit ?? 10);
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}
