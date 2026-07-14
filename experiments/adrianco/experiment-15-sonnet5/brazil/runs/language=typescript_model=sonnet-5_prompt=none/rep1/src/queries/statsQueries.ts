import type { Dataset, Match } from "../types.js";
import { competitionMatches, getOrCreateRow, makeRowMap, type TableRowBase } from "./shared.js";

export interface StatsFilterOptions {
  competition?: string;
  season?: number;
}

function playedMatches(dataset: Dataset, opts: StatsFilterOptions = {}): Match[] {
  let matches = dataset.matches.filter((m) => m.homeGoals !== null && m.awayGoals !== null);
  if (opts.competition) matches = matches.filter((m) => competitionMatches(m, opts.competition!));
  if (opts.season !== undefined) matches = matches.filter((m) => m.season === opts.season);
  return matches;
}

export interface AverageGoalsResult {
  matches: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWinRatePct: number;
  drawRatePct: number;
  awayWinRatePct: number;
}

/** Average goals per match plus home/draw/away outcome rates, optionally
 * scoped to a competition and/or season. */
export function averageGoals(dataset: Dataset, opts: StatsFilterOptions = {}): AverageGoalsResult {
  const matches = playedMatches(dataset, opts);
  let totalGoals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;

  for (const m of matches) {
    totalGoals += (m.homeGoals as number) + (m.awayGoals as number);
    if ((m.homeGoals as number) > (m.awayGoals as number)) homeWins += 1;
    else if ((m.awayGoals as number) > (m.homeGoals as number)) awayWins += 1;
    else draws += 1;
  }

  const n = matches.length;
  return {
    matches: n,
    totalGoals,
    averageGoalsPerMatch: n > 0 ? totalGoals / n : 0,
    homeWinRatePct: n > 0 ? (homeWins / n) * 100 : 0,
    drawRatePct: n > 0 ? (draws / n) * 100 : 0,
    awayWinRatePct: n > 0 ? (awayWins / n) * 100 : 0,
  };
}

export interface BiggestWin {
  match: Match;
  goalDifference: number;
  totalGoals: number;
}

export interface BiggestWinsOptions extends StatsFilterOptions {
  limit?: number;
}

/** Largest-margin victories, optionally scoped to a competition/season. */
export function biggestWins(dataset: Dataset, opts: BiggestWinsOptions = {}): BiggestWin[] {
  const matches = playedMatches(dataset, opts);
  const withDiff = matches
    .map((m) => ({
      match: m,
      goalDifference: Math.abs((m.homeGoals as number) - (m.awayGoals as number)),
      totalGoals: (m.homeGoals as number) + (m.awayGoals as number),
    }))
    .filter((x) => x.goalDifference > 0);

  withDiff.sort((a, b) => b.goalDifference - a.goalDifference || b.totalGoals - a.totalGoals);

  const limit = opts.limit ?? 10;
  return withDiff.slice(0, limit);
}

export interface VenueRecordRow extends TableRowBase {
  winRatePct: number;
}

export interface VenueRecordOptions extends StatsFilterOptions {
  minMatches?: number;
  limit?: number;
}

/** Ranks teams by win rate at a given venue (home or away), useful for
 * "best home/away record" questions. Teams with fewer than `minMatches`
 * (default 5) games are excluded to avoid small-sample outliers. */
export function bestVenueRecord(
  dataset: Dataset,
  venue: "home" | "away",
  opts: VenueRecordOptions = {},
): VenueRecordRow[] {
  const matches = playedMatches(dataset, opts);
  const table = makeRowMap();

  for (const m of matches) {
    const teamKey = venue === "home" ? m.homeTeam : m.awayTeam;
    const forGoals = venue === "home" ? (m.homeGoals as number) : (m.awayGoals as number);
    const againstGoals = venue === "home" ? (m.awayGoals as number) : (m.homeGoals as number);
    const row = getOrCreateRow(table, teamKey);
    row.played += 1;
    row.goalsFor += forGoals;
    row.goalsAgainst += againstGoals;
    if (forGoals > againstGoals) row.wins += 1;
    else if (forGoals < againstGoals) row.losses += 1;
    else row.draws += 1;
  }

  const minMatches = opts.minMatches ?? 5;
  const rows: VenueRecordRow[] = [...table.values()]
    .filter((r) => r.played >= minMatches)
    .map((r) => ({ ...r, winRatePct: (r.wins / r.played) * 100 }));

  rows.sort((a, b) => b.winRatePct - a.winRatePct || b.goalsFor - b.goalsAgainst - (a.goalsFor - a.goalsAgainst));

  const limit = opts.limit ?? 10;
  return rows.slice(0, limit);
}
