import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'csv-parse/sync';
import type { Match, Player } from './types.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DATA_DIR_CANDIDATES = [
  join(__dirname, '..', 'data', 'kaggle'),
  join(__dirname, '..', '..', 'data', 'kaggle'),
];

function resolveDataDir(override?: string): string {
  if (override) return override;
  for (const c of DATA_DIR_CANDIDATES) {
    try {
      readFileSync(join(c, 'Brasileirao_Matches.csv'), 'utf8').slice(0, 1);
      return c;
    } catch {
      // try next
    }
  }
  return DATA_DIR_CANDIDATES[0];
}

function readCsv(path: string): Record<string, string>[] {
  let content = readFileSync(path, 'utf8');
  if (content.charCodeAt(0) === 0xfeff) {
    content = content.slice(1);
  }
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    relax_column_count: true,
    relax_quotes: true,
  }) as Record<string, string>[];
}

function num(v: string | undefined): number {
  if (v === undefined || v === null || v === '') return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function normalizeDate(s: string | undefined): string {
  if (!s) return '';
  const trimmed = s.trim();
  // DD/MM/YYYY
  const br = trimmed.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (br) return `${br[3]}-${br[2]}-${br[1]}`;
  // ISO with possible time
  const iso = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  return trimmed;
}

function yearFromDate(s: string): number {
  const m = s.match(/^(\d{4})/);
  return m ? Number(m[1]) : 0;
}

export interface DataStore {
  matches: Match[];
  players: Player[];
  dataDir: string;
}

let cached: DataStore | null = null;

export function loadAll(dataDir?: string): DataStore {
  if (cached && !dataDir) return cached;
  const dir = resolveDataDir(dataDir);
  const matches: Match[] = [];

  // 1. Brasileirao_Matches.csv
  try {
    const rows = readCsv(join(dir, 'Brasileirao_Matches.csv'));
    for (const r of rows) {
      const date = normalizeDate(r['datetime']);
      matches.push({
        competition: 'Brasileirao',
        season: num(r['season']) || yearFromDate(date),
        date,
        homeTeam: r['home_team'] ?? '',
        awayTeam: r['away_team'] ?? '',
        homeGoals: num(r['home_goal']),
        awayGoals: num(r['away_goal']),
        round: r['round'],
        homeState: r['home_team_state'],
        awayState: r['away_team_state'],
      });
    }
  } catch (e) {
    // skip missing file
  }

  // 2. Brazilian_Cup_Matches.csv
  try {
    const rows = readCsv(join(dir, 'Brazilian_Cup_Matches.csv'));
    for (const r of rows) {
      const date = normalizeDate(r['datetime']);
      matches.push({
        competition: 'Copa do Brasil',
        season: num(r['season']) || yearFromDate(date),
        date,
        homeTeam: r['home_team'] ?? '',
        awayTeam: r['away_team'] ?? '',
        homeGoals: num(r['home_goal']),
        awayGoals: num(r['away_goal']),
        round: r['round'],
      });
    }
  } catch {
    // skip
  }

  // 3. Libertadores_Matches.csv
  try {
    const rows = readCsv(join(dir, 'Libertadores_Matches.csv'));
    for (const r of rows) {
      const date = normalizeDate(r['datetime']);
      matches.push({
        competition: 'Libertadores',
        season: num(r['season']) || yearFromDate(date),
        date,
        homeTeam: r['home_team'] ?? '',
        awayTeam: r['away_team'] ?? '',
        homeGoals: num(r['home_goal']),
        awayGoals: num(r['away_goal']),
        stage: r['stage'],
      });
    }
  } catch {
    // skip
  }

  // 4. BR-Football-Dataset.csv
  try {
    const rows = readCsv(join(dir, 'BR-Football-Dataset.csv'));
    for (const r of rows) {
      const date = normalizeDate(r['date']);
      matches.push({
        competition: 'BR-Football',
        season: yearFromDate(date),
        date,
        homeTeam: r['home'] ?? '',
        awayTeam: r['away'] ?? '',
        homeGoals: num(r['home_goal']),
        awayGoals: num(r['away_goal']),
        homeCorners: num(r['home_corner']),
        awayCorners: num(r['away_corner']),
        homeShots: num(r['home_shots']),
        awayShots: num(r['away_shots']),
        homeAttacks: num(r['home_attack']),
        awayAttacks: num(r['away_attack']),
        totalCorners: num(r['total_corners']),
      });
    }
  } catch {
    // skip
  }

  // 5. novo_campeonato_brasileiro.csv
  try {
    const rows = readCsv(join(dir, 'novo_campeonato_brasileiro.csv'));
    for (const r of rows) {
      const date = normalizeDate(r['Data']);
      matches.push({
        competition: 'Historical Brasileirao',
        season: num(r['Ano']) || yearFromDate(date),
        date,
        homeTeam: r['Equipe_mandante'] ?? '',
        awayTeam: r['Equipe_visitante'] ?? '',
        homeGoals: num(r['Gols_mandante']),
        awayGoals: num(r['Gols_visitante']),
        round: r['Rodada'],
        homeState: r['Mandante_UF'],
        awayState: r['Visitante_UF'],
        arena: r['Arena'],
      });
    }
  } catch {
    // skip
  }

  const players: Player[] = [];
  try {
    const rows = readCsv(join(dir, 'fifa_data.csv'));
    for (const r of rows) {
      if (!r['Name']) continue;
      players.push({
        id: num(r['ID']),
        name: r['Name'],
        age: num(r['Age']),
        nationality: r['Nationality'] ?? '',
        overall: num(r['Overall']),
        potential: num(r['Potential']),
        club: r['Club'] ?? '',
        position: r['Position'] ?? '',
        jerseyNumber: num(r['Jersey Number']),
        height: r['Height'],
        weight: r['Weight'],
        preferredFoot: r['Preferred Foot'],
      });
    }
  } catch {
    // skip
  }

  const store: DataStore = { matches, players, dataDir: dir };
  if (!dataDir) cached = store;
  return store;
}

export function resetCache(): void {
  cached = null;
}
