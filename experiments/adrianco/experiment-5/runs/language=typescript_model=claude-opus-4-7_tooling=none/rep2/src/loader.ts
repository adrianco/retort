import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "csv-parse/sync";
import { normalizeTeam } from "./normalize.js";
import type { Dataset, Match, Player } from "./types.js";

const COMPETITION_LABELS = {
  Brasileirao: "Brasileirão Serie A",
  CopaDoBrasil: "Copa do Brasil",
  Libertadores: "Copa Libertadores",
  BRDataset: "BR Extended Stats",
  BrasileiraoHistorical: "Brasileirão Historical 2003-2019",
} as const;

function toNum(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (s === "" || s.toLowerCase() === "nan") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

function toInt(v: unknown): number | null {
  const n = toNum(v);
  return n === null ? null : Math.trunc(n);
}

function toDateISO(v: unknown): { date: string; time: string | null } {
  if (v === null || v === undefined) return { date: "", time: null };
  const raw = String(v).trim();
  if (!raw) return { date: "", time: null };
  // ISO "2023-09-24 18:30:00" or "2023-09-24"
  const isoMatch = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2}(?::\d{2})?))?/.exec(raw);
  if (isoMatch) return { date: `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`, time: isoMatch[4] ?? null };
  // Brazilian "DD/MM/YYYY"
  const brMatch = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(raw);
  if (brMatch) {
    const d = brMatch[1].padStart(2, "0");
    const m = brMatch[2].padStart(2, "0");
    return { date: `${brMatch[3]}-${m}-${d}`, time: null };
  }
  return { date: "", time: null };
}

function loadCsv(path: string): Record<string, string>[] {
  const text = readFileSync(path, "utf-8");
  return parse(text, {
    columns: true,
    skip_empty_lines: true,
    relax_column_count: true,
    relax_quotes: true,
    bom: true,
    trim: true,
  });
}

export function loadBrasileirao(dataDir: string): Match[] {
  const rows = loadCsv(join(dataDir, "Brasileirao_Matches.csv"));
  return rows.map((r, i) => {
    const { date, time } = toDateISO(r["datetime"]);
    return {
      id: `brasileirao:${i}`,
      competition: "Brasileirao",
      competitionLabel: COMPETITION_LABELS.Brasileirao,
      season: toInt(r["season"]),
      round: r["round"] ? String(r["round"]) : null,
      stage: null,
      date,
      time,
      homeTeam: normalizeTeam(r["home_team"]),
      awayTeam: normalizeTeam(r["away_team"]),
      homeTeamRaw: r["home_team"] ?? "",
      awayTeamRaw: r["away_team"] ?? "",
      homeTeamState: r["home_team_state"] || null,
      awayTeamState: r["away_team_state"] || null,
      homeGoals: toInt(r["home_goal"]),
      awayGoals: toInt(r["away_goal"]),
      arena: null,
    } satisfies Match;
  });
}

export function loadCopaDoBrasil(dataDir: string): Match[] {
  const rows = loadCsv(join(dataDir, "Brazilian_Cup_Matches.csv"));
  return rows.map((r, i) => {
    const { date, time } = toDateISO(r["datetime"]);
    return {
      id: `copa:${i}`,
      competition: "CopaDoBrasil",
      competitionLabel: COMPETITION_LABELS.CopaDoBrasil,
      season: toInt(r["season"]),
      round: r["round"] ? String(r["round"]) : null,
      stage: null,
      date,
      time,
      homeTeam: normalizeTeam(r["home_team"]),
      awayTeam: normalizeTeam(r["away_team"]),
      homeTeamRaw: r["home_team"] ?? "",
      awayTeamRaw: r["away_team"] ?? "",
      homeTeamState: null,
      awayTeamState: null,
      homeGoals: toInt(r["home_goal"]),
      awayGoals: toInt(r["away_goal"]),
      arena: null,
    } satisfies Match;
  });
}

export function loadLibertadores(dataDir: string): Match[] {
  const rows = loadCsv(join(dataDir, "Libertadores_Matches.csv"));
  return rows.map((r, i) => {
    const { date, time } = toDateISO(r["datetime"]);
    return {
      id: `libertadores:${i}`,
      competition: "Libertadores",
      competitionLabel: COMPETITION_LABELS.Libertadores,
      season: toInt(r["season"]),
      round: null,
      stage: r["stage"] || null,
      date,
      time,
      homeTeam: normalizeTeam(r["home_team"]),
      awayTeam: normalizeTeam(r["away_team"]),
      homeTeamRaw: r["home_team"] ?? "",
      awayTeamRaw: r["away_team"] ?? "",
      homeTeamState: null,
      awayTeamState: null,
      homeGoals: toInt(r["home_goal"]),
      awayGoals: toInt(r["away_goal"]),
      arena: null,
    } satisfies Match;
  });
}

export function loadBRDataset(dataDir: string): Match[] {
  const rows = loadCsv(join(dataDir, "BR-Football-Dataset.csv"));
  return rows.map((r, i) => {
    const { date } = toDateISO(r["date"]);
    return {
      id: `br-dataset:${i}`,
      competition: "BRDataset",
      competitionLabel: r["tournament"] || COMPETITION_LABELS.BRDataset,
      season: date ? Number(date.slice(0, 4)) : null,
      round: null,
      stage: null,
      date,
      time: r["time"] || null,
      homeTeam: normalizeTeam(r["home"]),
      awayTeam: normalizeTeam(r["away"]),
      homeTeamRaw: r["home"] ?? "",
      awayTeamRaw: r["away"] ?? "",
      homeTeamState: null,
      awayTeamState: null,
      homeGoals: toInt(r["home_goal"]),
      awayGoals: toInt(r["away_goal"]),
      arena: null,
      homeCorners: toNum(r["home_corner"]),
      awayCorners: toNum(r["away_corner"]),
      homeShots: toNum(r["home_shots"]),
      awayShots: toNum(r["away_shots"]),
      homeAttacks: toNum(r["home_attack"]),
      awayAttacks: toNum(r["away_attack"]),
      htResult: r["ht_result"] || null,
      atResult: r["at_result"] || null,
      totalCorners: toNum(r["total_corners"]),
    } satisfies Match;
  });
}

export function loadBrasileiraoHistorical(dataDir: string): Match[] {
  const rows = loadCsv(join(dataDir, "novo_campeonato_brasileiro.csv"));
  return rows.map((r, i) => {
    const { date } = toDateISO(r["Data"]);
    return {
      id: `brasileirao-hist:${r["ID"] || i}`,
      competition: "BrasileiraoHistorical",
      competitionLabel: COMPETITION_LABELS.BrasileiraoHistorical,
      season: toInt(r["Ano"]),
      round: r["Rodada"] ? String(r["Rodada"]) : null,
      stage: null,
      date,
      time: null,
      homeTeam: normalizeTeam(r["Equipe_mandante"]),
      awayTeam: normalizeTeam(r["Equipe_visitante"]),
      homeTeamRaw: r["Equipe_mandante"] ?? "",
      awayTeamRaw: r["Equipe_visitante"] ?? "",
      homeTeamState: r["Mandante_UF"] || null,
      awayTeamState: r["Visitante_UF"] || null,
      homeGoals: toInt(r["Gols_mandante"]),
      awayGoals: toInt(r["Gols_visitante"]),
      arena: r["Arena"] || null,
    } satisfies Match;
  });
}

export function loadPlayers(dataDir: string): Player[] {
  const rows = loadCsv(join(dataDir, "fifa_data.csv"));
  return rows.map((r) => ({
    id: toInt(r["ID"]) ?? 0,
    name: r["Name"] ?? "",
    age: toInt(r["Age"]),
    nationality: r["Nationality"] ?? "",
    overall: toInt(r["Overall"]),
    potential: toInt(r["Potential"]),
    club: r["Club"] ?? "",
    position: r["Position"] ?? "",
    jerseyNumber: toInt(r["Jersey Number"]),
    height: r["Height"] ?? "",
    weight: r["Weight"] ?? "",
    preferredFoot: r["Preferred Foot"] ?? "",
    crossing: toInt(r["Crossing"]),
    finishing: toInt(r["Finishing"]),
    dribbling: toInt(r["Dribbling"]),
    shortPassing: toInt(r["ShortPassing"]),
    longPassing: toInt(r["LongPassing"]),
    acceleration: toInt(r["Acceleration"]),
    sprintSpeed: toInt(r["SprintSpeed"]),
    stamina: toInt(r["Stamina"]),
    strength: toInt(r["Strength"]),
    shotPower: toInt(r["ShotPower"]),
  }));
}

export function loadAll(dataDir: string): Dataset {
  const matches = [
    ...loadBrasileirao(dataDir),
    ...loadCopaDoBrasil(dataDir),
    ...loadLibertadores(dataDir),
    ...loadBRDataset(dataDir),
    ...loadBrasileiraoHistorical(dataDir),
  ];
  const players = loadPlayers(dataDir);
  return { matches, players };
}
