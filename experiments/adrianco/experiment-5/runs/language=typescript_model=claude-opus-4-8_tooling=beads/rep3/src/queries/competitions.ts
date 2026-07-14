/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/competitions.ts
 * Purpose: Competition-level queries: compute a league table (standings) for a
 *          given competition + season directly from match results, determine
 *          the champion, and (heuristically) the relegated teams.
 * Inputs:  A loaded `Dataset`, competition name, and season year.
 * Outputs: Sorted `StandingRow[]` and derived champion / relegation info.
 * Notes:   Standings use 3-1-0 points, tie-broken by points, goal difference,
 *          goals for, then name. Relegation heuristic = bottom 4 of a 20-team
 *          Série A table (only reported when the table has >= 16 teams).
 * ============================================================================
 */

import type { Dataset } from "../data/loader.js";
import type { StandingRow } from "../data/types.js";
import { findMatches } from "./matches.js";

/** Compute the full standings table for a competition + season. */
export function standings(
  ds: Dataset,
  competition: string,
  season: number,
): StandingRow[] {
  const matches = findMatches(ds, { competition, season });

  interface Acc {
    team: string;
    played: number;
    wins: number;
    draws: number;
    losses: number;
    goalsFor: number;
    goalsAgainst: number;
  }
  const table = new Map<string, Acc>();

  const ensure = (key: string, display: string): Acc => {
    let a = table.get(key);
    if (!a) {
      a = {
        team: display,
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
      };
      table.set(key, a);
    }
    return a;
  };

  for (const m of matches) {
    if (m.homeGoals == null || m.awayGoals == null) continue;
    const home = ensure(m.homeKey, m.homeTeam);
    const away = ensure(m.awayKey, m.awayTeam);
    home.played++;
    away.played++;
    home.goalsFor += m.homeGoals;
    home.goalsAgainst += m.awayGoals;
    away.goalsFor += m.awayGoals;
    away.goalsAgainst += m.homeGoals;
    if (m.homeGoals > m.awayGoals) {
      home.wins++;
      away.losses++;
    } else if (m.homeGoals < m.awayGoals) {
      away.wins++;
      home.losses++;
    } else {
      home.draws++;
      away.draws++;
    }
  }

  const rows: StandingRow[] = [...table.values()].map((a) => ({
    position: 0,
    team: a.team,
    played: a.played,
    wins: a.wins,
    draws: a.draws,
    losses: a.losses,
    goalsFor: a.goalsFor,
    goalsAgainst: a.goalsAgainst,
    goalDifference: a.goalsFor - a.goalsAgainst,
    points: a.wins * 3 + a.draws,
  }));

  rows.sort(
    (x, y) =>
      y.points - x.points ||
      y.goalDifference - x.goalDifference ||
      y.goalsFor - x.goalsFor ||
      x.team.localeCompare(y.team),
  );
  rows.forEach((r, i) => (r.position = i + 1));
  return rows;
}

export interface CompetitionSummary {
  competition: string;
  season: number;
  champion: string | null;
  table: StandingRow[];
  relegated: string[];
}

/** Summarize a competition season: champion, full table, relegation guess. */
export function competitionSummary(
  ds: Dataset,
  competition: string,
  season: number,
): CompetitionSummary {
  const table = standings(ds, competition, season);
  const champion = table.length > 0 ? table[0].team : null;
  // Relegation heuristic for a points-based league with a full table.
  const relegated =
    table.length >= 16 ? table.slice(-4).map((r) => r.team) : [];
  return { competition, season, champion, table, relegated };
}

/** List the distinct seasons available for a competition. */
export function availableSeasons(ds: Dataset, competition: string): number[] {
  const seasons = new Set<number>();
  for (const m of findMatches(ds, { competition })) {
    if (m.season != null) seasons.add(m.season);
  }
  return [...seasons].sort((a, b) => a - b);
}
