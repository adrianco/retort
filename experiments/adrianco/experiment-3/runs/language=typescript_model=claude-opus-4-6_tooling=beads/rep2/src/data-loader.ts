import { parse } from "csv-parse/sync";
import { readFileSync } from "fs";
import { join } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";
import type { UnifiedMatch, FifaPlayer } from "./types.js";
import {
  normalizeTeamName,
  parseDateToISO,
  safeParseInt,
  safeParseFloat,
} from "./normalize.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DATA_DIR = join(__dirname, "..", "data", "kaggle");

function readCsv(filename: string): Record<string, string>[] {
  const content = readFileSync(join(DATA_DIR, filename), "utf-8");
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true,
    relax_quotes: true,
    relax_column_count: true,
  });
}

function loadBrasileiraoMatches(): UnifiedMatch[] {
  const rows = readCsv("Brasileirao_Matches.csv");
  return rows.map((r) => ({
    datetime: r.datetime?.split(" ")[0] || "",
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoal: safeParseInt(r.home_goal),
    awayGoal: safeParseInt(r.away_goal),
    season: safeParseInt(r.season),
    competition: "Brasileirão",
    round: safeParseInt(r.round),
    homeTeamState: r.home_team_state,
    awayTeamState: r.away_team_state,
  }));
}

function loadCupMatches(): UnifiedMatch[] {
  const rows = readCsv("Brazilian_Cup_Matches.csv");
  return rows.map((r) => ({
    datetime: r.datetime?.split(" ")[0] || "",
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoal: safeParseInt(r.home_goal),
    awayGoal: safeParseInt(r.away_goal),
    season: safeParseInt(r.season),
    competition: "Copa do Brasil",
    round: r.round,
  }));
}

function loadLibertadoresMatches(): UnifiedMatch[] {
  const rows = readCsv("Libertadores_Matches.csv");
  return rows.map((r) => ({
    datetime: r.datetime?.split(" ")[0] || "",
    homeTeam: normalizeTeamName(r.home_team),
    awayTeam: normalizeTeamName(r.away_team),
    homeGoal: safeParseInt(r.home_goal),
    awayGoal: safeParseInt(r.away_goal),
    season: safeParseInt(r.season),
    competition: "Copa Libertadores",
    stage: r.stage,
  }));
}

function loadExtendedMatches(): UnifiedMatch[] {
  const rows = readCsv("BR-Football-Dataset.csv");
  return rows.map((r) => ({
    datetime: r.date || "",
    homeTeam: normalizeTeamName(r.home),
    awayTeam: normalizeTeamName(r.away),
    homeGoal: safeParseInt(r.home_goal),
    awayGoal: safeParseInt(r.away_goal),
    season: safeParseInt((r.date || "").split("-")[0]),
    competition: r.tournament || "Unknown",
    homeCorner: safeParseFloat(r.home_corner),
    awayCorner: safeParseFloat(r.away_corner),
    homeShots: safeParseFloat(r.home_shots),
    awayShots: safeParseFloat(r.away_shots),
  }));
}

function loadHistoricalMatches(): UnifiedMatch[] {
  const rows = readCsv("novo_campeonato_brasileiro.csv");
  return rows.map((r) => ({
    datetime: parseDateToISO(r.Data),
    homeTeam: normalizeTeamName(r.Equipe_mandante),
    awayTeam: normalizeTeamName(r.Equipe_visitante),
    homeGoal: safeParseInt(r.Gols_mandante),
    awayGoal: safeParseInt(r.Gols_visitante),
    season: safeParseInt(r.Ano),
    competition: "Brasileirão",
    round: safeParseInt(r.Rodada),
    homeTeamState: r.Mandante_UF,
    awayTeamState: r.Visitante_UF,
    arena: r.Arena,
  }));
}

function loadFifaPlayers(): FifaPlayer[] {
  const rows = readCsv("fifa_data.csv");
  return rows.map((r) => ({
    id: safeParseInt(r.ID),
    name: r.Name || "",
    age: safeParseInt(r.Age),
    nationality: r.Nationality || "",
    overall: safeParseInt(r.Overall),
    potential: safeParseInt(r.Potential),
    club: r.Club || "",
    position: r.Position || "",
    jerseyNumber: safeParseInt(r["Jersey Number"]),
    height: r.Height || "",
    weight: r.Weight || "",
    crossing: safeParseInt(r.Crossing),
    finishing: safeParseInt(r.Finishing),
    headingAccuracy: safeParseInt(r.HeadingAccuracy),
    shortPassing: safeParseInt(r.ShortPassing),
    dribbling: safeParseInt(r.Dribbling),
    curve: safeParseInt(r.Curve),
    fkAccuracy: safeParseInt(r.FKAccuracy),
    longPassing: safeParseInt(r.LongPassing),
    ballControl: safeParseInt(r.BallControl),
    acceleration: safeParseInt(r.Acceleration),
    sprintSpeed: safeParseInt(r.SprintSpeed),
    agility: safeParseInt(r.Agility),
    reactions: safeParseInt(r.Reactions),
    balance: safeParseInt(r.Balance),
    shotPower: safeParseInt(r.ShotPower),
    jumping: safeParseInt(r.Jumping),
    stamina: safeParseInt(r.Stamina),
    strength: safeParseInt(r.Strength),
    longShots: safeParseInt(r.LongShots),
    aggression: safeParseInt(r.Aggression),
    interceptions: safeParseInt(r.Interceptions),
    positioning: safeParseInt(r.Positioning),
    vision: safeParseInt(r.Vision),
    penalties: safeParseInt(r.Penalties),
    composure: safeParseInt(r.Composure),
    marking: safeParseInt(r.Marking),
    standingTackle: safeParseInt(r.StandingTackle),
    slidingTackle: safeParseInt(r.SlidingTackle),
    preferredFoot: r["Preferred Foot"] || "",
    workRate: r["Work Rate"] || "",
    value: r.Value || "",
    wage: r.Wage || "",
  }));
}

export interface SoccerData {
  matches: UnifiedMatch[];
  players: FifaPlayer[];
}

let cachedData: SoccerData | null = null;

export function loadAllData(): SoccerData {
  if (cachedData) return cachedData;

  const brasileirao = loadBrasileiraoMatches();
  const cup = loadCupMatches();
  const libertadores = loadLibertadoresMatches();
  const extended = loadExtendedMatches();
  const historical = loadHistoricalMatches();
  const players = loadFifaPlayers();

  cachedData = {
    matches: [...brasileirao, ...cup, ...libertadores, ...extended, ...historical],
    players,
  };

  return cachedData;
}

export function getDataStats(): {
  brasileirao: number;
  cup: number;
  libertadores: number;
  extended: number;
  historical: number;
  totalMatches: number;
  players: number;
} {
  const brasileirao = loadBrasileiraoMatches();
  const cup = loadCupMatches();
  const libertadores = loadLibertadoresMatches();
  const extended = loadExtendedMatches();
  const historical = loadHistoricalMatches();
  const players = loadFifaPlayers();

  return {
    brasileirao: brasileirao.length,
    cup: cup.length,
    libertadores: libertadores.length,
    extended: extended.length,
    historical: historical.length,
    totalMatches:
      brasileirao.length + cup.length + libertadores.length + extended.length + historical.length,
    players: players.length,
  };
}
