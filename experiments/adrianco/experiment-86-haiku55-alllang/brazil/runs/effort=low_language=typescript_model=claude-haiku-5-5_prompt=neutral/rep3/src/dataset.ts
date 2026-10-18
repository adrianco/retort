/*
 * Context: Loads and normalizes all six Kaggle CSV files into one in-memory Dataset.
 * - Two passes: first buffer every raw match row, then decide team keys. A base name that
 *   appears with several state suffixes (Botafogo-RJ / -SP / -PB) is split into one key per
 *   state so unrelated clubs are never merged.
 * - Brasileirão files overlap (2012–2019 appear in several sources), so matches are
 *   de-duplicated on (season, competition, home, away, score); sources disagree on dates
 *   by a day at times, so the date is not part of identity.
 * - BR-Football-Dataset's "tournament" column is mapped to canonical competition names.
 * - Rows with missing scores (unplayed fixtures) are skipped.
 * The result is cached per data directory; loading is the only expensive step.
 * Related: csv.ts, dates.ts, normalize.ts, types.ts.
 */
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import { readCsv, toLeadingInt, toNumber } from './csv.js';
import { parseDate } from './dates.js';
import { displayFor, stateOf, teamKey } from './normalize.js';
import type { Dataset, Match, Player } from './types.js';

export const COMPETITION = {
  SERIE_A: 'Brasileirão Série A',
  SERIE_B: 'Brasileirão Série B',
  SERIE_C: 'Brasileirão Série C',
  COPA_DO_BRASIL: 'Copa do Brasil',
  LIBERTADORES: 'Copa Libertadores',
} as const;

const BR_FOOTBALL_TOURNAMENTS: Record<string, string> = {
  'Serie A': COMPETITION.SERIE_A,
  'Serie B': COMPETITION.SERIE_B,
  'Serie C': COMPETITION.SERIE_C,
  'Copa do Brasil': COMPETITION.COPA_DO_BRASIL,
};

const SKILL_COLUMNS = [
  'Crossing', 'Finishing', 'HeadingAccuracy', 'ShortPassing', 'Volleys', 'Dribbling', 'Curve',
  'FKAccuracy', 'LongPassing', 'BallControl', 'Acceleration', 'SprintSpeed', 'Agility', 'Reactions',
  'Balance', 'ShotPower', 'Jumping', 'Stamina', 'Strength', 'LongShots', 'Aggression',
  'Interceptions', 'Positioning', 'Vision', 'Penalties', 'Composure', 'Marking', 'StandingTackle',
  'SlidingTackle', 'GKDiving', 'GKHandling', 'GKKicking', 'GKPositioning', 'GKReflexes',
];

/** Resolves to <project>/data/kaggle from both src/ (tests) and dist/ (runtime). */
export const DEFAULT_DATA_DIR = join(fileURLToPath(new URL('..', import.meta.url)), 'data', 'kaggle');

const cache = new Map<string, Promise<Dataset>>();

/** Load (once per directory) the complete dataset. */
export function loadDataset(dataDir: string = process.env.DATA_DIR ?? DEFAULT_DATA_DIR): Promise<Dataset> {
  let pending = cache.get(dataDir);
  if (!pending) {
    pending = Promise.resolve().then(() => buildDataset(dataDir));
    cache.set(dataDir, pending);
  }
  return pending;
}

/** Test helper: drop cached datasets. */
export function clearDatasetCache(): void {
  cache.clear();
}

interface RawMatch {
  date: string;
  season: number | null;
  competition: string;
  round: string | null;
  homeRaw: string;
  awayRaw: string;
  homeGoals: number;
  awayGoals: number;
  source: string;
}

export function buildDataset(dataDir: string): Dataset {
  const loadedFiles: string[] = [];
  const raw: (RawMatch | null)[] = [];

  const existing = (name: string) => {
    const path = join(dataDir, name);
    if (!existsSync(path)) throw new Error(`Required dataset file missing: ${path}`);
    loadedFiles.push(name);
    return path;
  };

  // 1. Brasileirão 2012+ (Brasileirao_Matches.csv)
  for (const r of readCsv(existing('Brasileirao_Matches.csv'))) {
    raw.push(row({
      date: parseDate(r.datetime), season: toNumber(r.season), competition: COMPETITION.SERIE_A,
      round: r.round, homeRaw: r.home_team, awayRaw: r.away_team,
      homeGoals: toNumber(r.home_goal), awayGoals: toNumber(r.away_goal), source: 'Brasileirao_Matches.csv',
    }));
  }

  // 2. Brasileirão 2003–2019 (novo_campeonato_brasileiro.csv), Portuguese column names
  for (const r of readCsv(existing('novo_campeonato_brasileiro.csv'))) {
    raw.push(row({
      date: parseDate(r.Data), season: toNumber(r.Ano), competition: COMPETITION.SERIE_A,
      round: r.Rodada, homeRaw: r.Equipe_mandante, awayRaw: r.Equipe_visitante,
      homeGoals: toNumber(r.Gols_mandante), awayGoals: toNumber(r.Gols_visitante),
      source: 'novo_campeonato_brasileiro.csv',
    }));
  }

  // 3. Copa do Brasil
  for (const r of readCsv(existing('Brazilian_Cup_Matches.csv'))) {
    raw.push(row({
      date: parseDate(r.datetime), season: toNumber(r.season), competition: COMPETITION.COPA_DO_BRASIL,
      round: r.round, homeRaw: r.home_team, awayRaw: r.away_team,
      homeGoals: toNumber(r.home_goal), awayGoals: toNumber(r.away_goal), source: 'Brazilian_Cup_Matches.csv',
    }));
  }

  // 4. Copa Libertadores
  for (const r of readCsv(existing('Libertadores_Matches.csv'))) {
    raw.push(row({
      date: parseDate(r.datetime), season: toNumber(r.season), competition: COMPETITION.LIBERTADORES,
      round: r.stage, homeRaw: r.home_team, awayRaw: r.away_team,
      homeGoals: toNumber(r.home_goal), awayGoals: toNumber(r.away_goal), source: 'Libertadores_Matches.csv',
    }));
  }

  // 5. Extended statistics (BR-Football-Dataset.csv) — tournament names mapped to canonical ones
  for (const r of readCsv(existing('BR-Football-Dataset.csv'))) {
    const competition = BR_FOOTBALL_TOURNAMENTS[r.tournament];
    if (!competition) continue;
    const date = parseDate(r.date);
    raw.push(row({
      date, season: date ? Number(date.slice(0, 4)) : null, competition, round: null,
      homeRaw: r.home, awayRaw: r.away, homeGoals: toNumber(r.home_goal), awayGoals: toNumber(r.away_goal),
      source: 'BR-Football-Dataset.csv',
    }));
  }

  // Historical 2003–2019 matches come from (2); FIFA player data is loaded below.
  const teams = new Map<string, string>();
  const matches = buildMatches(raw, teams);
  const players = loadPlayers(existing('fifa_data.csv'));
  return { matches, players, teams, loadedFiles };
}

/** Turn a parsed CSV row into a RawMatch, or null when it lacks a date or scores. */
function row(r: {
  date: string | null; season: number | null; competition: string; round: string | undefined | null;
  homeRaw: string; awayRaw: string; homeGoals: number | null; awayGoals: number | null; source: string;
}): RawMatch | null {
  if (!r.date || r.homeGoals === null || r.awayGoals === null) return null;
  return {
    date: r.date,
    season: r.season,
    competition: r.competition,
    round: r.round || null,
    homeRaw: r.homeRaw,
    awayRaw: r.awayRaw,
    homeGoals: r.homeGoals,
    awayGoals: r.awayGoals,
    source: r.source,
  };
}

function buildMatches(rows: (RawMatch | null)[], teams: Map<string, string>): Match[] {
  const valid = rows.filter((r): r is RawMatch => r !== null);

  // Pass 1: which base keys are shared by clubs from different states? The most frequent
  // state keeps the plain key; minority states get a state-qualified key ("botafogo sp").
  const counts = new Map<string, Map<string, number>>();
  for (const r of valid) {
    for (const name of [r.homeRaw, r.awayRaw]) {
      const state = stateOf(name);
      if (!state) continue;
      const key = teamKey(name);
      const byState = counts.get(key) ?? new Map<string, number>();
      byState.set(state, (byState.get(state) ?? 0) + 1);
      counts.set(key, byState);
    }
  }
  const ambiguous = new Set<string>();
  const dominant = new Map<string, string>();
  for (const [key, byState] of counts) {
    if (byState.size < 2) continue;
    ambiguous.add(key);
    dominant.set(key, [...byState].sort((a, b) => b[1] - a[1])[0][0]);
  }
  const isQualified = (name: string) => {
    const key = teamKey(name);
    const state = stateOf(name);
    return ambiguous.has(key) && state !== null && state !== dominant.get(key);
  };

  // Pass 2: keys, display names, de-duplication.
  const keyOf = (name: string) => {
    const key = teamKey(name);
    return isQualified(name) ? `${key} ${stateOf(name)!.toLowerCase()}` : key;
  };
  const seen = new Set<string>();
  const matches: Match[] = [];
  for (const r of valid) {
    const homeKey = keyOf(r.homeRaw);
    const awayKey = keyOf(r.awayRaw);
    const identity = [r.season, r.competition, homeKey, awayKey, r.homeGoals, r.awayGoals].join('|');
    if (seen.has(identity)) continue;
    seen.add(identity);
    const home = displayFor(r.homeRaw, homeKey, isQualified(r.homeRaw));
    const away = displayFor(r.awayRaw, awayKey, isQualified(r.awayRaw));
    teams.set(homeKey, home);
    teams.set(awayKey, away);
    matches.push({
      id: '',
      date: r.date,
      season: r.season,
      competition: r.competition,
      round: r.round,
      home,
      away,
      homeKey,
      awayKey,
      homeGoals: r.homeGoals,
      awayGoals: r.awayGoals,
      source: r.source,
    });
  }
  matches.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
  matches.forEach((m, i) => (m.id = `${i + 1}`));
  return matches;
}

function loadPlayers(path: string): Player[] {
  return readCsv(path).map((r, i): Player => {
    const attributes: Record<string, number> = {};
    for (const col of SKILL_COLUMNS) {
      const v = toLeadingInt(r[col]);
      if (v !== null) attributes[col] = v;
    }
    const club = r.Club ?? '';
    return {
      id: r.ID || `${i}`,
      name: r.Name ?? '',
      age: toNumber(r.Age),
      nationality: r.Nationality ?? '',
      overall: toLeadingInt(r.Overall),
      potential: toLeadingInt(r.Potential),
      club,
      clubKey: club ? teamKey(club) : '',
      position: r.Position ?? '',
      jerseyNumber: toNumber(r['Jersey Number']),
      preferredFoot: r['Preferred Foot'] ?? '',
      heightCm: parseHeightCm(r.Height),
      weightKg: parseWeightKg(r.Weight),
      value: r.Value ?? '',
      wage: r.Wage ?? '',
      attributes,
    };
  });
}

/** FIFA heights look like 5'7 → centimetres. */
export function parseHeightCm(raw: string | undefined): number | null {
  const m = /^(\d+)'(\d+)/.exec(raw ?? '');
  if (!m) return null;
  return Math.round((Number(m[1]) * 12 + Number(m[2])) * 2.54);
}

/** FIFA weights look like 159lbs → kilograms. */
export function parseWeightKg(raw: string | undefined): number | null {
  const m = /^(\d+)\s*lbs/i.exec(raw ?? '');
  if (!m) return null;
  return Math.round(Number(m[1]) * 0.453592);
}
