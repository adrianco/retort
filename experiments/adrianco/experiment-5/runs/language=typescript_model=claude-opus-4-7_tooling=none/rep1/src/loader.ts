import { readFileSync } from 'node:fs';
import { parse } from 'csv-parse/sync';
import { normalizeTeamName } from './normalize.js';
import type { Match, Player, DataStore } from './types.js';

interface LoaderOptions {
  dataDir?: string;
}

const DEFAULT_DATA_DIR = 'data/kaggle';

function parseCsv<T = Record<string, string>>(path: string): T[] {
  const raw = readFileSync(path);
  return parse(raw, {
    columns: true,
    bom: true,
    skip_empty_lines: true,
    relax_quotes: true,
    relax_column_count: true,
    trim: true,
  }) as T[];
}

function toInt(value: unknown): number {
  if (value === undefined || value === null || value === '') return 0;
  const n = Number(String(value).replace(/,/g, ''));
  if (Number.isNaN(n)) return 0;
  return Math.trunc(n);
}

function toOptionalInt(value: unknown): number | undefined {
  if (value === undefined || value === null || value === '') return undefined;
  const n = Number(String(value).replace(/,/g, ''));
  if (Number.isNaN(n)) return undefined;
  return Math.trunc(n);
}

function toIsoDate(value: string | undefined): string {
  if (!value) return '';
  const trimmed = value.trim();
  // Handle DD/MM/YYYY (Brazilian format)
  const br = trimmed.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (br) {
    return `${br[3]}-${br[2]}-${br[1]}`;
  }
  // Handle ISO with optional time
  const iso = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) {
    return `${iso[1]}-${iso[2]}-${iso[3]}`;
  }
  return trimmed;
}

function extractStateFromName(team: string): string | undefined {
  const dashMatch = team.match(/-\s*([A-Z]{2})$/);
  if (dashMatch) return dashMatch[1];
  return undefined;
}

function loadBrasileirao(path: string): Match[] {
  const rows = parseCsv<Record<string, string>>(path);
  return rows.map((row): Match => ({
    competition: 'Brasileirão Serie A',
    date: toIsoDate(row.datetime),
    season: toInt(row.season),
    round: row.round,
    homeTeam: normalizeTeamName(row.home_team),
    homeTeamRaw: row.home_team,
    homeState: row.home_team_state || extractStateFromName(row.home_team),
    awayTeam: normalizeTeamName(row.away_team),
    awayTeamRaw: row.away_team,
    awayState: row.away_team_state || extractStateFromName(row.away_team),
    homeGoals: toInt(row.home_goal),
    awayGoals: toInt(row.away_goal),
  }));
}

function loadCup(path: string): Match[] {
  const rows = parseCsv<Record<string, string>>(path);
  return rows.map((row): Match => ({
    competition: 'Copa do Brasil',
    date: toIsoDate(row.datetime),
    season: toInt(row.season),
    round: row.round,
    homeTeam: normalizeTeamName(row.home_team),
    homeTeamRaw: row.home_team,
    homeState: extractStateFromName(row.home_team),
    awayTeam: normalizeTeamName(row.away_team),
    awayTeamRaw: row.away_team,
    awayState: extractStateFromName(row.away_team),
    homeGoals: toInt(row.home_goal),
    awayGoals: toInt(row.away_goal),
  }));
}

function loadLibertadores(path: string): Match[] {
  const rows = parseCsv<Record<string, string>>(path);
  return rows.map((row): Match => ({
    competition: 'Copa Libertadores',
    date: toIsoDate(row.datetime),
    season: toInt(row.season),
    stage: row.stage,
    homeTeam: normalizeTeamName(row.home_team),
    homeTeamRaw: row.home_team,
    awayTeam: normalizeTeamName(row.away_team),
    awayTeamRaw: row.away_team,
    homeGoals: toInt(row.home_goal),
    awayGoals: toInt(row.away_goal),
  }));
}

function loadBrFootball(path: string): Match[] {
  const rows = parseCsv<Record<string, string>>(path);
  return rows.map((row): Match => {
    const date = toIsoDate(row.date);
    const season = date ? toInt(date.slice(0, 4)) : 0;
    return {
      competition: 'BR-Football Dataset',
      date,
      season,
      round: row.tournament,
      homeTeam: normalizeTeamName(row.home),
      homeTeamRaw: row.home,
      awayTeam: normalizeTeamName(row.away),
      awayTeamRaw: row.away,
      homeGoals: toInt(row.home_goal),
      awayGoals: toInt(row.away_goal),
      homeShots: toOptionalInt(row.home_shots),
      awayShots: toOptionalInt(row.away_shots),
      homeCorners: toOptionalInt(row.home_corner),
      awayCorners: toOptionalInt(row.away_corner),
      homeAttacks: toOptionalInt(row.home_attack),
      awayAttacks: toOptionalInt(row.away_attack),
      htResult: row.ht_result,
      atResult: row.at_result,
    };
  });
}

function loadNovoBrasileirao(path: string): Match[] {
  const rows = parseCsv<Record<string, string>>(path);
  return rows.map((row): Match => ({
    competition: 'Brasileirão (Historical 2003-2019)',
    date: toIsoDate(row.Data),
    season: toInt(row.Ano),
    round: row.Rodada,
    homeTeam: normalizeTeamName(row.Equipe_mandante),
    homeTeamRaw: row.Equipe_mandante,
    homeState: row.Mandante_UF,
    awayTeam: normalizeTeamName(row.Equipe_visitante),
    awayTeamRaw: row.Equipe_visitante,
    awayState: row.Visitante_UF,
    homeGoals: toInt(row.Gols_mandante),
    awayGoals: toInt(row.Gols_visitante),
    arena: row.Arena,
  }));
}

function loadFifaPlayers(path: string): Player[] {
  const rows = parseCsv<Record<string, string>>(path);
  return rows.map((row): Player => ({
    id: toInt(row.ID),
    name: row.Name || '',
    age: toOptionalInt(row.Age),
    nationality: row.Nationality,
    overall: toOptionalInt(row.Overall),
    potential: toOptionalInt(row.Potential),
    club: row.Club,
    position: row.Position,
    jerseyNumber: toOptionalInt(row['Jersey Number']),
    height: row.Height,
    weight: row.Weight,
    preferredFoot: row['Preferred Foot'],
    value: row.Value,
    wage: row.Wage,
  })).filter((p) => p.name);
}

export function loadData(options: LoaderOptions = {}): DataStore {
  const dir = options.dataDir ?? DEFAULT_DATA_DIR;
  const matches: Match[] = [
    ...loadBrasileirao(`${dir}/Brasileirao_Matches.csv`),
    ...loadCup(`${dir}/Brazilian_Cup_Matches.csv`),
    ...loadLibertadores(`${dir}/Libertadores_Matches.csv`),
    ...loadBrFootball(`${dir}/BR-Football-Dataset.csv`),
    ...loadNovoBrasileirao(`${dir}/novo_campeonato_brasileiro.csv`),
  ];
  const players = loadFifaPlayers(`${dir}/fifa_data.csv`);
  return { matches, players };
}
