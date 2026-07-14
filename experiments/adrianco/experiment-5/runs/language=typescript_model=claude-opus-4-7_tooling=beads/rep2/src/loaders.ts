import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { parse } from "csv-parse/sync";
import type { Match, Player } from "./types.js";
import { normalizeTeam } from "./normalize.js";
import { parseDate, parseGoal, parseSeason } from "./dates.js";

export interface LoadResult {
  matches: Match[];
  players: Player[];
}

function readCsv(path: string): Record<string, string>[] {
  const content = readFileSync(path, "utf8");
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true,
    bom: true,
  });
}

function loadBrasileirao(path: string): Match[] {
  const rows = readCsv(path);
  return rows.map((r) => ({
    source: "Brasileirao_Matches.csv",
    competition: "Brasileirão",
    date: parseDate(r.datetime),
    season: parseSeason(r.season),
    round: r.round ? String(r.round) : null,
    stage: null,
    homeTeam: r.home_team ?? "",
    homeTeamNormalized: normalizeTeam(r.home_team),
    homeState: r.home_team_state ?? null,
    awayTeam: r.away_team ?? "",
    awayTeamNormalized: normalizeTeam(r.away_team),
    awayState: r.away_team_state ?? null,
    homeGoal: parseGoal(r.home_goal),
    awayGoal: parseGoal(r.away_goal),
    arena: null,
  }));
}

function loadCopaBrasil(path: string): Match[] {
  const rows = readCsv(path);
  return rows.map((r) => ({
    source: "Brazilian_Cup_Matches.csv",
    competition: "Copa do Brasil",
    date: parseDate(r.datetime),
    season: parseSeason(r.season),
    round: r.round ? String(r.round) : null,
    stage: null,
    homeTeam: r.home_team ?? "",
    homeTeamNormalized: normalizeTeam(r.home_team),
    homeState: null,
    awayTeam: r.away_team ?? "",
    awayTeamNormalized: normalizeTeam(r.away_team),
    awayState: null,
    homeGoal: parseGoal(r.home_goal),
    awayGoal: parseGoal(r.away_goal),
    arena: null,
  }));
}

function loadLibertadores(path: string): Match[] {
  const rows = readCsv(path);
  return rows.map((r) => ({
    source: "Libertadores_Matches.csv",
    competition: "Copa Libertadores",
    date: parseDate(r.datetime),
    season: parseSeason(r.season),
    round: null,
    stage: r.stage ?? null,
    homeTeam: r.home_team ?? "",
    homeTeamNormalized: normalizeTeam(r.home_team),
    homeState: null,
    awayTeam: r.away_team ?? "",
    awayTeamNormalized: normalizeTeam(r.away_team),
    awayState: null,
    homeGoal: parseGoal(r.home_goal),
    awayGoal: parseGoal(r.away_goal),
    arena: null,
  }));
}

function loadBRFootball(path: string): Match[] {
  const rows = readCsv(path);
  return rows.map((r) => ({
    source: "BR-Football-Dataset.csv",
    competition: r.tournament ?? "Other",
    date: parseDate(r.date),
    season: r.date ? parseSeason(r.date.slice(0, 4)) : null,
    round: null,
    stage: null,
    homeTeam: r.home ?? "",
    homeTeamNormalized: normalizeTeam(r.home),
    homeState: null,
    awayTeam: r.away ?? "",
    awayTeamNormalized: normalizeTeam(r.away),
    awayState: null,
    homeGoal: parseGoal(r.home_goal),
    awayGoal: parseGoal(r.away_goal),
    arena: null,
    extras: {
      homeCorner: parseGoal(r.home_corner),
      awayCorner: parseGoal(r.away_corner),
      homeShots: parseGoal(r.home_shots),
      awayShots: parseGoal(r.away_shots),
      homeAttack: parseGoal(r.home_attack),
      awayAttack: parseGoal(r.away_attack),
      totalCorners: parseGoal(r.total_corners),
      htResult: r.ht_result ?? null,
      atResult: r.at_result ?? null,
      time: r.time ?? null,
    },
  }));
}

function loadHistoricalBrasileirao(path: string): Match[] {
  const rows = readCsv(path);
  return rows.map((r) => ({
    source: "novo_campeonato_brasileiro.csv",
    competition: "Brasileirão (historical)",
    date: parseDate(r.Data),
    season: parseSeason(r.Ano),
    round: r.Rodada ? String(r.Rodada) : null,
    stage: null,
    homeTeam: r.Equipe_mandante ?? "",
    homeTeamNormalized: normalizeTeam(r.Equipe_mandante),
    homeState: r.Mandante_UF ?? null,
    awayTeam: r.Equipe_visitante ?? "",
    awayTeamNormalized: normalizeTeam(r.Equipe_visitante),
    awayState: r.Visitante_UF ?? null,
    homeGoal: parseGoal(r.Gols_mandante),
    awayGoal: parseGoal(r.Gols_visitante),
    arena: r.Arena ?? null,
  }));
}

function parseInt0(s: string | undefined): number | null {
  if (s === undefined || s === null || s === "") return null;
  const n = parseInt(String(s), 10);
  return Number.isFinite(n) ? n : null;
}

function loadFifaPlayers(path: string): Player[] {
  const rows = readCsv(path);
  return rows
    .map((r) => {
      const id = parseInt0(r.ID);
      if (id === null) return null;
      const club = r.Club ?? "";
      return {
        id,
        name: r.Name ?? "",
        age: parseInt0(r.Age),
        nationality: r.Nationality ?? "",
        overall: parseInt0(r.Overall),
        potential: parseInt0(r.Potential),
        club,
        clubNormalized: normalizeTeam(club),
        position: r.Position || null,
        jerseyNumber: parseInt0(r["Jersey Number"]),
        height: r.Height || null,
        weight: r.Weight || null,
        preferredFoot: r["Preferred Foot"] || null,
      } satisfies Player;
    })
    .filter((p): p is Player => p !== null);
}

export function loadAll(dataDir: string): LoadResult {
  const files = {
    brasileirao: join(dataDir, "Brasileirao_Matches.csv"),
    copaBrasil: join(dataDir, "Brazilian_Cup_Matches.csv"),
    libertadores: join(dataDir, "Libertadores_Matches.csv"),
    brFootball: join(dataDir, "BR-Football-Dataset.csv"),
    historical: join(dataDir, "novo_campeonato_brasileiro.csv"),
    fifa: join(dataDir, "fifa_data.csv"),
  };

  const matches: Match[] = [];
  if (existsSync(files.brasileirao)) matches.push(...loadBrasileirao(files.brasileirao));
  if (existsSync(files.copaBrasil)) matches.push(...loadCopaBrasil(files.copaBrasil));
  if (existsSync(files.libertadores)) matches.push(...loadLibertadores(files.libertadores));
  if (existsSync(files.brFootball)) matches.push(...loadBRFootball(files.brFootball));
  if (existsSync(files.historical)) matches.push(...loadHistoricalBrasileirao(files.historical));

  const players = existsSync(files.fifa) ? loadFifaPlayers(files.fifa) : [];

  return { matches, players };
}

export function defaultDataDir(): string {
  return process.env.SOCCER_DATA_DIR || join(process.cwd(), "data", "kaggle");
}
