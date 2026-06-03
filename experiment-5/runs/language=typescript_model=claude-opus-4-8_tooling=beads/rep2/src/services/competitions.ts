/**
 * services/competitions.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   Competition service: reconstructs a league table from raw match results for
 *   a given competition + season ("Who won the 2019 Brasileirão?", "Which teams
 *   were relegated in 2020?"). Points follow the modern 3-1-0 rule and the table
 *   is ranked by points, then goal difference, then goals for, then wins.
 *
 *   Teams are grouped by their normalised key (`teamKey`) so home/away rows for
 *   the same club aggregate correctly despite naming variants; the display name
 *   is the cleaned form. Relegation defaults to the bottom 4 (Brasileirão since
 *   2006). `listSeasons` enumerates available seasons for a competition.
 * -----------------------------------------------------------------------------
 */

import type { Dataset } from "../types.js";
import { cleanTeamName, teamKey } from "../data/normalize.js";
import { findMatches } from "./matches.js";

export interface StandingRow {
  position: number;
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}

interface Acc {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}

/** Compute the final standings for a competition + season from match results. */
export function standings(
  ds: Dataset,
  competition: string,
  season: number,
): StandingRow[] {
  const matches = findMatches(ds, { competition, season });
  const table = new Map<string, Acc>();

  const get = (raw: string): Acc => {
    const key = teamKey(raw);
    let acc = table.get(key);
    if (!acc) {
      acc = {
        team: cleanTeamName(raw),
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
      };
      table.set(key, acc);
    }
    return acc;
  };

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const home = get(m.homeTeam);
    const away = get(m.awayTeam);
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
    (a, b) =>
      b.points - a.points ||
      b.goalDifference - a.goalDifference ||
      b.goalsFor - a.goalsFor ||
      b.wins - a.wins ||
      a.team.localeCompare(b.team),
  );
  rows.forEach((r, i) => (r.position = i + 1));
  return rows;
}

/** The champion (top of the table) for a competition + season, or null. */
export function champion(
  ds: Dataset,
  competition: string,
  season: number,
): StandingRow | null {
  const table = standings(ds, competition, season);
  return table.length > 0 ? table[0] : null;
}

/** The relegated teams (bottom `count`) for a league competition + season. */
export function relegated(
  ds: Dataset,
  competition: string,
  season: number,
  count = 4,
): StandingRow[] {
  const table = standings(ds, competition, season);
  if (table.length === 0) return [];
  return table.slice(Math.max(0, table.length - count));
}

/** List the seasons available for a competition, ascending. */
export function listSeasons(ds: Dataset, competition?: string): number[] {
  const matches = competition
    ? findMatches(ds, { competition })
    : ds.matches;
  const seasons = new Set<number>();
  for (const m of matches) if (m.season !== null) seasons.add(m.season);
  return [...seasons].sort((a, b) => a - b);
}
