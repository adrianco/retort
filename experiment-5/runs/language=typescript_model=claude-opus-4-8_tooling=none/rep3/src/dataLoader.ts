/**
 * ============================================================================
 * Context: Brazilian Soccer MCP Server — Data Loader
 * ----------------------------------------------------------------------------
 * Purpose : Reads the six provided CSV files from data/kaggle/ and normalizes
 *           every row into the unified `Match` / `Player` models. Each source
 *           file has its own column layout, date format, encoding quirk and
 *           competition meaning; this module is the single place that knows
 *           about those per-file details. Everything downstream sees clean,
 *           consistent records.
 * Strategy: Eager, in-memory load (the whole corpus is ~12 MB / ~42k rows),
 *           cached behind `loadDataset()` so repeated calls are free. This
 *           keeps query latency well under the spec's 2s/5s targets.
 * Consumers: queries.ts, server.ts, tests.
 * ============================================================================
 */

import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "csv-parse/sync";

import type { Match, Player } from "./types.js";
import { cleanTeamName, parseDate, parseGoals, parseIntSafe } from "./normalize.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** The fully loaded, in-memory dataset. */
export interface Dataset {
  matches: Match[];
  players: Player[];
  /** Sorted list of distinct canonical competition names present. */
  competitions: string[];
}

/**
 * Resolve the data directory. Defaults to `<repo>/data/kaggle` relative to this
 * source file (works for both `src/` via tsx and compiled `dist/`), but can be
 * overridden with the BR_SOCCER_DATA_DIR environment variable.
 */
export function resolveDataDir(): string {
  const override = process.env.BR_SOCCER_DATA_DIR;
  if (override) return resolve(override);
  // From src/ or dist/, the repo root is one level up.
  return resolve(__dirname, "..", "data", "kaggle");
}

type Row = Record<string, string>;

function readCsv(dir: string, file: string): Row[] {
  const text = readFileSync(join(dir, file), "utf-8");
  return parse(text, {
    columns: true,
    skip_empty_lines: true,
    relax_quotes: true,
    relax_column_count: true,
    trim: true,
    bom: true,
  }) as Row[];
}

// --- Per-file row mappers -------------------------------------------------

function loadBrasileirao(dir: string): Match[] {
  return readCsv(dir, "Brasileirao_Matches.csv").map((r) => ({
    competition: "Brasileirão Série A",
    source: "Brasileirao_Matches.csv",
    date: parseDate(r.datetime),
    season: parseIntSafe(r.season),
    round: r.round ? String(r.round) : null,
    stage: null,
    homeTeam: cleanTeamName(r.home_team),
    awayTeam: cleanTeamName(r.away_team),
    homeGoals: parseGoals(r.home_goal),
    awayGoals: parseGoals(r.away_goal),
    homeState: r.home_team_state || null,
    awayState: r.away_team_state || null,
    venue: null,
  }));
}

function loadCup(dir: string): Match[] {
  return readCsv(dir, "Brazilian_Cup_Matches.csv").map((r) => ({
    competition: "Copa do Brasil",
    source: "Brazilian_Cup_Matches.csv",
    date: parseDate(r.datetime),
    season: parseIntSafe(r.season),
    round: r.round ? String(r.round) : null,
    stage: null,
    homeTeam: cleanTeamName(r.home_team),
    awayTeam: cleanTeamName(r.away_team),
    homeGoals: parseGoals(r.home_goal),
    awayGoals: parseGoals(r.away_goal),
    homeState: null,
    awayState: null,
    venue: null,
  }));
}

function loadLibertadores(dir: string): Match[] {
  return readCsv(dir, "Libertadores_Matches.csv").map((r) => ({
    competition: "Copa Libertadores",
    source: "Libertadores_Matches.csv",
    date: parseDate(r.datetime),
    season: parseIntSafe(r.season),
    round: null,
    stage: r.stage || null,
    homeTeam: cleanTeamName(r.home_team),
    awayTeam: cleanTeamName(r.away_team),
    homeGoals: parseGoals(r.home_goal),
    awayGoals: parseGoals(r.away_goal),
    homeState: null,
    awayState: null,
    venue: null,
  }));
}

/** Map the BR-Football "tournament" column to a canonical competition name. */
function brTournament(raw: string): string {
  const t = (raw || "").toLowerCase();
  if (t.includes("copa do brasil")) return "Copa do Brasil";
  if (t.includes("serie a") || t.includes("série a")) return "Brasileirão Série A";
  if (t.includes("serie b") || t.includes("série b")) return "Brasileirão Série B";
  if (t.includes("serie c") || t.includes("série c")) return "Brasileirão Série C";
  return raw || "Unknown";
}

function loadBrFootball(dir: string): Match[] {
  return readCsv(dir, "BR-Football-Dataset.csv").map((r) => {
    const date = parseDate(r.date);
    return {
      competition: brTournament(r.tournament),
      source: "BR-Football-Dataset.csv",
      date,
      season: date ? parseIntSafe(date.slice(0, 4)) : null,
      round: null,
      stage: null,
      homeTeam: cleanTeamName(r.home),
      awayTeam: cleanTeamName(r.away),
      homeGoals: parseGoals(r.home_goal),
      awayGoals: parseGoals(r.away_goal),
      homeState: null,
      awayState: null,
      venue: null,
    };
  });
}

function loadHistorical(dir: string): Match[] {
  return readCsv(dir, "novo_campeonato_brasileiro.csv").map((r) => ({
    competition: "Brasileirão (Histórico)",
    source: "novo_campeonato_brasileiro.csv",
    date: parseDate(r.Data),
    season: parseIntSafe(r.Ano),
    round: r.Rodada ? String(r.Rodada) : null,
    stage: null,
    homeTeam: cleanTeamName(r.Equipe_mandante),
    awayTeam: cleanTeamName(r.Equipe_visitante),
    homeGoals: parseGoals(r.Gols_mandante),
    awayGoals: parseGoals(r.Gols_visitante),
    homeState: r.Mandante_UF || null,
    awayState: r.Visitante_UF || null,
    venue: r.Arena || null,
  }));
}

function loadPlayers(dir: string): Player[] {
  return readCsv(dir, "fifa_data.csv").map((r) => ({
    id: parseIntSafe(r.ID),
    name: r.Name ?? "",
    age: parseIntSafe(r.Age),
    nationality: r.Nationality ?? "",
    overall: parseIntSafe(r.Overall),
    potential: parseIntSafe(r.Potential),
    club: r.Club ?? "",
    position: r.Position ?? "",
    jerseyNumber: r["Jersey Number"] || null,
    height: r.Height || null,
    weight: r.Weight || null,
    value: r.Value || null,
    wage: r.Wage || null,
    preferredFoot: r["Preferred Foot"] || null,
  }));
}

// --- Cached entry point ---------------------------------------------------

let cache: Dataset | null = null;

/**
 * Load (and cache) the full dataset from disk. Subsequent calls return the
 * cached instance unless `force` is set.
 */
export function loadDataset(force = false): Dataset {
  if (cache && !force) return cache;

  const dir = resolveDataDir();
  const matches: Match[] = [
    ...loadBrasileirao(dir),
    ...loadCup(dir),
    ...loadLibertadores(dir),
    ...loadBrFootball(dir),
    ...loadHistorical(dir),
  ];
  const players = loadPlayers(dir);
  const competitions = Array.from(new Set(matches.map((m) => m.competition))).sort();

  cache = { matches, players, competitions };
  return cache;
}
