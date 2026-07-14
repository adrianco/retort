import { readFile } from 'node:fs/promises';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'csv-parse/sync';
import {
  Match,
  Player,
  DataStore,
  Competition,
} from './types.js';
import { normalizeTeam, parseDate } from './normalize.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/** Default location of the kaggle data, relative to the project root. */
export function defaultDataDir(): string {
  // src/dataLoader.ts -> repo root -> data/kaggle
  // dist/dataLoader.js -> repo root -> data/kaggle
  return resolve(__dirname, '..', 'data', 'kaggle');
}

function num(value: unknown): number | undefined {
  if (value === undefined || value === null || value === '') return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function numRequired(value: unknown): number {
  const n = num(value);
  return n ?? 0;
}

async function readCsv(path: string): Promise<Record<string, string>[]> {
  const raw = await readFile(path, 'utf8');
  // The fifa_data.csv begins with a BOM; csv-parse handles BOM with `bom: true`.
  return parse(raw, {
    columns: true,
    bom: true,
    skip_empty_lines: true,
    relax_column_count: true,
    relax_quotes: true,
    trim: true,
  }) as Record<string, string>[];
}

function buildMatch(
  source: string,
  competition: Competition,
  raw: {
    dateRaw: string;
    homeTeam: string;
    awayTeam: string;
    homeGoals: unknown;
    awayGoals: unknown;
    season?: unknown;
    round?: unknown;
    stage?: string;
    arena?: string;
    homeState?: string;
    awayState?: string;
    homeCorners?: unknown;
    awayCorners?: unknown;
    homeShots?: unknown;
    awayShots?: unknown;
    htResult?: string;
    atResult?: string;
    tournamentRaw?: string;
  },
): Match {
  const { date, time } = parseDate(raw.dateRaw);
  return {
    source,
    competition,
    tournamentRaw: raw.tournamentRaw,
    date,
    time,
    homeTeam: raw.homeTeam,
    awayTeam: raw.awayTeam,
    homeKey: normalizeTeam(raw.homeTeam),
    awayKey: normalizeTeam(raw.awayTeam),
    homeGoals: numRequired(raw.homeGoals),
    awayGoals: numRequired(raw.awayGoals),
    season: num(raw.season),
    round: raw.round != null && raw.round !== '' ? String(raw.round) : undefined,
    stage: raw.stage || undefined,
    arena: raw.arena || undefined,
    homeState: raw.homeState || undefined,
    awayState: raw.awayState || undefined,
    homeCorners: num(raw.homeCorners),
    awayCorners: num(raw.awayCorners),
    homeShots: num(raw.homeShots),
    awayShots: num(raw.awayShots),
    htResult: raw.htResult || undefined,
    atResult: raw.atResult || undefined,
  };
}

function competitionFromTournament(t: string | undefined): Competition {
  if (!t) return 'Other';
  const s = t.toLowerCase().trim();
  if (s.includes('brasileir')) return 'Brasileirão';
  if (s.includes('copa do brasil')) return 'Copa do Brasil';
  if (s.includes('libertadores')) return 'Libertadores';
  // "Serie A" in the BR-Football dataset is the Brazilian top tier (Brasileirão).
  if (s === 'serie a' || s === 'série a') return 'Brasileirão';
  return 'Other';
}

async function loadBrasileiraoMatches(path: string): Promise<Match[]> {
  const rows = await readCsv(path);
  return rows.map((r) =>
    buildMatch('Brasileirao_Matches.csv', 'Brasileirão', {
      dateRaw: r.datetime,
      homeTeam: r.home_team,
      awayTeam: r.away_team,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
      season: r.season,
      round: r.round,
      homeState: r.home_team_state,
      awayState: r.away_team_state,
    }),
  );
}

async function loadCupMatches(path: string): Promise<Match[]> {
  const rows = await readCsv(path);
  return rows.map((r) =>
    buildMatch('Brazilian_Cup_Matches.csv', 'Copa do Brasil', {
      dateRaw: r.datetime,
      homeTeam: r.home_team,
      awayTeam: r.away_team,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
      season: r.season,
      round: r.round,
    }),
  );
}

async function loadLibertadoresMatches(path: string): Promise<Match[]> {
  const rows = await readCsv(path);
  return rows.map((r) =>
    buildMatch('Libertadores_Matches.csv', 'Libertadores', {
      dateRaw: r.datetime,
      homeTeam: r.home_team,
      awayTeam: r.away_team,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
      season: r.season,
      stage: r.stage,
    }),
  );
}

async function loadExtendedMatches(path: string): Promise<Match[]> {
  const rows = await readCsv(path);
  return rows.map((r) =>
    buildMatch(
      'BR-Football-Dataset.csv',
      competitionFromTournament(r.tournament),
      {
        dateRaw: r.date,
        homeTeam: r.home,
        awayTeam: r.away,
        homeGoals: r.home_goal,
        awayGoals: r.away_goal,
        homeCorners: r.home_corner,
        awayCorners: r.away_corner,
        homeShots: r.home_shots,
        awayShots: r.away_shots,
        htResult: r.ht_result,
        atResult: r.at_result,
        tournamentRaw: r.tournament,
      },
    ),
  );
}

async function loadHistoricalBrasileirao(path: string): Promise<Match[]> {
  const rows = await readCsv(path);
  return rows.map((r) =>
    buildMatch('novo_campeonato_brasileiro.csv', 'Brasileirão', {
      dateRaw: r.Data,
      homeTeam: r.Equipe_mandante,
      awayTeam: r.Equipe_visitante,
      homeGoals: r.Gols_mandante,
      awayGoals: r.Gols_visitante,
      season: r.Ano,
      round: r.Rodada,
      arena: r.Arena,
      homeState: r.Mandante_UF,
      awayState: r.Visitante_UF,
    }),
  );
}

async function loadPlayers(path: string): Promise<Player[]> {
  const rows = await readCsv(path);
  const players: Player[] = [];
  for (const r of rows) {
    const id = Number(r.ID);
    if (!Number.isFinite(id)) continue;
    const club = (r.Club ?? '').trim();
    players.push({
      id,
      name: r.Name?.trim() ?? '',
      age: num(r.Age),
      nationality: r.Nationality?.trim() || undefined,
      overall: num(r.Overall),
      potential: num(r.Potential),
      club: club || undefined,
      clubKey: club ? normalizeTeam(club) : undefined,
      position: r.Position?.trim() || undefined,
      jerseyNumber: num(r['Jersey Number']),
      height: r.Height?.trim() || undefined,
      weight: r.Weight?.trim() || undefined,
      preferredFoot: r['Preferred Foot']?.trim() || undefined,
      workRate: r['Work Rate']?.trim() || undefined,
      value: r.Value?.trim() || undefined,
      wage: r.Wage?.trim() || undefined,
    });
  }
  return players;
}

export interface LoadOptions {
  dataDir?: string;
}

/**
 * Load every CSV file in the dataset. Cached on a per-directory basis so
 * subsequent calls (and tests) avoid the disk + parse round-trip.
 */
const cache = new Map<string, Promise<DataStore>>();

export function loadAll(opts: LoadOptions = {}): Promise<DataStore> {
  const dir = opts.dataDir ?? defaultDataDir();
  let entry = cache.get(dir);
  if (!entry) {
    entry = loadAllUncached(dir);
    cache.set(dir, entry);
  }
  return entry;
}

async function loadAllUncached(dir: string): Promise<DataStore> {
  const [m1, m2, m3, m4, m5, players] = await Promise.all([
    loadBrasileiraoMatches(join(dir, 'Brasileirao_Matches.csv')),
    loadCupMatches(join(dir, 'Brazilian_Cup_Matches.csv')),
    loadLibertadoresMatches(join(dir, 'Libertadores_Matches.csv')),
    loadExtendedMatches(join(dir, 'BR-Football-Dataset.csv')),
    loadHistoricalBrasileirao(join(dir, 'novo_campeonato_brasileiro.csv')),
    loadPlayers(join(dir, 'fifa_data.csv')),
  ]);
  const matches = [...m1, ...m2, ...m3, ...m4, ...m5];
  return { matches, players };
}

/** Clear the in-memory cache. Mostly useful for tests. */
export function clearCache(): void {
  cache.clear();
}
