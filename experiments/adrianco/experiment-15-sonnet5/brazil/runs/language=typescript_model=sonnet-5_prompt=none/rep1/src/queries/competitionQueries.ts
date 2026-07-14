import type { Dataset } from "../types.js";
import { competitionMatches, getOrCreateRow, makeRowMap, type TableRowBase } from "./shared.js";

export interface StandingsRow extends TableRowBase {
  goalDifference: number;
  points: number;
}

export interface StandingsResult {
  competition: string;
  season: number;
  matchesUsed: number;
  table: StandingsRow[];
}

/** Computes a league table (points, W/D/L, goals) for a competition + season
 * from the underlying match results. Sorted by points, then goal
 * difference, then goals scored, matching standard Brasileirao tie-break
 * rules. */
export function standings(dataset: Dataset, competition: string, season: number): StandingsResult {
  const matches = dataset.matches.filter(
    (m) => competitionMatches(m, competition) && m.season === season && m.homeGoals !== null && m.awayGoals !== null,
  );

  const table = makeRowMap();

  for (const m of matches) {
    const home = getOrCreateRow(table, m.homeTeam);
    const away = getOrCreateRow(table, m.awayTeam);
    const homeGoals = m.homeGoals as number;
    const awayGoals = m.awayGoals as number;

    home.played += 1;
    away.played += 1;
    home.goalsFor += homeGoals;
    home.goalsAgainst += awayGoals;
    away.goalsFor += awayGoals;
    away.goalsAgainst += homeGoals;

    if (homeGoals > awayGoals) {
      home.wins += 1;
      away.losses += 1;
    } else if (homeGoals < awayGoals) {
      away.wins += 1;
      home.losses += 1;
    } else {
      home.draws += 1;
      away.draws += 1;
    }
  }

  const rows: StandingsRow[] = [...table.values()].map((row) => ({
    ...row,
    goalDifference: row.goalsFor - row.goalsAgainst,
    points: row.wins * 3 + row.draws,
  }));

  rows.sort((a, b) => b.points - a.points || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor);

  return { competition, season, matchesUsed: matches.length, table: rows };
}

export interface CompetitionInfo {
  competition: string;
  source: string;
  matches: number;
  seasons: number[];
}

/** Lists every distinct competition/tournament label available across the
 * loaded datasets, useful for discovering what can be queried. */
export function listCompetitions(dataset: Dataset): CompetitionInfo[] {
  const byKey = new Map<string, { competition: string; source: string; matches: number; seasons: Set<number> }>();
  for (const m of dataset.matches) {
    const key = `${m.source}::${m.competition}`;
    let entry = byKey.get(key);
    if (!entry) {
      entry = { competition: m.competition, source: m.source, matches: 0, seasons: new Set() };
      byKey.set(key, entry);
    }
    entry.matches += 1;
    if (m.season !== null) entry.seasons.add(m.season);
  }
  return [...byKey.values()]
    .map((e) => ({ ...e, seasons: [...e.seasons].sort((a, b) => a - b) }))
    .sort((a, b) => b.matches - a.matches);
}
