/**
 * Loads the six Kaggle CSV files into one in-memory model.
 *
 * Several files cover the same matches (e.g. Série A 2012-2019 appears in three
 * files). Each match keeps its `source`, and exactly one source per
 * competition/season is flagged `primary` so aggregate queries never double count.
 */
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseCsv } from './csv.js';
import { Competition, displayCandidate, parseDate, parseNum, teamKey } from './normalize.js';

export type Source = 'brasileirao' | 'copa_do_brasil' | 'libertadores' | 'br_football' | 'historical';

export const SOURCE_FILES: Record<Source | 'fifa', string> = {
  brasileirao: 'Brasileirao_Matches.csv',
  copa_do_brasil: 'Brazilian_Cup_Matches.csv',
  libertadores: 'Libertadores_Matches.csv',
  br_football: 'BR-Football-Dataset.csv',
  historical: 'novo_campeonato_brasileiro.csv',
  fifa: 'fifa_data.csv',
};

export interface ExtendedStats {
  homeCorners: number | null;
  awayCorners: number | null;
  homeAttacks: number | null;
  awayAttacks: number | null;
  homeShots: number | null;
  awayShots: number | null;
}

export interface Match {
  source: Source;
  competition: Competition;
  season: number | null;
  date: string | null;
  time: string | null;
  round: string | null;
  stage: string | null;
  homeKey: string;
  awayKey: string;
  homeRaw: string;
  awayRaw: string;
  homeGoals: number | null;
  awayGoals: number | null;
  homeState: string | null;
  awayState: string | null;
  arena: string | null;
  stats: ExtendedStats | null;
  /** True when this row is the preferred record of the match across overlapping files. */
  primary: boolean;
}

export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number;
  potential: number | null;
  club: string;
  clubKey: string;
  position: string;
  jersey: number | null;
  height: string;
  weight: string;
  preferredFoot: string;
  value: string;
  wage: string;
  attributes: Record<string, number>;
}

const ATTRIBUTES = [
  'Crossing', 'Finishing', 'HeadingAccuracy', 'ShortPassing', 'Volleys', 'Dribbling', 'Curve',
  'FKAccuracy', 'LongPassing', 'BallControl', 'Acceleration', 'SprintSpeed', 'Agility',
  'Reactions', 'Balance', 'ShotPower', 'Jumping', 'Stamina', 'Strength', 'LongShots',
  'Aggression', 'Interceptions', 'Positioning', 'Vision', 'Penalties', 'Composure', 'Marking',
  'StandingTackle', 'SlidingTackle', 'GKDiving', 'GKHandling', 'GKKicking', 'GKPositioning',
  'GKReflexes',
];

export interface Dataset {
  matches: Match[];
  players: Player[];
  /** team key -> display name */
  teamNames: Map<string, string>;
  /** rows loaded per file */
  counts: Record<string, number>;
}

export function defaultDataDir(): string {
  if (process.env.BRAZILIAN_SOCCER_DATA_DIR) return resolve(process.env.BRAZILIAN_SOCCER_DATA_DIR);
  return join(dirname(fileURLToPath(import.meta.url)), '..', 'data', 'kaggle');
}

export function loadDataset(dataDir: string = defaultDataDir()): Dataset {
  const read = (key: Source | 'fifa') => parseCsv(readFileSync(join(dataDir, SOURCE_FILES[key]), 'utf8'));
  const matches: Match[] = [];
  const counts: Record<string, number> = {};
  const best = new Map<string, { name: string; score: number }>();

  const team = (raw: string): string => {
    const key = teamKey(raw);
    const cand = displayCandidate(raw, key);
    const cur = best.get(key);
    if (!cur || cand.score > cur.score) best.set(key, cand);
    return key;
  };
  const base = (source: Source, competition: Competition, home: string, away: string) => ({
    source,
    competition,
    homeKey: team(home),
    awayKey: team(away),
    homeRaw: home,
    awayRaw: away,
    round: null as string | null,
    stage: null as string | null,
    homeState: null as string | null,
    awayState: null as string | null,
    arena: null as string | null,
    stats: null as ExtendedStats | null,
    primary: true,
  });
  const yearOf = (d: string | null) => (d ? Number(d.slice(0, 4)) : null);

  // 1. Brasileirão Série A 2012-2022
  let rows = read('brasileirao');
  counts[SOURCE_FILES.brasileirao] = rows.length;
  for (const r of rows) {
    const d = parseDate(r.datetime);
    matches.push({
      ...base('brasileirao', 'Brasileirão Série A', r.home_team, r.away_team),
      ...d,
      season: parseNum(r.season) ?? yearOf(d.date),
      round: r.round || null,
      homeGoals: parseNum(r.home_goal),
      awayGoals: parseNum(r.away_goal),
      homeState: r.home_team_state || null,
      awayState: r.away_team_state || null,
    });
  }

  // 2. Copa do Brasil
  rows = read('copa_do_brasil');
  counts[SOURCE_FILES.copa_do_brasil] = rows.length;
  for (const r of rows) {
    const d = parseDate(r.datetime);
    matches.push({
      ...base('copa_do_brasil', 'Copa do Brasil', r.home_team, r.away_team),
      ...d,
      season: parseNum(r.season) ?? yearOf(d.date),
      round: r.round || null,
      stage: r.round ? `Round ${r.round}` : null,
      homeGoals: parseNum(r.home_goal),
      awayGoals: parseNum(r.away_goal),
    });
  }

  // 3. Copa Libertadores
  rows = read('libertadores');
  counts[SOURCE_FILES.libertadores] = rows.length;
  let lastSeason: number | null = null;
  for (const r of rows) {
    const d = parseDate(r.datetime);
    const season: number | null = parseNum(r.season) ?? yearOf(d.date) ?? lastSeason;
    lastSeason = season;
    matches.push({
      ...base('libertadores', 'Copa Libertadores', r.home_team, r.away_team),
      ...d,
      season,
      stage: r.stage || null,
      homeGoals: parseNum(r.home_goal),
      awayGoals: parseNum(r.away_goal),
    });
  }

  // 4. Extended statistics (Série A/B/C + Copa do Brasil, 2014-2023)
  rows = read('br_football');
  counts[SOURCE_FILES.br_football] = rows.length;
  const tournaments: Record<string, Competition> = {
    'Serie A': 'Brasileirão Série A',
    'Serie B': 'Série B',
    'Serie C': 'Série C',
    'Copa do Brasil': 'Copa do Brasil',
  };
  for (const r of rows) {
    const d = parseDate(r.date);
    matches.push({
      ...base('br_football', tournaments[r.tournament] ?? 'Brasileirão Série A', r.home, r.away),
      date: d.date,
      time: r.time ? r.time.slice(0, 5) : null,
      season: yearOf(d.date),
      homeGoals: parseNum(r.home_goal),
      awayGoals: parseNum(r.away_goal),
      stats: {
        homeCorners: parseNum(r.home_corner),
        awayCorners: parseNum(r.away_corner),
        homeAttacks: parseNum(r.home_attack),
        awayAttacks: parseNum(r.away_attack),
        homeShots: parseNum(r.home_shots),
        awayShots: parseNum(r.away_shots),
      },
    });
  }

  // 5. Historical Brasileirão 2003-2019
  rows = read('historical');
  counts[SOURCE_FILES.historical] = rows.length;
  for (const r of rows) {
    const d = parseDate(r.Data);
    matches.push({
      ...base('historical', 'Brasileirão Série A', r.Equipe_mandante, r.Equipe_visitante),
      ...d,
      season: parseNum(r.Ano) ?? yearOf(d.date),
      round: r.Rodada || null,
      homeGoals: parseNum(r.Gols_mandante),
      awayGoals: parseNum(r.Gols_visitante),
      homeState: r.Mandante_UF || null,
      awayState: r.Visitante_UF || null,
      arena: r.Arena || null,
    });
  }

  markPrimary(matches);
  markCupFinals(matches);

  // 6. FIFA players
  rows = read('fifa');
  counts[SOURCE_FILES.fifa] = rows.length;
  const players: Player[] = rows.map((r) => {
    const attributes: Record<string, number> = {};
    for (const a of ATTRIBUTES) {
      const v = parseNum(r[a]);
      if (v !== null) attributes[a] = v;
    }
    return {
      id: Number(r.ID),
      name: r.Name,
      age: parseNum(r.Age),
      nationality: r.Nationality,
      overall: parseNum(r.Overall) ?? 0,
      potential: parseNum(r.Potential),
      club: r.Club,
      clubKey: r.Club ? teamKey(r.Club) : '',
      position: r.Position,
      jersey: parseNum(r['Jersey Number']),
      height: r.Height,
      weight: r.Weight,
      preferredFoot: r['Preferred Foot'],
      value: r.Value,
      wage: r.Wage,
      attributes,
    };
  });

  const teamNames = new Map<string, string>();
  for (const [k, v] of best) teamNames.set(k, v.name);
  return { matches, players, teamNames, counts };
}

/**
 * Resolve overlaps between files. Preference per competition:
 *  - Série A: Brasileirao_Matches for its seasons, the historical file before
 *    that, BR-Football only for years after the dedicated file ends.
 *  - Copa do Brasil: the dedicated cup file for its seasons, BR-Football after.
 */
function markPrimary(matches: Match[]): void {
  const range = (source: Source) => {
    const s = matches.filter((m) => m.source === source && m.season !== null).map((m) => m.season as number);
    return { min: Math.min(...s), max: Math.max(...s) };
  };
  const serieA = range('brasileirao');
  const cup = range('copa_do_brasil');
  for (const m of matches) {
    if (m.source === 'historical') {
      m.primary = m.season === null || m.season < serieA.min;
    } else if (m.source === 'br_football') {
      if (m.competition === 'Brasileirão Série A') m.primary = (m.season ?? 0) > serieA.max;
      else if (m.competition === 'Copa do Brasil') m.primary = (m.season ?? 0) > cup.max;
    }
  }
}

/** The cup file only numbers rounds; label the last round of a season "final" when it is a 1-2 leg tie. */
function markCupFinals(matches: Match[]): void {
  const bySeason = new Map<number, Match[]>();
  for (const m of matches) {
    if (m.source !== 'copa_do_brasil' || m.season === null) continue;
    if (!bySeason.has(m.season)) bySeason.set(m.season, []);
    bySeason.get(m.season)!.push(m);
  }
  for (const ms of bySeason.values()) {
    const max = Math.max(...ms.map((m) => Number(m.round) || 0));
    const last = ms.filter((m) => Number(m.round) === max);
    if (last.length <= 2) for (const m of last) m.stage = 'final';
  }
}
