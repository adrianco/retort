/**
 * CSV loaders for the Brazilian Soccer datasets.
 *
 * Each provided CSV has its own schema; the per-dataset `parse*` functions
 * translate raw rows into the unified `Match`/`Player` domain types, attaching a
 * canonical competition name, normalized team keys and parsed dates. `loadAll`
 * reads every file from a data directory and returns the combined corpus.
 *
 * Parsing is split from file IO so the row-mapping logic can be unit-tested with
 * small inline CSV strings.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "csv-parse/sync";
import type { Match, Player } from "./types.js";
import { normalizeTeamName, normalizeName, parseDate } from "./normalize.js";

type Row = Record<string, string>;

/** Parse a CSV string into objects keyed by header, tolerant of BOM/encoding. */
function rows(csv: string): Row[] {
  return parse(csv, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
    relax_quotes: true,
    relax_column_count: true,
    trim: true,
  }) as Row[];
}

/** Parse an integer that may be written as a float ("1.0") or quoted ("2"). */
function toInt(value: string | undefined): number {
  if (value == null || value.trim() === "" || value.toUpperCase() === "NA") {
    return 0;
  }
  return Math.round(parseFloat(value));
}

/** Parse a nullable integer, returning null for blanks. */
function toIntOrNull(value: string | undefined): number | null {
  if (value == null || value.trim() === "" || value.toUpperCase() === "NA") {
    return null;
  }
  const n = Math.round(parseFloat(value));
  return Number.isNaN(n) ? null : n;
}

/** Brasileirão Série A (Brasileirao_Matches.csv). */
export function parseBrasileirao(csv: string): Match[] {
  return rows(csv).map((r) => ({
    competition: "Brasileirão Série A",
    date: parseDate(r.datetime),
    season: toIntOrNull(r.season),
    round: r.round || undefined,
    homeTeam: r.home_team,
    awayTeam: r.away_team,
    homeKey: normalizeTeamName(r.home_team),
    awayKey: normalizeTeamName(r.away_team),
    homeGoals: toInt(r.home_goal),
    awayGoals: toInt(r.away_goal),
    source: "Brasileirao_Matches.csv",
  }));
}

/** Copa do Brasil (Brazilian_Cup_Matches.csv). */
export function parseCup(csv: string): Match[] {
  return rows(csv).map((r) => ({
    competition: "Copa do Brasil",
    date: parseDate(r.datetime),
    season: toIntOrNull(r.season),
    round: r.round || undefined,
    homeTeam: r.home_team,
    awayTeam: r.away_team,
    homeKey: normalizeTeamName(r.home_team),
    awayKey: normalizeTeamName(r.away_team),
    homeGoals: toInt(r.home_goal),
    awayGoals: toInt(r.away_goal),
    source: "Brazilian_Cup_Matches.csv",
  }));
}

/** Copa Libertadores (Libertadores_Matches.csv). */
export function parseLibertadores(csv: string): Match[] {
  return rows(csv).map((r) => ({
    competition: "Copa Libertadores",
    date: parseDate(r.datetime),
    season: toIntOrNull(r.season),
    stage: r.stage || undefined,
    homeTeam: r.home_team,
    awayTeam: r.away_team,
    homeKey: normalizeTeamName(r.home_team),
    awayKey: normalizeTeamName(r.away_team),
    homeGoals: toInt(r.home_goal),
    awayGoals: toInt(r.away_goal),
    source: "Libertadores_Matches.csv",
  }));
}

/** Map a BR-Football-Dataset tournament label to a canonical competition. */
function brTournament(name: string): string {
  const t = name.trim().toLowerCase();
  if (t === "serie a") return "Brasileirão Série A";
  if (t === "serie b") return "Brasileirão Série B";
  if (t === "serie c") return "Brasileirão Série C";
  if (t === "copa do brasil") return "Copa do Brasil";
  return name.trim();
}

/** Extended match statistics (BR-Football-Dataset.csv). */
export function parseBRFootball(csv: string): Match[] {
  return rows(csv).map((r) => {
    const date = parseDate(r.date);
    return {
      competition: brTournament(r.tournament),
      date,
      season: date ? date.getUTCFullYear() : null,
      homeTeam: r.home,
      awayTeam: r.away,
      homeKey: normalizeTeamName(r.home),
      awayKey: normalizeTeamName(r.away),
      homeGoals: toInt(r.home_goal),
      awayGoals: toInt(r.away_goal),
      source: "BR-Football-Dataset.csv",
      stats: {
        homeCorners: toIntOrNull(r.home_corner) ?? undefined,
        awayCorners: toIntOrNull(r.away_corner) ?? undefined,
        homeAttacks: toIntOrNull(r.home_attack) ?? undefined,
        awayAttacks: toIntOrNull(r.away_attack) ?? undefined,
        homeShots: toIntOrNull(r.home_shots) ?? undefined,
        awayShots: toIntOrNull(r.away_shots) ?? undefined,
        totalCorners: toIntOrNull(r.total_corners) ?? undefined,
        halfTimeHomeResult: r.ht_result || undefined,
        halfTimeAwayResult: r.at_result || undefined,
      },
    };
  });
}

/** Historical Brasileirão 2003-2019 (novo_campeonato_brasileiro.csv). */
export function parseNovoBrasileirao(csv: string): Match[] {
  return rows(csv).map((r) => ({
    competition: "Brasileirão Série A",
    date: parseDate(r.Data),
    season: toIntOrNull(r.Ano),
    round: r.Rodada || undefined,
    homeTeam: r.Equipe_mandante,
    awayTeam: r.Equipe_visitante,
    homeKey: normalizeTeamName(r.Equipe_mandante),
    awayKey: normalizeTeamName(r.Equipe_visitante),
    homeGoals: toInt(r.Gols_mandante),
    awayGoals: toInt(r.Gols_visitante),
    arena: r.Arena || undefined,
    source: "novo_campeonato_brasileiro.csv",
  }));
}

/** FIFA player database (fifa_data.csv). */
export function parsePlayers(csv: string): Player[] {
  return rows(csv).map((r) => ({
    id: toInt(r.ID),
    name: r.Name,
    nameKey: normalizeName(r.Name ?? ""),
    age: toIntOrNull(r.Age),
    nationality: r.Nationality ?? "",
    overall: toIntOrNull(r.Overall),
    potential: toIntOrNull(r.Potential),
    club: r.Club ?? "",
    clubKey: normalizeTeamName(r.Club ?? ""),
    position: r.Position ?? "",
    jerseyNumber: toIntOrNull(r["Jersey Number"]),
    height: r.Height ?? "",
    weight: r.Weight ?? "",
  }));
}

/**
 * Reduce the raw, multi-source corpus to a canonical, non-overlapping set.
 *
 * The provided datasets overlap (e.g. Brasileirão Série A 2019 appears in three
 * files) and use inconsistent team-name spellings across files, which makes a
 * cross-file fixture-level merge unreliable. Instead, for each
 * (competition, season) we keep matches from the single source that covers it
 * most completely. Within one file the naming is self-consistent and there is no
 * duplication, so derived standings/statistics are correct. Matches with
 * unparseable (e.g. abandoned "-") scores are dropped.
 */
export function canonicalMatches(matches: Match[]): Match[] {
  const valid = matches.filter(
    (m) => Number.isFinite(m.homeGoals) && Number.isFinite(m.awayGoals)
  );

  // Count matches per (competition|season) per source.
  const counts = new Map<string, Map<string, number>>();
  const groupKey = (m: Match) => `${m.competition}|${m.season ?? "?"}`;
  for (const m of valid) {
    const g = groupKey(m);
    let bySource = counts.get(g);
    if (!bySource) {
      bySource = new Map();
      counts.set(g, bySource);
    }
    bySource.set(m.source, (bySource.get(m.source) ?? 0) + 1);
  }

  // Choose the most complete source for each group (first-seen wins ties).
  const chosen = new Map<string, string>();
  for (const [g, bySource] of counts) {
    let bestSource = "";
    let bestCount = -1;
    for (const [source, count] of bySource) {
      if (count > bestCount) {
        bestCount = count;
        bestSource = source;
      }
    }
    chosen.set(g, bestSource);
  }

  return valid.filter((m) => chosen.get(groupKey(m)) === m.source);
}

export interface Corpus {
  matches: Match[];
  players: Player[];
}

/** Read and parse every dataset from a directory of Kaggle CSVs. */
export function loadAll(dataDir: string): Corpus {
  const read = (file: string) => readFileSync(join(dataDir, file), "utf-8");

  const matches: Match[] = [
    ...parseBrasileirao(read("Brasileirao_Matches.csv")),
    ...parseCup(read("Brazilian_Cup_Matches.csv")),
    ...parseLibertadores(read("Libertadores_Matches.csv")),
    ...parseBRFootball(read("BR-Football-Dataset.csv")),
    ...parseNovoBrasileirao(read("novo_campeonato_brasileiro.csv")),
  ];
  const players = parsePlayers(read("fifa_data.csv"));

  return { matches, players };
}
