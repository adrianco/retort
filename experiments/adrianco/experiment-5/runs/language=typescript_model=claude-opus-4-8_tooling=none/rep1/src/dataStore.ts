/**
 * Context
 * -------
 * Loads the six Kaggle CSV files from `data/kaggle/` and maps every row into
 * the unified `Match` / `Player` shapes defined in `types.ts`.
 *
 * The store is an in-memory cache: CSVs are parsed once (synchronously) on
 * first access and reused for all subsequent queries, which keeps simple
 * lookups well under the 2s budget in the spec. The data directory can be
 * overridden with the `SOCCER_DATA_DIR` environment variable; otherwise it is
 * resolved relative to this file so the server works from any CWD.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { parse } from "csv-parse/sync";
import type { Competition, Match, Player } from "./types.js";
import { canonicalKey, normalizeDate, normalizeTeamName, parseIntSafe } from "./normalize.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Resolve the directory containing the Kaggle CSV files. */
export function resolveDataDir(): string {
  if (process.env.SOCCER_DATA_DIR) {
    return resolve(process.env.SOCCER_DATA_DIR);
  }
  // src/ -> project root -> data/kaggle (works for both src and dist builds).
  return resolve(__dirname, "..", "data", "kaggle");
}

interface CsvRow {
  [key: string]: string;
}

function readCsv(file: string): CsvRow[] {
  const text = readFileSync(file, "utf8");
  return parse(text, {
    columns: (header: string[]) =>
      // Strip a leading UTF-8 BOM from the first column name (fifa_data.csv).
      header.map((h) => h.replace(/^﻿/, "").trim()),
    skip_empty_lines: true,
    relax_quotes: true,
    relax_column_count: true,
    trim: true,
  }) as CsvRow[];
}

function buildMatch(
  competition: Competition,
  source: string,
  homeRaw: string,
  awayRaw: string,
  homeGoal: number | null,
  awayGoal: number | null,
  season: number | null,
  date: string | null,
  round: number | null,
  stage: string | null,
  arena: string | null,
): Match {
  return {
    competition,
    homeTeam: normalizeTeamName(homeRaw),
    awayTeam: normalizeTeamName(awayRaw),
    homeTeamRaw: homeRaw,
    awayTeamRaw: awayRaw,
    homeGoal,
    awayGoal,
    season,
    date,
    round,
    stage,
    arena,
    source,
  };
}

/** In-memory dataset loaded from the CSV files. */
export class DataStore {
  private _matches: Match[] | null = null;
  private _players: Player[] | null = null;
  readonly dataDir: string;

  constructor(dataDir: string = resolveDataDir()) {
    this.dataDir = dataDir;
  }

  /** All matches across every competition (lazily loaded & cached). */
  get matches(): Match[] {
    if (this._matches === null) this._matches = this.loadMatches();
    return this._matches;
  }

  /** All FIFA players (lazily loaded & cached). */
  get players(): Player[] {
    if (this._players === null) this._players = this.loadPlayers();
    return this._players;
  }

  /** Force eager loading of every dataset (used at server startup). */
  loadAll(): { matches: number; players: number } {
    return { matches: this.matches.length, players: this.players.length };
  }

  private file(name: string): string {
    return join(this.dataDir, name);
  }

  private loadMatches(): Match[] {
    const matches: Match[] = [];

    // 1. Brasileirão Série A
    for (const r of readCsv(this.file("Brasileirao_Matches.csv"))) {
      matches.push(
        buildMatch(
          "Brasileirão Série A",
          "Brasileirao_Matches.csv",
          r.home_team,
          r.away_team,
          parseIntSafe(r.home_goal),
          parseIntSafe(r.away_goal),
          parseIntSafe(r.season),
          normalizeDate(r.datetime),
          parseIntSafe(r.round),
          null,
          null,
        ),
      );
    }

    // 2. Copa do Brasil
    for (const r of readCsv(this.file("Brazilian_Cup_Matches.csv"))) {
      matches.push(
        buildMatch(
          "Copa do Brasil",
          "Brazilian_Cup_Matches.csv",
          r.home_team,
          r.away_team,
          parseIntSafe(r.home_goal),
          parseIntSafe(r.away_goal),
          parseIntSafe(r.season),
          normalizeDate(r.datetime),
          null,
          r.round ? `Round ${r.round}` : null,
          null,
        ),
      );
    }

    // 3. Copa Libertadores
    for (const r of readCsv(this.file("Libertadores_Matches.csv"))) {
      matches.push(
        buildMatch(
          "Copa Libertadores",
          "Libertadores_Matches.csv",
          r.home_team,
          r.away_team,
          parseIntSafe(r.home_goal),
          parseIntSafe(r.away_goal),
          parseIntSafe(r.season),
          normalizeDate(r.datetime),
          null,
          r.stage ?? null,
          null,
        ),
      );
    }

    // 4. Extended match statistics (BR-Football-Dataset). Maps tournament text
    //    to a canonical competition; non-Série-A Brazilian leagues are kept.
    for (const r of readCsv(this.file("BR-Football-Dataset.csv"))) {
      const competition = mapTournament(r.tournament);
      if (!competition) continue;
      matches.push(
        buildMatch(
          competition,
          "BR-Football-Dataset.csv",
          r.home,
          r.away,
          parseIntSafe(r.home_goal),
          parseIntSafe(r.away_goal),
          yearFromDate(normalizeDate(r.date)),
          normalizeDate(r.date),
          null,
          null,
          null,
        ),
      );
    }

    // 5. Historical Brasileirão 2003-2019
    for (const r of readCsv(this.file("novo_campeonato_brasileiro.csv"))) {
      matches.push(
        buildMatch(
          "Brasileirão Série A",
          "novo_campeonato_brasileiro.csv",
          r.Equipe_mandante,
          r.Equipe_visitante,
          parseIntSafe(r.Gols_mandante),
          parseIntSafe(r.Gols_visitante),
          parseIntSafe(r.Ano),
          normalizeDate(r.Data),
          parseIntSafe(r.Rodada),
          null,
          r.Arena || null,
        ),
      );
    }

    return dedupeMatches(matches);
  }

  private loadPlayers(): Player[] {
    const players: Player[] = [];
    for (const r of readCsv(this.file("fifa_data.csv"))) {
      players.push({
        id: r.ID ?? "",
        name: r.Name ?? "",
        age: parseIntSafe(r.Age),
        nationality: r.Nationality ?? "",
        overall: parseIntSafe(r.Overall),
        potential: parseIntSafe(r.Potential),
        club: r.Club ?? "",
        position: r.Position ?? "",
        jerseyNumber: r["Jersey Number"] ?? "",
        height: r.Height ?? "",
        weight: r.Weight ?? "",
        value: r.Value ?? "",
        wage: r.Wage ?? "",
        preferredFoot: r["Preferred Foot"] ?? "",
      });
    }
    return players;
  }
}

/**
 * The source files overlap heavily — e.g. Brasileirão Série A 2012-2019 appears
 * in Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv AND
 * BR-Football-Dataset.csv. Without dedup, standings and aggregate stats are
 * inflated 2-3x. A league fixture is uniquely identified within a season by
 * (competition, season, home, away); when the same fixture is seen more than
 * once we keep the record with the most complete information (date, round,
 * arena), which preserves details across sources.
 */
function dedupeMatches(matches: Match[]): Match[] {
  const completeness = (m: Match): number =>
    (m.date ? 1 : 0) + (m.round != null ? 1 : 0) + (m.stage ? 1 : 0) + (m.arena ? 1 : 0);

  const byKey = new Map<string, Match>();
  for (const m of matches) {
    const key = [
      m.competition,
      m.season ?? "?",
      canonicalKey(m.homeTeamRaw),
      canonicalKey(m.awayTeamRaw),
    ].join("|");
    const existing = byKey.get(key);
    if (!existing || completeness(m) > completeness(existing)) {
      byKey.set(key, m);
    }
  }
  return [...byKey.values()];
}

/** Map the free-text `tournament` column of BR-Football-Dataset to a competition. */
function mapTournament(tournament: string | undefined): Competition | null {
  const t = (tournament ?? "").trim().toLowerCase();
  if (t === "serie a") return "Brasileirão Série A";
  if (t === "serie b") return "Brasileirão Série B";
  if (t === "serie c") return "Brasileirão Série C";
  if (t === "copa do brasil") return "Copa do Brasil";
  return null;
}

function yearFromDate(iso: string | null): number | null {
  if (!iso) return null;
  return parseIntSafe(iso.slice(0, 4));
}

/** Shared singleton used by the server and query layer. */
let shared: DataStore | null = null;
export function getDataStore(): DataStore {
  if (shared === null) shared = new DataStore();
  return shared;
}
