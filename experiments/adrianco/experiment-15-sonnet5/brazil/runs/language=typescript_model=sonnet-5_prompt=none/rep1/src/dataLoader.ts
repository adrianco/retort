import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "csv-parse/sync";
import { parseFlexibleDate, parseTeamName } from "./normalize.js";
import type { Dataset, Match, MatchExtraStats, Player } from "./types.js";

const PROJECT_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DATA_DIR = join(PROJECT_ROOT, "data", "kaggle");

function readCsv(fileName: string): Record<string, string>[] {
  const content = readFileSync(join(DATA_DIR, fileName), "utf8");
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true,
  }) as Record<string, string>[];
}

function toInt(value: string | undefined | null): number | null {
  if (value === undefined || value === null || value.trim() === "") return null;
  const n = Number.parseFloat(value);
  return Number.isFinite(n) ? Math.round(n) : null;
}

function toFloat(value: string | undefined | null): number | null {
  if (value === undefined || value === null || value.trim() === "") return null;
  const n = Number.parseFloat(value);
  return Number.isFinite(n) ? n : null;
}

function nonEmpty(value: string | undefined | null): string | null {
  if (value === undefined || value === null) return null;
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

let idCounter = 0;
function nextId(prefix: string): string {
  idCounter += 1;
  return `${prefix}-${idCounter}`;
}

function loadBrasileirao(): Match[] {
  return readCsv("Brasileirao_Matches.csv").map((row) => {
    const date = parseFlexibleDate(row.datetime);
    return {
      id: nextId("bra"),
      source: "Brasileirao",
      competition: "Brasileirao Serie A",
      season: toInt(row.season),
      round: nonEmpty(row.round),
      stage: null,
      date,
      dateRaw: row.datetime,
      homeTeam: parseTeamName(row.home_team),
      awayTeam: parseTeamName(row.away_team),
      homeGoals: toInt(row.home_goal),
      awayGoals: toInt(row.away_goal),
      stadium: null,
      extra: null,
    } satisfies Match;
  });
}

function loadCopaDoBrasil(): Match[] {
  return readCsv("Brazilian_Cup_Matches.csv").map((row) => {
    const date = parseFlexibleDate(row.datetime);
    return {
      id: nextId("cdb"),
      source: "Copa do Brasil",
      competition: "Copa do Brasil",
      season: toInt(row.season),
      round: nonEmpty(row.round),
      stage: null,
      date,
      dateRaw: row.datetime,
      homeTeam: parseTeamName(row.home_team),
      awayTeam: parseTeamName(row.away_team),
      homeGoals: toInt(row.home_goal),
      awayGoals: toInt(row.away_goal),
      stadium: null,
      extra: null,
    } satisfies Match;
  });
}

function loadLibertadores(): Match[] {
  return readCsv("Libertadores_Matches.csv").map((row) => {
    const date = parseFlexibleDate(row.datetime);
    return {
      id: nextId("lib"),
      source: "Libertadores",
      competition: "Copa Libertadores",
      season: toInt(row.season),
      round: null,
      stage: nonEmpty(row.stage),
      date,
      dateRaw: row.datetime,
      homeTeam: parseTeamName(row.home_team),
      awayTeam: parseTeamName(row.away_team),
      homeGoals: toInt(row.home_goal),
      awayGoals: toInt(row.away_goal),
      stadium: null,
      extra: null,
    } satisfies Match;
  });
}

function loadBrFootball(): Match[] {
  return readCsv("BR-Football-Dataset.csv").map((row) => {
    const dateRaw = row.time ? `${row.date} ${row.time}` : row.date;
    const date = parseFlexibleDate(row.date);
    const extra: MatchExtraStats = {
      homeCorners: toFloat(row.home_corner),
      awayCorners: toFloat(row.away_corner),
      homeShots: toFloat(row.home_shots),
      awayShots: toFloat(row.away_shots),
      homeAttacks: toFloat(row.home_attack),
      awayAttacks: toFloat(row.away_attack),
    };
    return {
      id: nextId("brf"),
      source: "BR-Football",
      competition: nonEmpty(row.tournament) ?? "Unknown",
      season: date ? date.getUTCFullYear() : null,
      round: null,
      stage: null,
      date,
      dateRaw,
      homeTeam: parseTeamName(row.home),
      awayTeam: parseTeamName(row.away),
      homeGoals: toInt(row.home_goal),
      awayGoals: toInt(row.away_goal),
      stadium: null,
      extra,
    } satisfies Match;
  });
}

function loadHistoricalBrasileirao(): Match[] {
  return readCsv("novo_campeonato_brasileiro.csv").map((row) => {
    const date = parseFlexibleDate(row.Data);
    const homeRaw = row.Mandante_UF ? `${row.Equipe_mandante}-${row.Mandante_UF}` : row.Equipe_mandante;
    const awayRaw = row.Visitante_UF ? `${row.Equipe_visitante}-${row.Visitante_UF}` : row.Equipe_visitante;
    return {
      id: nonEmpty(row.ID) ?? nextId("hist"),
      source: "Historical-Brasileirao",
      competition: "Brasileirao Serie A",
      season: toInt(row.Ano),
      round: nonEmpty(row.Rodada),
      stage: null,
      date,
      dateRaw: row.Data,
      homeTeam: parseTeamName(homeRaw),
      awayTeam: parseTeamName(awayRaw),
      homeGoals: toInt(row.Gols_mandante),
      awayGoals: toInt(row.Gols_visitante),
      stadium: nonEmpty(row.Arena),
      extra: null,
    } satisfies Match;
  });
}

function loadPlayers(): Player[] {
  return readCsv("fifa_data.csv").map((row) => {
    return {
      id: nonEmpty(row.ID) ?? nextId("player"),
      name: row.Name ?? "",
      age: toInt(row.Age),
      nationality: row.Nationality ?? "",
      overall: toInt(row.Overall),
      potential: toInt(row.Potential),
      club: row.Club ?? "",
      position: row.Position ?? "",
      jerseyNumber: toInt(row["Jersey Number"]),
      preferredFoot: nonEmpty(row["Preferred Foot"]),
      height: nonEmpty(row.Height),
      weight: nonEmpty(row.Weight),
      valueRaw: nonEmpty(row.Value),
      wageRaw: nonEmpty(row.Wage),
    } satisfies Player;
  });
}

/** Brasileirao_Matches.csv (2012-2022) and novo_campeonato_brasileiro.csv
 * (2003-2019) both describe the same competition (Brasileirao Serie A) and
 * overlap for 2012-2019. To avoid double-counting real-world matches in
 * standings/records, we keep the newer, cleaner dataset for any season it
 * covers and only fall back to the historical one for seasons it doesn't. */
function mergeBrasileiraoSources(primary: Match[], historical: Match[]): Match[] {
  const seasonsWithPrimary = new Set(
    primary.map((m) => m.season).filter((s): s is number => s !== null),
  );
  const fallback = historical.filter((m) => m.season !== null && !seasonsWithPrimary.has(m.season));
  return [...primary, ...fallback];
}

function seasonsOf(matches: Match[]): Set<number> {
  return new Set(matches.map((m) => m.season).filter((s): s is number => s !== null));
}

/** BR-Football's own "Serie A" and "Copa do Brasil" tournament rows describe
 * the same real-world matches already covered by the dedicated Brasileirao
 * and Copa do Brasil datasets for the seasons those cover, which would
 * otherwise double-count matches in aggregate stats and head-to-head
 * records. We drop BR-Football rows for competition+season combinations
 * already covered elsewhere, keeping only the seasons/tournaments (Serie B,
 * Serie C, and any season not covered by the dedicated datasets) that are
 * unique to it - along with its extra stats (corners, shots, attacks). */
function dedupeBrFootball(brFootball: Match[], brasileiraoSeasons: Set<number>, copaDoBrasilSeasons: Set<number>): Match[] {
  return brFootball.filter((m) => {
    if (m.season === null) return true;
    if (m.competition === "Serie A") return !brasileiraoSeasons.has(m.season);
    if (m.competition === "Copa do Brasil") return !copaDoBrasilSeasons.has(m.season);
    return true;
  });
}

let cachedDataset: Dataset | null = null;

/** Loads and parses all six CSV datasets once, then serves the parsed
 * in-memory result on subsequent calls. */
export function getDataset(): Dataset {
  if (cachedDataset) return cachedDataset;

  const brasileirao = mergeBrasileiraoSources(loadBrasileirao(), loadHistoricalBrasileirao());
  const copaDoBrasil = loadCopaDoBrasil();
  const brFootball = dedupeBrFootball(loadBrFootball(), seasonsOf(brasileirao), seasonsOf(copaDoBrasil));

  const matches: Match[] = [...brasileirao, ...copaDoBrasil, ...loadLibertadores(), ...brFootball];
  const players = loadPlayers();

  cachedDataset = { matches, players };
  return cachedDataset;
}
