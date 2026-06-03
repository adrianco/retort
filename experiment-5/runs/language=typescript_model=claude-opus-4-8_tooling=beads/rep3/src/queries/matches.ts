/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/matches.ts
 * Purpose: Match-centric queries: find fixtures by team / competition / season
 *          / date range, and compute head-to-head records between two teams.
 * Inputs:  A loaded `Dataset` plus filter criteria.
 * Outputs: Filtered `Match[]` and `HeadToHead` aggregates.
 * Notes:   Team matching is done on normalized keys, so "Palmeiras", "São
 *          Paulo", and "Palmeiras-SP" all resolve correctly. A `team` filter
 *          matches the team as either home or away unless `side` narrows it.
 * ============================================================================
 */

import type { Dataset } from "../data/loader.js";
import { displayNameFor } from "../data/loader.js";
import type { Match, Competition } from "../data/types.js";
import { normalizeTeam, teamsMatch } from "../data/normalize.js";

export interface MatchFilter {
  team?: string;
  team2?: string;
  side?: "home" | "away" | "either";
  competition?: Competition | string;
  season?: number;
  /** Inclusive ISO date lower bound (YYYY-MM-DD). */
  dateFrom?: string;
  /** Inclusive ISO date upper bound (YYYY-MM-DD). */
  dateTo?: string;
  limit?: number;
}

function competitionMatches(m: Match, comp: string): boolean {
  const c = comp.trim().toLowerCase();
  const mc = m.competition.toLowerCase();
  if (mc === c) return true;
  // Friendly aliases.
  if ((c === "brasileirao" || c === "brasileirão" || c === "serie a") &&
      m.competition === "Brasileirão Série A") return true;
  if ((c === "libertadores" || c === "copa libertadores") &&
      m.competition === "Copa Libertadores") return true;
  if ((c === "copa do brasil" || c === "cup") &&
      m.competition === "Copa do Brasil") return true;
  return mc.includes(c);
}

/** Sort matches by date descending (most recent first); nulls last. */
export function sortByDateDesc(matches: Match[]): Match[] {
  return [...matches].sort((a, b) => {
    if (a.date === b.date) return 0;
    if (a.date == null) return 1;
    if (b.date == null) return -1;
    return a.date < b.date ? 1 : -1;
  });
}

/** Find matches matching the given filter. Results sorted most-recent first. */
export function findMatches(ds: Dataset, filter: MatchFilter): Match[] {
  const key1 = filter.team ? normalizeTeam(filter.team) : null;
  const key2 = filter.team2 ? normalizeTeam(filter.team2) : null;
  const side = filter.side ?? "either";

  let result = ds.matches.filter((m) => {
    if (key1) {
      const home = teamsMatch(m.homeKey, key1);
      const away = teamsMatch(m.awayKey, key1);
      if (side === "home" && !home) return false;
      if (side === "away" && !away) return false;
      if (side === "either" && !home && !away) return false;
    }
    if (key2) {
      // Both teams must be present (in any order).
      const pair =
        (teamsMatch(m.homeKey, key1!) && teamsMatch(m.awayKey, key2)) ||
        (teamsMatch(m.homeKey, key2) && teamsMatch(m.awayKey, key1!));
      if (!pair) return false;
    }
    if (filter.competition && !competitionMatches(m, String(filter.competition)))
      return false;
    if (filter.season != null && m.season !== filter.season) return false;
    if (filter.dateFrom && (m.date == null || m.date < filter.dateFrom))
      return false;
    if (filter.dateTo && (m.date == null || m.date > filter.dateTo))
      return false;
    return true;
  });

  result = sortByDateDesc(result);
  if (filter.limit != null && filter.limit > 0) {
    result = result.slice(0, filter.limit);
  }
  return result;
}

export interface HeadToHead {
  team1: string;
  team2: string;
  totalMatches: number;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  team1Goals: number;
  team2Goals: number;
  matches: Match[];
}

/** Compute the head-to-head record between two teams across all competitions. */
export function headToHead(
  ds: Dataset,
  team1: string,
  team2: string,
  opts: { competition?: string; season?: number } = {},
): HeadToHead {
  const k1 = normalizeTeam(team1);
  const k2 = normalizeTeam(team2);
  const matches = findMatches(ds, {
    team: team1,
    team2,
    competition: opts.competition,
    season: opts.season,
  });

  let t1w = 0,
    t2w = 0,
    draws = 0,
    t1g = 0,
    t2g = 0;
  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    const t1Home = teamsMatch(m.homeKey, k1);
    const t1Goals = t1Home ? m.homeGoals : m.awayGoals;
    const t2Goals = t1Home ? m.awayGoals : m.homeGoals;
    t1g += t1Goals;
    t2g += t2Goals;
    if (t1Goals > t2Goals) t1w++;
    else if (t2Goals > t1Goals) t2w++;
    else draws++;
  }

  return {
    team1: displayNameFor(ds, k1) ?? team1,
    team2: displayNameFor(ds, k2) ?? team2,
    totalMatches: matches.length,
    team1Wins: t1w,
    team2Wins: t2w,
    draws,
    team1Goals: t1g,
    team2Goals: t2g,
    matches,
  };
}
