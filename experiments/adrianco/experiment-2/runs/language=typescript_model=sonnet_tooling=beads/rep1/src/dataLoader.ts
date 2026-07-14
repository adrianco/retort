import { parse } from 'csv-parse/sync';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { Match, Player, DataStore } from './types.js';
import { normalizeTeamName } from './normalize.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, '..', 'data', 'kaggle');

function parseDate(raw: string): string {
  if (!raw) return '';
  const s = raw.trim();
  // ISO with time: "2012-05-19 18:30:00"
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
    return s.split(' ')[0];
  }
  // Brazilian format: "29/03/2003"
  if (/^\d{2}\/\d{2}\/\d{4}/.test(s)) {
    const [day, month, year] = s.split('/');
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  }
  return s;
}

function toInt(val: unknown): number {
  const n = parseInt(String(val), 10);
  return isNaN(n) ? 0 : n;
}

function toFloat(val: unknown): number {
  const n = parseFloat(String(val));
  return isNaN(n) ? 0 : n;
}

function readCsv(filename: string): Record<string, string>[] {
  const filePath = join(DATA_DIR, filename);
  const content = readFileSync(filePath, 'utf-8').replace(/^\uFEFF/, ''); // strip BOM
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_quotes: true,
    relax_column_count: true,
  }) as Record<string, string>[];
}

function loadBrasileirao(): Match[] {
  const rows = readCsv('Brasileirao_Matches.csv');
  return rows.map((r) => ({
    date: parseDate(r['datetime']),
    homeTeam: normalizeTeamName(r['home_team']),
    awayTeam: normalizeTeamName(r['away_team']),
    homeGoals: toInt(r['home_goal']),
    awayGoals: toInt(r['away_goal']),
    competition: 'Brasileirão Série A',
    season: toInt(r['season']),
    round: r['round'],
  }));
}

function loadCopaDoBrasil(): Match[] {
  const rows = readCsv('Brazilian_Cup_Matches.csv');
  return rows.map((r) => ({
    date: parseDate(r['datetime']),
    homeTeam: normalizeTeamName(r['home_team']),
    awayTeam: normalizeTeamName(r['away_team']),
    homeGoals: toInt(r['home_goal']),
    awayGoals: toInt(r['away_goal']),
    competition: 'Copa do Brasil',
    season: toInt(r['season']),
    round: r['round'],
  }));
}

function loadLibertadores(): Match[] {
  const rows = readCsv('Libertadores_Matches.csv');
  return rows.map((r) => ({
    date: parseDate(r['datetime']),
    homeTeam: normalizeTeamName(r['home_team']),
    awayTeam: normalizeTeamName(r['away_team']),
    homeGoals: toInt(r['home_goal']),
    awayGoals: toInt(r['away_goal']),
    competition: 'Copa Libertadores',
    season: toInt(r['season']),
    stage: r['stage'],
  }));
}

function loadBrFootball(): Match[] {
  const rows = readCsv('BR-Football-Dataset.csv');
  return rows.map((r) => ({
    date: parseDate(r['date']),
    homeTeam: normalizeTeamName(r['home']),
    awayTeam: normalizeTeamName(r['away']),
    homeGoals: toFloat(r['home_goal']),
    awayGoals: toFloat(r['away_goal']),
    competition: r['tournament'] || 'Unknown',
    season: r['date'] ? parseInt(r['date'].substring(0, 4), 10) : 0,
    homeCorners: toFloat(r['home_corner']),
    awayCorners: toFloat(r['away_corner']),
    homeAttacks: toFloat(r['home_attack']),
    awayAttacks: toFloat(r['away_attack']),
    homeShots: toFloat(r['home_shots']),
    awayShots: toFloat(r['away_shots']),
  }));
}

function loadHistoricalBrasileirao(): Match[] {
  const rows = readCsv('novo_campeonato_brasileiro.csv');
  return rows.map((r) => ({
    date: parseDate(r['Data']),
    homeTeam: normalizeTeamName(r['Equipe_mandante']),
    awayTeam: normalizeTeamName(r['Equipe_visitante']),
    homeGoals: toInt(r['Gols_mandante']),
    awayGoals: toInt(r['Gols_visitante']),
    competition: 'Brasileirão Série A',
    season: toInt(r['Ano']),
    round: r['Rodada'],
    arena: r['Arena'],
  }));
}

function loadFifaPlayers(): Player[] {
  const rows = readCsv('fifa_data.csv');
  return rows.map((r) => ({
    id: r['ID'],
    name: r['Name'],
    age: toInt(r['Age']),
    nationality: r['Nationality'],
    overall: toInt(r['Overall']),
    potential: toInt(r['Potential']),
    club: r['Club'] || '',
    position: r['Position'] || '',
    jerseyNumber: r['Jersey Number'] ? toInt(r['Jersey Number']) : undefined,
    height: r['Height'],
    weight: r['Weight'],
    value: r['Value'],
    wage: r['Wage'],
  }));
}

export function loadAllData(): DataStore {
  const matches: Match[] = [
    ...loadBrasileirao(),
    ...loadCopaDoBrasil(),
    ...loadLibertadores(),
    ...loadBrFootball(),
    ...loadHistoricalBrasileirao(),
  ];
  const players = loadFifaPlayers();
  return { matches, players };
}
