import { readFileSync } from "node:fs";
import { parse } from "csv-parse/sync";
import { Match, Player, DataStore } from "./types.js";
import { normalizeTeamName } from "./normalize.js";

function parseDate(raw: string): string {
  if (!raw) return "";
  const trimmed = raw.trim();

  // DD/MM/YYYY format
  const brMatch = trimmed.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (brMatch) {
    return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;
  }

  // ISO or datetime format — extract date part
  const isoMatch = trimmed.match(/^(\d{4}-\d{2}-\d{2})/);
  if (isoMatch) {
    return isoMatch[1];
  }

  return trimmed;
}

function safeInt(val: unknown): number {
  if (val === null || val === undefined || val === "") return 0;
  const n = parseInt(String(val), 10);
  return isNaN(n) ? 0 : n;
}

function safeFloat(val: unknown): number {
  if (val === null || val === undefined || val === "") return 0;
  const n = parseFloat(String(val));
  return isNaN(n) ? 0 : n;
}

function parseCsv(filePath: string): Record<string, string>[] {
  const content = readFileSync(filePath, "utf-8");
  // Remove BOM if present
  const cleaned = content.replace(/^﻿/, "");
  return parse(cleaned, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true,
  });
}

function loadBrasileiraoMatches(dataDir: string): Match[] {
  const rows = parseCsv(`${dataDir}/Brasileirao_Matches.csv`);
  return rows.map((r) => ({
    date: parseDate(r.datetime),
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoals: safeInt(r.home_goal),
    awayGoals: safeInt(r.away_goal),
    season: safeInt(r.season),
    competition: "Brasileirão Serie A",
    round: r.round,
    homeTeamState: r.home_team_state,
    awayTeamState: r.away_team_state,
  }));
}

function loadCupMatches(dataDir: string): Match[] {
  const rows = parseCsv(`${dataDir}/Brazilian_Cup_Matches.csv`);
  return rows.map((r) => ({
    date: parseDate(r.datetime),
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoals: safeInt(r.home_goal),
    awayGoals: safeInt(r.away_goal),
    season: safeInt(r.season),
    competition: "Copa do Brasil",
    round: r.round,
  }));
}

function loadLibertadoresMatches(dataDir: string): Match[] {
  const rows = parseCsv(`${dataDir}/Libertadores_Matches.csv`);
  return rows.map((r) => ({
    date: parseDate(r.datetime),
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoals: safeInt(r.home_goal),
    awayGoals: safeInt(r.away_goal),
    season: safeInt(r.season),
    competition: "Copa Libertadores",
    stage: r.stage,
  }));
}

function loadExtendedMatches(dataDir: string): Match[] {
  const rows = parseCsv(`${dataDir}/BR-Football-Dataset.csv`);
  return rows.map((r) => ({
    date: parseDate(r.date),
    homeTeam: normalizeTeamName(r.home),
    awayTeam: normalizeTeamName(r.away),
    homeGoals: safeInt(r.home_goal),
    awayGoals: safeInt(r.away_goal),
    season: safeInt(r.date?.substring(0, 4)),
    competition: r.tournament || "Unknown",
    homeCorners: safeFloat(r.home_corner) || undefined,
    awayCorners: safeFloat(r.away_corner) || undefined,
    homeShots: safeFloat(r.home_shots) || undefined,
    awayShots: safeFloat(r.away_shots) || undefined,
  }));
}

function loadHistoricalMatches(dataDir: string): Match[] {
  const rows = parseCsv(`${dataDir}/novo_campeonato_brasileiro.csv`);
  return rows.map((r) => ({
    date: parseDate(r.Data),
    homeTeam: normalizeTeamName(r.Equipe_mandante),
    awayTeam: normalizeTeamName(r.Equipe_visitante),
    homeGoals: safeInt(r.Gols_mandante),
    awayGoals: safeInt(r.Gols_visitante),
    season: safeInt(r.Ano),
    competition: "Brasileirão Serie A",
    round: r.Rodada,
    stadium: r.Arena,
    homeTeamState: r.Mandante_UF,
    awayTeamState: r.Visitante_UF,
  }));
}

function loadPlayers(dataDir: string): Player[] {
  const rows = parseCsv(`${dataDir}/fifa_data.csv`);
  return rows.map((r) => ({
    id: safeInt(r.ID),
    name: r.Name || "",
    age: safeInt(r.Age),
    nationality: r.Nationality || "",
    overall: safeInt(r.Overall),
    potential: safeInt(r.Potential),
    club: r.Club || "",
    position: r.Position || "",
    jerseyNumber: safeInt(r["Jersey Number"]) || undefined,
    height: r.Height || undefined,
    weight: r.Weight || undefined,
    preferredFoot: r["Preferred Foot"] || undefined,
    value: r.Value || undefined,
    wage: r.Wage || undefined,
    crossing: safeInt(r.Crossing) || undefined,
    finishing: safeInt(r.Finishing) || undefined,
    headingAccuracy: safeInt(r.HeadingAccuracy) || undefined,
    shortPassing: safeInt(r.ShortPassing) || undefined,
    dribbling: safeInt(r.Dribbling) || undefined,
    curve: safeInt(r.Curve) || undefined,
    longPassing: safeInt(r.LongPassing) || undefined,
    ballControl: safeInt(r.BallControl) || undefined,
    acceleration: safeInt(r.Acceleration) || undefined,
    sprintSpeed: safeInt(r.SprintSpeed) || undefined,
    agility: safeInt(r.Agility) || undefined,
    reactions: safeInt(r.Reactions) || undefined,
    shotPower: safeInt(r.ShotPower) || undefined,
    stamina: safeInt(r.Stamina) || undefined,
    strength: safeInt(r.Strength) || undefined,
    longShots: safeInt(r.LongShots) || undefined,
    aggression: safeInt(r.Aggression) || undefined,
    interceptions: safeInt(r.Interceptions) || undefined,
    positioning: safeInt(r.Positioning) || undefined,
    vision: safeInt(r.Vision) || undefined,
    penalties: safeInt(r.Penalties) || undefined,
    composure: safeInt(r.Composure) || undefined,
  }));
}

export function loadAllData(dataDir: string): DataStore {
  const brasileirao = loadBrasileiraoMatches(dataDir);
  const cup = loadCupMatches(dataDir);
  const libertadores = loadLibertadoresMatches(dataDir);
  const extended = loadExtendedMatches(dataDir);
  const historical = loadHistoricalMatches(dataDir);
  const players = loadPlayers(dataDir);

  const matches = [...brasileirao, ...cup, ...libertadores, ...extended, ...historical];

  return { matches, players };
}
