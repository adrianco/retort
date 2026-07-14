import fs from "node:fs";
import path from "node:path";
import { parseCSV } from "./csv.js";
import { normalizeTeamName, canonicalizeTeamNames, splitStateSuffix } from "./normalize.js";
import { parseFlexibleDate } from "./dates.js";
import type { Match, Player } from "./types.js";

function toNumber(value: string | undefined): number {
  if (value === undefined || value === "") return 0;
  return Number(value);
}

function toOptionalNumber(value: string | undefined): number | undefined {
  if (value === undefined || value === "") return undefined;
  const n = Number(value);
  return Number.isNaN(n) ? undefined : n;
}

function tryParseDate(value: string | undefined): Date | undefined {
  if (!value) return undefined;
  try {
    return parseFlexibleDate(value);
  } catch {
    return undefined;
  }
}

function isFiniteNumber(value: string | undefined): boolean {
  if (value === undefined || value === "") return false;
  return Number.isFinite(Number(value));
}

export function parseBrasileiraoMatches(csv: string): Match[] {
  const source = "Brasileirao_Matches.csv";
  return parseCSV(csv).flatMap((row, index) => {
    const date = tryParseDate(row.datetime);
    if (!date || !isFiniteNumber(row.home_goal) || !isFiniteNumber(row.away_goal)) return [];
    return [{
      id: `${source}-${index}`,
      source,
      competition: "Brasileirão",
      date,
      season: toNumber(row.season),
      round: row.round,
      homeTeam: normalizeTeamName(row.home_team),
      awayTeam: normalizeTeamName(row.away_team),
      homeTeamState: row.home_team_state,
      awayTeamState: row.away_team_state,
      homeGoals: toNumber(row.home_goal),
      awayGoals: toNumber(row.away_goal),
    }];
  });
}

export function parseCopaDoBrasilMatches(csv: string): Match[] {
  const source = "Brazilian_Cup_Matches.csv";
  return parseCSV(csv).flatMap((row, index) => {
    const date = tryParseDate(row.datetime);
    if (!date || !isFiniteNumber(row.home_goal) || !isFiniteNumber(row.away_goal)) return [];
    const home = splitStateSuffix(row.home_team);
    const away = splitStateSuffix(row.away_team);
    return [{
      id: `${source}-${index}`,
      source,
      competition: "Copa do Brasil",
      date,
      season: toNumber(row.season),
      round: row.round,
      homeTeam: normalizeTeamName(home.name),
      awayTeam: normalizeTeamName(away.name),
      homeTeamState: home.state,
      awayTeamState: away.state,
      homeGoals: toNumber(row.home_goal),
      awayGoals: toNumber(row.away_goal),
    }];
  });
}

export function parseLibertadoresMatches(csv: string): Match[] {
  const source = "Libertadores_Matches.csv";
  return parseCSV(csv).flatMap((row, index) => {
    const date = tryParseDate(row.datetime);
    if (!date || !isFiniteNumber(row.home_goal) || !isFiniteNumber(row.away_goal)) return [];
    return [{
      id: `${source}-${index}`,
      source,
      competition: "Copa Libertadores",
      date,
      season: toNumber(row.season),
      stage: row.stage,
      homeTeam: normalizeTeamName(row.home_team),
      awayTeam: normalizeTeamName(row.away_team),
      homeGoals: toNumber(row.home_goal),
      awayGoals: toNumber(row.away_goal),
    }];
  });
}

export function parseBRFootballDataset(csv: string): Match[] {
  const source = "BR-Football-Dataset.csv";
  return parseCSV(csv).flatMap((row, index) => {
    const date = tryParseDate(row.date);
    if (!date || !isFiniteNumber(row.home_goal) || !isFiniteNumber(row.away_goal)) return [];
    return [{
      id: `${source}-${index}`,
      source,
      competition: row.tournament,
      date,
      season: date.getUTCFullYear(),
      homeTeam: normalizeTeamName(row.home),
      awayTeam: normalizeTeamName(row.away),
      homeGoals: toNumber(row.home_goal),
      awayGoals: toNumber(row.away_goal),
      extra: {
        home_corner: toNumber(row.home_corner),
        away_corner: toNumber(row.away_corner),
        home_attack: toNumber(row.home_attack),
        away_attack: toNumber(row.away_attack),
        home_shots: toNumber(row.home_shots),
        away_shots: toNumber(row.away_shots),
        total_corners: toNumber(row.total_corners),
        ht_result: row.ht_result,
        at_result: row.at_result,
      },
    }];
  });
}

export function parseHistoricalBrasileirao(csv: string): Match[] {
  const source = "novo_campeonato_brasileiro.csv";
  return parseCSV(csv).flatMap((row, index) => {
    const date = tryParseDate(row.Data);
    if (!date || !isFiniteNumber(row.Gols_mandante) || !isFiniteNumber(row.Gols_visitante)) return [];
    return [{
      id: `${source}-${index}`,
      source,
      competition: "Brasileirão",
      date,
      season: toNumber(row.Ano),
      round: row.Rodada,
      homeTeam: normalizeTeamName(row.Equipe_mandante),
      awayTeam: normalizeTeamName(row.Equipe_visitante),
      homeTeamState: row.Mandante_UF,
      awayTeamState: row.Visitante_UF,
      homeGoals: toNumber(row.Gols_mandante),
      awayGoals: toNumber(row.Gols_visitante),
      venue: row.Arena || undefined,
    }];
  });
}

export function parseFifaPlayers(csv: string): Player[] {
  return parseCSV(csv).map((row) => ({
    id: row.ID,
    name: row.Name,
    age: toOptionalNumber(row.Age),
    nationality: row.Nationality,
    club: row.Club,
    overall: toOptionalNumber(row.Overall),
    potential: toOptionalNumber(row.Potential),
    position: row.Position || undefined,
    jerseyNumber: toOptionalNumber(row["Jersey Number"]),
    height: row.Height || undefined,
    weight: row.Weight || undefined,
  }));
}

export function loadAllData(dataDir: string): { matches: Match[]; players: Player[] } {
  const read = (filename: string) =>
    fs.readFileSync(path.join(dataDir, filename), "utf-8");

  const matches: Match[] = canonicalizeTeamNames([
    ...parseBrasileiraoMatches(read("Brasileirao_Matches.csv")),
    ...parseCopaDoBrasilMatches(read("Brazilian_Cup_Matches.csv")),
    ...parseLibertadoresMatches(read("Libertadores_Matches.csv")),
    ...parseBRFootballDataset(read("BR-Football-Dataset.csv")),
    ...parseHistoricalBrasileirao(read("novo_campeonato_brasileiro.csv")),
  ]);

  const players: Player[] = parseFifaPlayers(read("fifa_data.csv"));

  return { matches, players };
}
