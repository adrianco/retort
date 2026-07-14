/**
 * The DataStore loads every provided CSV file once and exposes the normalized
 * in-memory collections (matches + players) that all queries read from.
 *
 * Loading all six files into memory keeps every query well under the 2s/5s
 * performance targets in the spec: the datasets total ~40k matches and ~18k
 * players, which is trivial to scan in memory.
 */
import { existsSync } from "node:fs";
import { join } from "node:path";
import { loadCsv, type CsvRow } from "./csv.js";
import { cleanTeamName, parseDate, parseGoals, parseIntOrNull } from "./normalize.js";
import type { Match, Player } from "./types.js";

/** Canonical Brasileirão league name used for league-table calculations. */
export const BRASILEIRAO = "Brasileirão Série A";
export const COPA_DO_BRASIL = "Copa do Brasil";
export const LIBERTADORES = "Copa Libertadores";

const MATCH_FILES = {
  brasileirao: "Brasileirao_Matches.csv",
  cup: "Brazilian_Cup_Matches.csv",
  libertadores: "Libertadores_Matches.csv",
  extended: "BR-Football-Dataset.csv",
  historical: "novo_campeonato_brasileiro.csv",
} as const;

const PLAYER_FILE = "fifa_data.csv";

export class DataStore {
  readonly matches: Match[] = [];
  readonly players: Player[] = [];
  private loaded = false;

  constructor(private readonly dataDir: string) {}

  /** Load and normalize all datasets. Idempotent. */
  load(): void {
    if (this.loaded) return;
    this.loadBrasileirao();
    this.loadCup();
    this.loadLibertadores();
    this.loadExtended();
    this.loadHistorical();
    this.loadPlayers();
    this.loaded = true;
  }

  private filePath(name: string): string {
    return join(this.dataDir, name);
  }

  private readFile(name: string): CsvRow[] {
    const path = this.filePath(name);
    if (!existsSync(path)) {
      throw new Error(`Expected data file not found: ${path}`);
    }
    return loadCsv(path);
  }

  /** Brasileirao_Matches.csv — Série A 2012-2022 with rounds + team states. */
  private loadBrasileirao(): void {
    const source = MATCH_FILES.brasileirao;
    for (const row of this.readFile(source)) {
      this.matches.push({
        competition: BRASILEIRAO,
        source,
        date: parseDate(row.datetime),
        dateRaw: row.datetime ?? null,
        season: parseIntOrNull(row.season),
        round: emptyToNull(row.round),
        stage: null,
        homeTeam: cleanTeamName(row.home_team ?? ""),
        awayTeam: cleanTeamName(row.away_team ?? ""),
        homeTeamRaw: row.home_team ?? "",
        awayTeamRaw: row.away_team ?? "",
        homeGoals: parseGoals(row.home_goal),
        awayGoals: parseGoals(row.away_goal),
      });
    }
  }

  /** Brazilian_Cup_Matches.csv — Copa do Brasil. */
  private loadCup(): void {
    const source = MATCH_FILES.cup;
    for (const row of this.readFile(source)) {
      this.matches.push({
        competition: COPA_DO_BRASIL,
        source,
        date: parseDate(row.datetime),
        dateRaw: row.datetime ?? null,
        season: parseIntOrNull(row.season),
        round: emptyToNull(row.round),
        stage: emptyToNull(row.round),
        homeTeam: cleanTeamName(row.home_team ?? ""),
        awayTeam: cleanTeamName(row.away_team ?? ""),
        homeTeamRaw: row.home_team ?? "",
        awayTeamRaw: row.away_team ?? "",
        homeGoals: parseGoals(row.home_goal),
        awayGoals: parseGoals(row.away_goal),
      });
    }
  }

  /** Libertadores_Matches.csv — Copa Libertadores with tournament stage. */
  private loadLibertadores(): void {
    const source = MATCH_FILES.libertadores;
    for (const row of this.readFile(source)) {
      this.matches.push({
        competition: LIBERTADORES,
        source,
        date: parseDate(row.datetime),
        dateRaw: row.datetime ?? null,
        season: parseIntOrNull(row.season),
        round: null,
        stage: emptyToNull(row.stage),
        homeTeam: cleanTeamName(row.home_team ?? ""),
        awayTeam: cleanTeamName(row.away_team ?? ""),
        homeTeamRaw: row.home_team ?? "",
        awayTeamRaw: row.away_team ?? "",
        homeGoals: parseGoals(row.home_goal),
        awayGoals: parseGoals(row.away_goal),
      });
    }
  }

  /** BR-Football-Dataset.csv — extended stats, tournament column drives competition. */
  private loadExtended(): void {
    const source = MATCH_FILES.extended;
    for (const row of this.readFile(source)) {
      const date = parseDate(row.date);
      this.matches.push({
        competition: (row.tournament ?? "").trim() || "Unknown",
        source,
        date,
        dateRaw: row.date ?? null,
        season: date ? date.getUTCFullYear() : null,
        round: null,
        stage: null,
        homeTeam: cleanTeamName(row.home ?? ""),
        awayTeam: cleanTeamName(row.away ?? ""),
        homeTeamRaw: row.home ?? "",
        awayTeamRaw: row.away ?? "",
        homeGoals: parseGoals(row.home_goal),
        awayGoals: parseGoals(row.away_goal),
      });
    }
  }

  /** novo_campeonato_brasileiro.csv — historical Série A 2003-2019. */
  private loadHistorical(): void {
    const source = MATCH_FILES.historical;
    for (const row of this.readFile(source)) {
      this.matches.push({
        competition: BRASILEIRAO,
        source,
        date: parseDate(row.Data),
        dateRaw: row.Data ?? null,
        season: parseIntOrNull(row.Ano),
        round: emptyToNull(row.Rodada),
        stage: null,
        homeTeam: cleanTeamName(row.Equipe_mandante ?? ""),
        awayTeam: cleanTeamName(row.Equipe_visitante ?? ""),
        homeTeamRaw: row.Equipe_mandante ?? "",
        awayTeamRaw: row.Equipe_visitante ?? "",
        homeGoals: parseGoals(row.Gols_mandante),
        awayGoals: parseGoals(row.Gols_visitante),
      });
    }
  }

  /** fifa_data.csv — player database. */
  private loadPlayers(): void {
    for (const row of this.readFile(PLAYER_FILE)) {
      const id = parseIntOrNull(row.ID);
      if (id === null) continue;
      this.players.push({
        id,
        name: (row.Name ?? "").trim(),
        age: parseIntOrNull(row.Age),
        nationality: (row.Nationality ?? "").trim(),
        overall: parseIntOrNull(row.Overall),
        potential: parseIntOrNull(row.Potential),
        club: (row.Club ?? "").trim(),
        position: (row.Position ?? "").trim(),
        jerseyNumber: parseIntOrNull(row["Jersey Number"]),
        height: (row.Height ?? "").trim(),
        weight: (row.Weight ?? "").trim(),
        preferredFoot: (row["Preferred Foot"] ?? "").trim(),
        value: (row.Value ?? "").trim(),
        wage: (row.Wage ?? "").trim(),
      });
    }
  }
}

function emptyToNull(value: string | undefined): string | null {
  if (value === undefined) return null;
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

/** Resolve the default data directory (…/data/kaggle) relative to a base. */
export function defaultDataDir(baseDir: string): string {
  return join(baseDir, "data", "kaggle");
}
