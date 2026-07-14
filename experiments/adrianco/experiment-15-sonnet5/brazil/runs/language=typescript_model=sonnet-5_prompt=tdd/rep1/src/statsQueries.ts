import type { Match } from "./types.js";

export function averageGoalsPerMatch(matches: Match[]): number {
  if (matches.length === 0) return 0;
  const total = matches.reduce((sum, m) => sum + m.homeGoals + m.awayGoals, 0);
  return total / matches.length;
}

export interface WinRates {
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

export function homeAwayWinRates(matches: Match[]): WinRates {
  if (matches.length === 0) return { homeWinRate: 0, awayWinRate: 0, drawRate: 0 };

  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;

  for (const m of matches) {
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }

  const total = matches.length;
  return {
    homeWinRate: (homeWins / total) * 100,
    awayWinRate: (awayWins / total) * 100,
    drawRate: (draws / total) * 100,
  };
}

export interface MatchMargin {
  match: Match;
  margin: number;
}

export function biggestWins(matches: Match[], limit = 10): MatchMargin[] {
  return matches
    .filter((m) => m.homeGoals !== m.awayGoals)
    .map((match) => ({ match, margin: Math.abs(match.homeGoals - match.awayGoals) }))
    .sort((a, b) => b.margin - a.margin)
    .slice(0, limit);
}
