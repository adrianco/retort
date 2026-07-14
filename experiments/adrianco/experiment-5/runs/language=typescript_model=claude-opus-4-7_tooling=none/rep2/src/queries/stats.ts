import type { Dataset, Match } from "../types.js";
import { findMatches, type MatchFilter } from "./matches.js";

export interface MatchStats {
  matches: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

export function matchStats(dataset: Dataset, filter: MatchFilter = {}): MatchStats {
  const matches = findMatches(dataset, filter);
  let totalGoals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;
  let counted = 0;
  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    counted++;
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.awayGoals > m.homeGoals) awayWins++;
    else draws++;
  }
  const safeDiv = (a: number, b: number) => (b > 0 ? a / b : 0);
  return {
    matches: counted,
    totalGoals,
    averageGoalsPerMatch: safeDiv(totalGoals, counted),
    homeWins,
    awayWins,
    draws,
    homeWinRate: safeDiv(homeWins, counted),
    awayWinRate: safeDiv(awayWins, counted),
    drawRate: safeDiv(draws, counted),
  };
}

export interface BigWin {
  match: Match;
  margin: number;
  winner: string;
  loser: string;
  score: string;
}

export function biggestWins(dataset: Dataset, filter: MatchFilter & { limit?: number } = {}): BigWin[] {
  // findMatches accepts limit, but biggestWins must rank ALL matches first
  // and then trim to the user's requested limit.
  const { limit, ...rest } = filter;
  const matches = findMatches(dataset, rest);
  const wins: BigWin[] = [];
  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const margin = Math.abs(m.homeGoals - m.awayGoals);
    if (margin === 0) continue;
    const homeWon = m.homeGoals > m.awayGoals;
    wins.push({
      match: m,
      margin,
      winner: homeWon ? m.homeTeamRaw : m.awayTeamRaw,
      loser: homeWon ? m.awayTeamRaw : m.homeTeamRaw,
      score: `${m.homeGoals}-${m.awayGoals}`,
    });
  }
  wins.sort((a, b) => {
    if (b.margin !== a.margin) return b.margin - a.margin;
    const totA = (a.match.homeGoals ?? 0) + (a.match.awayGoals ?? 0);
    const totB = (b.match.homeGoals ?? 0) + (b.match.awayGoals ?? 0);
    return totB - totA;
  });
  return wins.slice(0, limit ?? 10);
}

export interface SeasonComparison {
  season: number;
  matches: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWinRate: number;
  drawRate: number;
}

export function compareSeasons(dataset: Dataset, seasons: number[], filter: MatchFilter = {}): SeasonComparison[] {
  return seasons.map((season) => {
    const s = matchStats(dataset, { ...filter, season });
    return {
      season,
      matches: s.matches,
      totalGoals: s.totalGoals,
      averageGoalsPerMatch: s.averageGoalsPerMatch,
      homeWinRate: s.homeWinRate,
      drawRate: s.drawRate,
    };
  });
}
