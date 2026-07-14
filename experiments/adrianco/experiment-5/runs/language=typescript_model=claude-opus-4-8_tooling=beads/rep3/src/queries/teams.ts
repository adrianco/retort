/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/teams.ts
 * Purpose: Team-centric queries: win/draw/loss + goals records, optionally
 *          filtered by season / competition / venue (home or away), and the
 *          list of competitions a team has appeared in.
 * Inputs:  A loaded `Dataset` and filter criteria.
 * Outputs: `TeamRecord` aggregates and supporting summaries.
 * Notes:   Records are computed purely from match results (only matches with
 *          both scores present are counted). Points use 3-1-0 scoring.
 * ============================================================================
 */

import type { Dataset } from "../data/loader.js";
import { displayNameFor } from "../data/loader.js";
import type { TeamRecord, Match } from "../data/types.js";
import { normalizeTeam, teamsMatch } from "../data/normalize.js";
import { findMatches } from "./matches.js";

export interface TeamRecordFilter {
  season?: number;
  competition?: string;
  venue?: "home" | "away" | "all";
}

/** Compute a team's W/D/L + goals record under the given filter. */
export function teamRecord(
  ds: Dataset,
  team: string,
  filter: TeamRecordFilter = {},
): TeamRecord {
  const key = normalizeTeam(team);
  const venue = filter.venue ?? "all";
  const side =
    venue === "home" ? "home" : venue === "away" ? "away" : "either";

  const matches = findMatches(ds, {
    team,
    side,
    season: filter.season,
    competition: filter.competition,
  });

  const rec: TeamRecord = {
    team: displayNameFor(ds, key) ?? team,
    played: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    points: 0,
  };

  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    const isHome = teamsMatch(m.homeKey, key);
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    rec.played++;
    rec.goalsFor += gf;
    rec.goalsAgainst += ga;
    if (gf > ga) rec.wins++;
    else if (gf < ga) rec.losses++;
    else rec.draws++;
  }
  rec.points = rec.wins * 3 + rec.draws;
  return rec;
}

/** Win rate as a fraction 0..1 (0 if no matches played). */
export function winRate(rec: TeamRecord): number {
  return rec.played === 0 ? 0 : rec.wins / rec.played;
}

/** List the competitions a team has appeared in, with appearance counts. */
export function teamCompetitions(
  ds: Dataset,
  team: string,
): { competition: string; appearances: number }[] {
  const key = normalizeTeam(team);
  const counts = new Map<string, number>();
  for (const m of ds.matches) {
    if (teamsMatch(m.homeKey, key) || teamsMatch(m.awayKey, key)) {
      counts.set(m.competition, (counts.get(m.competition) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([competition, appearances]) => ({ competition, appearances }))
    .sort((a, b) => b.appearances - a.appearances);
}

/** Resolve a (possibly messy) team name to its canonical display name. */
export function resolveTeam(ds: Dataset, team: string): string | null {
  const key = normalizeTeam(team);
  return displayNameFor(ds, key);
}

/** Return all matches for a team (helper used by stats + comparisons). */
export function teamMatches(ds: Dataset, team: string): Match[] {
  return findMatches(ds, { team });
}
