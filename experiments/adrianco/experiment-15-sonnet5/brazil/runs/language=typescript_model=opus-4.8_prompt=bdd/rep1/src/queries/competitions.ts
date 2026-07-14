/**
 * Competition-centric queries: calculate league standings from match results
 * and identify champions.
 *
 * Standings are derived purely from the match data (3 points for a win, 1 for a
 * draw). Because Brasileirão Série A appears in two overlapping datasets
 * (novo_campeonato 2003-2019 and Brasileirao_Matches 2012-2022), we select a
 * single source per season to avoid double-counting fixtures.
 */
import { teamIdentityKey } from "../normalize.js";
import type { Match, StandingsRow, TeamRecord } from "../types.js";
import { BRASILEIRAO } from "../dataStore.js";
import { filterMatches } from "./filters.js";

/** Source-file preference order for Brasileirão league-table calculations. */
const BRASILEIRAO_SOURCE_PRIORITY = [
  "Brasileirao_Matches.csv",
  "novo_campeonato_brasileiro.csv",
  "BR-Football-Dataset.csv",
];

/**
 * Select the played matches to use for a Brasileirão season table, choosing a
 * single source file to avoid the overlap between datasets.
 */
export function brasileiraoSeasonMatches(all: Match[], season: number): Match[] {
  const candidates = filterMatches(all, {
    competition: BRASILEIRAO,
    season,
    playedOnly: true,
  });
  for (const source of BRASILEIRAO_SOURCE_PRIORITY) {
    const fromSource = candidates.filter((m) => m.source === source);
    if (fromSource.length > 0) return fromSource;
  }
  return candidates;
}

/**
 * Calculate a league standings table from a set of round-robin matches.
 * Teams are keyed by their normalized name so the same club is not split by
 * spelling/suffix differences. Ties are broken by points, then goal
 * difference, then goals for, then name.
 */
export function calculateStandings(matches: Match[]): StandingsRow[] {
  const table = new Map<string, TeamRecord>();

  // Key by the suffix-preserving identity so "Atlético-MG" and "Atlético-PR"
  // stay distinct; display the raw (suffixed) name so the two are legible.
  const record = (rawName: string, displayName: string): TeamRecord => {
    const key = teamIdentityKey(rawName);
    let row = table.get(key);
    if (!row) {
      row = {
        team: displayName,
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        points: 0,
      };
      table.set(key, row);
    }
    return row;
  };

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const home = record(m.homeTeamRaw || m.homeTeam, m.homeTeamRaw || m.homeTeam);
    const away = record(m.awayTeamRaw || m.awayTeam, m.awayTeamRaw || m.awayTeam);
    home.played += 1;
    away.played += 1;
    home.goalsFor += m.homeGoals;
    home.goalsAgainst += m.awayGoals;
    away.goalsFor += m.awayGoals;
    away.goalsAgainst += m.homeGoals;
    if (m.homeGoals > m.awayGoals) {
      home.wins += 1;
      home.points += 3;
      away.losses += 1;
    } else if (m.homeGoals < m.awayGoals) {
      away.wins += 1;
      away.points += 3;
      home.losses += 1;
    } else {
      home.draws += 1;
      away.draws += 1;
      home.points += 1;
      away.points += 1;
    }
  }

  const rows = [...table.values()]
    .map((r) => ({
      ...r,
      position: 0,
      goalDifference: r.goalsFor - r.goalsAgainst,
    }))
    .sort(compareStandings);

  rows.forEach((row, index) => {
    row.position = index + 1;
  });
  return rows;
}

function compareStandings(a: StandingsRow, b: StandingsRow): number {
  // Official Brasileirão order: points, wins, goal difference, goals for.
  if (b.points !== a.points) return b.points - a.points;
  if (b.wins !== a.wins) return b.wins - a.wins;
  if (b.goalDifference !== a.goalDifference) return b.goalDifference - a.goalDifference;
  if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
  return a.team.localeCompare(b.team);
}

/** Convenience: full Brasileirão standings for a season. */
export function brasileiraoStandings(all: Match[], season: number): StandingsRow[] {
  return calculateStandings(brasileiraoSeasonMatches(all, season));
}

/** The champion (top of the table) of the Brasileirão for a season, or null. */
export function brasileiraoChampion(all: Match[], season: number): StandingsRow | null {
  const table = brasileiraoStandings(all, season);
  return table.length > 0 ? table[0] : null;
}
