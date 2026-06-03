/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/statistics.ts
 * Purpose: Aggregate statistical analysis across matches: goals-per-match
 *          averages, home-win rates, biggest victories, top scoring teams, and
 *          best home/away records (leaderboards computed from results).
 * Inputs:  A loaded `Dataset` and optional competition/season scoping.
 * Outputs: Numeric aggregates and ranked leaderboards.
 * Notes:   Only matches with both scores present contribute to aggregates.
 *          Leaderboards apply a minimum-matches threshold so a team that played
 *          a single game cannot top a "best record" ranking.
 * ============================================================================
 */

import type { Dataset } from "../data/loader.js";
import type { Match } from "../data/types.js";
import { findMatches } from "./matches.js";

export interface StatScope {
  competition?: string;
  season?: number;
}

export interface AggregateStats {
  matches: number;
  scoredMatches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

function scoped(ds: Dataset, scope: StatScope): Match[] {
  return findMatches(ds, {
    competition: scope.competition,
    season: scope.season,
  });
}

/** Compute headline aggregate statistics for a scope. */
export function aggregateStats(ds: Dataset, scope: StatScope = {}): AggregateStats {
  const matches = scoped(ds, scope);
  let total = 0,
    home = 0,
    away = 0,
    draw = 0,
    scoredMatches = 0;
  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    scoredMatches++;
    total += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) home++;
    else if (m.homeGoals < m.awayGoals) away++;
    else draw++;
  }
  const denom = scoredMatches || 1;
  return {
    matches: matches.length,
    scoredMatches,
    totalGoals: total,
    avgGoalsPerMatch: total / denom,
    homeWins: home,
    awayWins: away,
    draws: draw,
    homeWinRate: home / denom,
    awayWinRate: away / denom,
    drawRate: draw / denom,
  };
}

export interface BigWin {
  match: Match;
  margin: number;
}

/** Return the matches with the largest winning margin, biggest first. */
export function biggestWins(
  ds: Dataset,
  scope: StatScope = {},
  limit = 10,
): BigWin[] {
  const matches = scoped(ds, scope);
  const wins: BigWin[] = [];
  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    const margin = Math.abs(m.homeGoals - m.awayGoals);
    if (margin <= 0) continue;
    wins.push({ match: m, margin });
  }
  wins.sort(
    (a, b) =>
      b.margin - a.margin ||
      b.match.homeGoals! + b.match.awayGoals! -
        (a.match.homeGoals! + a.match.awayGoals!),
  );
  return wins.slice(0, limit);
}

export interface TeamGoalRank {
  team: string;
  goalsFor: number;
  matches: number;
}

/** Rank teams by total goals scored within a scope. */
export function topScoringTeams(
  ds: Dataset,
  scope: StatScope = {},
  limit = 10,
): TeamGoalRank[] {
  const matches = scoped(ds, scope);
  const map = new Map<string, { team: string; goals: number; n: number }>();
  const add = (key: string, team: string, goals: number) => {
    const g = map.get(key) ?? { team, goals: 0, n: 0 };
    g.goals += goals;
    g.n += 1;
    map.set(key, g);
  };
  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    add(m.homeKey, m.homeTeam, m.homeGoals);
    add(m.awayKey, m.awayTeam, m.awayGoals);
  }
  return [...map.values()]
    .map((g) => ({ team: g.team, goalsFor: g.goals, matches: g.n }))
    .sort((a, b) => b.goalsFor - a.goalsFor)
    .slice(0, limit);
}

export interface VenueRecord {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  winRate: number;
}

/**
 * Best home or away records within a scope. Only teams with at least
 * `minMatches` games are ranked, to avoid tiny-sample artifacts.
 */
export function bestVenueRecords(
  ds: Dataset,
  venue: "home" | "away",
  scope: StatScope = {},
  opts: { limit?: number; minMatches?: number } = {},
): VenueRecord[] {
  const matches = scoped(ds, scope);
  const minMatches = opts.minMatches ?? 5;
  const limit = opts.limit ?? 10;
  const map = new Map<
    string,
    { team: string; p: number; w: number; d: number; l: number }
  >();

  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    const isHome = venue === "home";
    const key = isHome ? m.homeKey : m.awayKey;
    const team = isHome ? m.homeTeam : m.awayTeam;
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    const g = map.get(key) ?? { team, p: 0, w: 0, d: 0, l: 0 };
    g.p++;
    if (gf > ga) g.w++;
    else if (gf < ga) g.l++;
    else g.d++;
    map.set(key, g);
  }

  return [...map.values()]
    .filter((g) => g.p >= minMatches)
    .map((g) => ({
      team: g.team,
      played: g.p,
      wins: g.w,
      draws: g.d,
      losses: g.l,
      winRate: g.w / g.p,
    }))
    .sort((a, b) => b.winRate - a.winRate || b.played - a.played)
    .slice(0, limit);
}
