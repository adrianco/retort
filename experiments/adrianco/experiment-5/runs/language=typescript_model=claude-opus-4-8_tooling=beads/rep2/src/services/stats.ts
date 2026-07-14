/**
 * services/stats.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   Statistical-analysis service: aggregate metrics over a filtered match set
 *   ("average goals per match", "home win rate", "biggest wins") and ranking
 *   helpers ("which team has the best home/away record").
 *
 *   `aggregateStats` reports goals-per-match plus home/draw/away outcome rates.
 *   `biggestWins` ranks matches by goal margin (then total goals). `bestRecords`
 *   builds per-team records across the whole filtered set and ranks them, with a
 *   minimum-matches guard so a single 1-0 win can't top the table.
 *
 *   All filtering is delegated to `findMatches`, so every stat respects the same
 *   competition / season / date / team semantics as the rest of the server.
 * -----------------------------------------------------------------------------
 */

import type { Dataset, Match } from "../types.js";
import { cleanTeamName, teamKey } from "../data/normalize.js";
import { findMatches, type MatchQuery, type Venue } from "./matches.js";
import { teamRecord, type TeamRecord } from "./teams.js";

export interface AggregateStats {
  matches: number;
  matchesWithScores: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWins: number;
  draws: number;
  awayWins: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
}

/** Aggregate scoring / outcome statistics over a filtered match set. */
export function aggregateStats(ds: Dataset, query: MatchQuery = {}): AggregateStats {
  const matches = findMatches(ds, query);
  let scored = 0;
  let totalGoals = 0;
  let homeWins = 0;
  let draws = 0;
  let awayWins = 0;

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    scored++;
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }

  return {
    matches: matches.length,
    matchesWithScores: scored,
    totalGoals,
    averageGoalsPerMatch: scored > 0 ? totalGoals / scored : 0,
    homeWins,
    draws,
    awayWins,
    homeWinRate: scored > 0 ? homeWins / scored : 0,
    drawRate: scored > 0 ? draws / scored : 0,
    awayWinRate: scored > 0 ? awayWins / scored : 0,
  };
}

export interface BiggestWin {
  match: Match;
  winner: string;
  loser: string;
  margin: number;
  scoreline: string;
}

/** Rank matches by winning margin (then total goals), largest first. */
export function biggestWins(
  ds: Dataset,
  query: MatchQuery = {},
  limit = 10,
): BiggestWin[] {
  const matches = findMatches(ds, { ...query, limit: 0 });
  const wins: BiggestWin[] = [];
  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const margin = Math.abs(m.homeGoals - m.awayGoals);
    if (margin === 0) continue;
    const homeWon = m.homeGoals > m.awayGoals;
    wins.push({
      match: m,
      winner: homeWon ? m.homeTeam : m.awayTeam,
      loser: homeWon ? m.awayTeam : m.homeTeam,
      margin,
      scoreline: `${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam}`,
    });
  }
  wins.sort(
    (a, b) =>
      b.margin - a.margin ||
      b.match.homeGoals! + b.match.awayGoals! - (a.match.homeGoals! + a.match.awayGoals!),
  );
  return wins.slice(0, limit);
}

/**
 * Rank teams by record over a filtered set (e.g. best home record). `metric`
 * selects the ranking key. `minMatches` filters out tiny samples.
 */
export function bestRecords(
  ds: Dataset,
  opts: {
    competition?: string;
    season?: number;
    venue?: Venue;
    metric?: "winRate" | "points" | "goalsFor" | "goalDifference";
    minMatches?: number;
    limit?: number;
  } = {},
): TeamRecord[] {
  const venue = opts.venue ?? "any";
  const metric = opts.metric ?? "winRate";
  const minMatches = opts.minMatches ?? 5;

  // Discover the universe of teams in the filtered competition/season.
  const universe = findMatches(ds, {
    competition: opts.competition,
    season: opts.season,
  });
  const teamKeys = new Map<string, string>(); // key -> display
  for (const m of universe) {
    teamKeys.set(teamKey(m.homeTeam), cleanTeamName(m.homeTeam));
    teamKeys.set(teamKey(m.awayTeam), cleanTeamName(m.awayTeam));
  }

  const records: TeamRecord[] = [];
  for (const display of teamKeys.values()) {
    const rec = teamRecord(ds, display, {
      competition: opts.competition,
      season: opts.season,
      venue,
    });
    if (rec.matchesWithScores >= minMatches) records.push(rec);
  }

  records.sort((a, b) => {
    switch (metric) {
      case "points":
        return b.points - a.points || b.goalDifference - a.goalDifference;
      case "goalsFor":
        return b.goalsFor - a.goalsFor;
      case "goalDifference":
        return b.goalDifference - a.goalDifference;
      case "winRate":
      default:
        return b.winRate - a.winRate || b.points - a.points;
    }
  });

  return opts.limit && opts.limit > 0 ? records.slice(0, opts.limit) : records;
}
