/**
 * services/teams.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   Team-query service: turns a filtered set of matches into a win/draw/loss
 *   record with goals for/against, points (3-1-0) and win rate. Supports the
 *   spec's "Corinthians home record in 2022" style questions via the optional
 *   season / competition / venue filters, all delegated to `findMatches`.
 *
 *   `headToHead` is re-exported from the match service so team comparisons have
 *   a single import surface. Matches with missing scores are excluded from the
 *   tallies (but still reported in `matchesWithScores` vs `matches`).
 * -----------------------------------------------------------------------------
 */

import type { Dataset } from "../types.js";
import { teamMatches } from "../data/normalize.js";
import { findMatches, type MatchQuery, type Venue } from "./matches.js";

export { headToHead } from "./matches.js";

export interface TeamRecord {
  team: string;
  venue: Venue;
  season?: number;
  competition?: string;
  matches: number;
  matchesWithScores: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  /** Win rate over matches with scores, as a fraction 0..1. */
  winRate: number;
}

export interface TeamRecordQuery {
  season?: number;
  competition?: string;
  venue?: Venue;
  dateFrom?: string;
  dateTo?: string;
}

/** Compute a team's record under the given filters. */
export function teamRecord(
  ds: Dataset,
  team: string,
  query: TeamRecordQuery = {},
): TeamRecord {
  const venue: Venue = query.venue ?? "any";
  const mq: MatchQuery = {
    team,
    venue,
    season: query.season,
    competition: query.competition,
    dateFrom: query.dateFrom,
    dateTo: query.dateTo,
  };
  const matches = findMatches(ds, mq);

  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsAgainst = 0;
  let scored = 0;

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    scored++;
    const isHome = teamMatches(team, m.homeTeam);
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    goalsFor += gf;
    goalsAgainst += ga;
    if (gf > ga) wins++;
    else if (gf < ga) losses++;
    else draws++;
  }

  return {
    team,
    venue,
    season: query.season,
    competition: query.competition,
    matches: matches.length,
    matchesWithScores: scored,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    goalDifference: goalsFor - goalsAgainst,
    points: wins * 3 + draws,
    winRate: scored > 0 ? wins / scored : 0,
  };
}
