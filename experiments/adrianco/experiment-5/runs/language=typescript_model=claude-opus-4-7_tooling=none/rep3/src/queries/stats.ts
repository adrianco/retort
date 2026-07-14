import { Match, Competition } from '../types.js';

export interface OverallStats {
  matches: number;
  totalGoals: number;
  averageGoals: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

export function overallStats(
  matches: Match[],
  opts: { competition?: Competition; season?: number } = {},
): OverallStats {
  const filtered = matches.filter((m) => {
    if (opts.competition && m.competition !== opts.competition) return false;
    if (opts.season != null && m.season !== opts.season) return false;
    return true;
  });

  let totalGoals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;
  for (const m of filtered) {
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }
  const n = filtered.length;
  return {
    matches: n,
    totalGoals,
    averageGoals: n > 0 ? totalGoals / n : 0,
    homeWins,
    awayWins,
    draws,
    homeWinRate: n > 0 ? homeWins / n : 0,
    awayWinRate: n > 0 ? awayWins / n : 0,
    drawRate: n > 0 ? draws / n : 0,
  };
}

export interface SeasonsAvailable {
  season: number;
  matches: number;
}

export function seasonsAvailable(
  matches: Match[],
  competition?: Competition,
): SeasonsAvailable[] {
  const counts = new Map<number, number>();
  for (const m of matches) {
    if (competition && m.competition !== competition) continue;
    if (m.season == null) continue;
    counts.set(m.season, (counts.get(m.season) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([season, matches]) => ({ season, matches }))
    .sort((a, b) => a.season - b.season);
}
