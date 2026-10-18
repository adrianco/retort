/**
 * Context: reads the six provided Kaggle CSV files from data/kaggle, maps each
 * to the shared `Match` / `Player` shapes, and removes cross-file duplicates
 * (the Brasileirão files overlap for 2014–2019). Files are read once and the
 * result is cached per directory.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseCsvRecords } from './csv.js';
import {
  normalizeCompetition,
  normalizeTeam,
  parseDate,
  parseGoals,
  parseNumber,
  type CompetitionName,
} from './normalize.js';
import type { Dataset, Match, Player } from './types.js';
import type { TeamIdentity } from './normalize.js';

/** Default location of the provided datasets, relative to this module (src/ or dist/). */
export const DEFAULT_DATA_DIR = fileURLToPath(new URL('../data/kaggle', import.meta.url));

const SKILL_COLUMNS = [
  'Crossing', 'Finishing', 'HeadingAccuracy', 'ShortPassing', 'Volleys', 'Dribbling',
  'Curve', 'FKAccuracy', 'LongPassing', 'BallControl', 'Acceleration', 'SprintSpeed',
  'Agility', 'Reactions', 'Balance', 'ShotPower', 'Jumping', 'Stamina', 'Strength',
  'LongShots', 'Aggression', 'Interceptions', 'Positioning', 'Vision', 'Penalties',
  'Composure', 'Marking', 'StandingTackle', 'SlidingTackle', 'GKDiving', 'GKHandling',
  'GKKicking', 'GKPositioning', 'GKReflexes',
];

type Row = Record<string, string>;

/** Builds a Match from a row, or undefined when the date, teams or score are unusable. */
function buildMatch(
  source: string,
  index: number,
  fields: {
    competition: CompetitionName;
    date: string | undefined;
    season?: number;
    homeTeam: string;
    awayTeam: string;
    homeGoals: string | undefined;
    awayGoals: string | undefined;
    round?: string;
    stage?: string;
  },
): Match | undefined {
  const homeGoals = parseGoals(fields.homeGoals);
  const awayGoals = parseGoals(fields.awayGoals);
  const date = fields.date ? parseDate(fields.date) : undefined;
  if (!date || homeGoals === undefined || awayGoals === undefined) return undefined;
  if (!fields.homeTeam || !fields.awayTeam) return undefined;

  return {
    id: `${source}:${index}`,
    source,
    competition: fields.competition,
    season: fields.season ?? Number(date.slice(0, 4)),
    date,
    round: fields.round || undefined,
    stage: fields.stage || undefined,
    home: normalizeTeam(fields.homeTeam),
    away: normalizeTeam(fields.awayTeam),
    homeGoals,
    awayGoals,
  };
}

function mapRows(
  source: string,
  rows: Row[],
  toMatch: (row: Row, index: number) => Match | undefined,
): Match[] {
  const out: Match[] = [];
  rows.forEach((row, index) => {
    const match = toMatch(row, index + 1);
    if (match) out.push(match);
  });
  return out;
}

function matchesFromBrasileirao(rows: Row[], source: string): Match[] {
  return mapRows(source, rows, (r, i) =>
    buildMatch(source, i, {
      competition: 'Brasileirão Série A',
      date: r.datetime,
      season: parseNumber(r.season),
      homeTeam: r.home_team,
      awayTeam: r.away_team,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
      round: r.round,
    }),
  );
}

function matchesFromNovo(rows: Row[], source: string): Match[] {
  return mapRows(source, rows, (r, i) =>
    buildMatch(source, i, {
      competition: 'Brasileirão Série A',
      date: r.Data,
      season: parseNumber(r.Ano),
      homeTeam: r.Equipe_mandante,
      awayTeam: r.Equipe_visitante,
      homeGoals: r.Gols_mandante,
      awayGoals: r.Gols_visitante,
      round: r.Rodada,
    }),
  );
}

function matchesFromCup(rows: Row[], source: string): Match[] {
  return mapRows(source, rows, (r, i) =>
    buildMatch(source, i, {
      competition: 'Copa do Brasil',
      date: r.datetime,
      season: parseNumber(r.season),
      homeTeam: r.home_team,
      awayTeam: r.away_team,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
      round: r.round,
    }),
  );
}

function matchesFromLibertadores(rows: Row[], source: string): Match[] {
  return mapRows(source, rows, (r, i) =>
    buildMatch(source, i, {
      competition: 'Copa Libertadores',
      date: r.datetime,
      season: parseNumber(r.season),
      homeTeam: r.home_team,
      awayTeam: r.away_team,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
      stage: r.stage,
    }),
  );
}

function matchesFromBrFootball(rows: Row[], source: string): Match[] {
  return mapRows(source, rows, (r, i) => {
    const competition = normalizeCompetition(r.tournament);
    if (!competition) return undefined;
    return buildMatch(source, i, {
      competition,
      date: r.date,
      homeTeam: r.home,
      awayTeam: r.away,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
    });
  });
}

function playerFromRow(row: Row): Player | undefined {
  const id = parseNumber(row.ID);
  const club = row.Club ?? '';
  if (id === undefined || !row.Name) return undefined;

  const attributes: Record<string, number> = {};
  for (const column of SKILL_COLUMNS) {
    const value = parseNumber(row[column]);
    if (value !== undefined) attributes[column] = value;
  }

  return {
    id,
    name: row.Name,
    age: parseNumber(row.Age),
    nationality: row.Nationality,
    overall: parseNumber(row.Overall),
    potential: parseNumber(row.Potential),
    club,
    clubKey: normalizeTeam(club).key,
    position: row.Position || undefined,
    jerseyNumber: parseNumber(row['Jersey Number']),
    height: row.Height || undefined,
    weight: row.Weight || undefined,
    preferredFoot: row['Preferred Foot'] || undefined,
    value: row.Value || undefined,
    wage: row.Wage || undefined,
    attributes,
  };
}

function dayDifference(a: string, b: string): number {
  return Math.abs(Date.parse(a) - Date.parse(b)) / 86_400_000;
}

/**
 * Removes fixtures that appear in more than one source. Sources disagree on
 * dates by up to a day (time zones), so a match is a duplicate when the same
 * two teams met within one day with the same score. The first occurrence in
 * load order is kept.
 */
export function dedupeMatches(matches: Match[]): Match[] {
  const kept: Match[] = [];
  const byPair = new Map<string, Match[]>();
  for (const m of matches) {
    const pair = [m.home.key, m.away.key].sort().join('|');
    const bucket = byPair.get(pair) ?? [];
    const duplicate = bucket.some(
      (k) =>
        k.home.key === m.home.key &&
        k.homeGoals === m.homeGoals &&
        k.awayGoals === m.awayGoals &&
        dayDifference(k.date, m.date) <= 1,
    );
    if (duplicate) continue;
    kept.push(m);
    bucket.push(m);
    byPair.set(pair, bucket);
  }
  return kept;
}

/** Loads all datasets from `dataDir`. Missing files raise an error naming the file. */
export function loadDataset(dataDir: string = DEFAULT_DATA_DIR): Dataset {
  const sources: Dataset['sources'] = [];
  const readRows = (file: string): Row[] => parseCsvRecords(readFileSync(join(dataDir, file), 'utf8'));

  const specs: Array<[string, (rows: Row[], source: string) => Match[]]> = [
    ['Brasileirao_Matches.csv', matchesFromBrasileirao],
    ['novo_campeonato_brasileiro.csv', matchesFromNovo],
    ['Brazilian_Cup_Matches.csv', matchesFromCup],
    ['Libertadores_Matches.csv', matchesFromLibertadores],
    ['BR-Football-Dataset.csv', matchesFromBrFootball],
  ];

  const allMatches: Match[] = [];
  for (const [file, convert] of specs) {
    const rows = readRows(file);
    const matches = convert(rows, file);
    sources.push({ file, rows: rows.length, loaded: matches.length });
    allMatches.push(...matches);
  }

  const playerRows = readRows('fifa_data.csv');
  const players = playerRows.map(playerFromRow).filter((p): p is Player => p !== undefined);
  sources.push({ file: 'fifa_data.csv', rows: playerRows.length, loaded: players.length });

  const priority = specs.map(([file]) => file);
  const matches = inferTeamStates(dedupeMatches(prioritizeSources(allMatches, priority))).sort((a, b) =>
    a.date.localeCompare(b.date),
  );
  return { matches, players, sources };
}

/**
 * Keeps, for each competition and season, only the rows from the highest-
 * priority source that covers it. Files are listed in priority order (earlier
 * wins). This avoids mixing a partial source with a complete one, which would
 * otherwise produce extra or missing games in standings.
 */
export function prioritizeSources(matches: Match[], sourcePriority: string[]): Match[] {
  const rank = (source: string) => {
    const idx = sourcePriority.indexOf(source);
    return idx === -1 ? sourcePriority.length : idx;
  };
  const best = new Map<string, number>();
  for (const m of matches) {
    const key = `${m.competition}|${m.season}`;
    const r = rank(m.source);
    best.set(key, Math.min(best.get(key) ?? Infinity, r));
  }
  return matches.filter((m) => rank(m.source) === best.get(`${m.competition}|${m.season}`));
}

/**
 * Sources label states inconsistently ("Palmeiras-SP" in one file, "Palmeiras"
 * in another). When a bare name is only ever seen with one state in the whole
 * dataset, the state is filled in so the same club groups together. Names seen
 * with several states (e.g. "Atletico") are left bare.
 */
export function inferTeamStates(matches: Match[]): Match[] {
  const statesByKey = new Map<string, Set<string>>();
  for (const m of matches) {
    for (const team of [m.home, m.away]) {
      if (!team.state) continue;
      const set = statesByKey.get(team.key) ?? new Set<string>();
      set.add(team.state);
      statesByKey.set(team.key, set);
    }
  }
  const resolve = (team: TeamIdentity): TeamIdentity => {
    if (team.state) return team;
    const states = statesByKey.get(team.key);
    if (!states || states.size !== 1) return team;
    const [state] = states;
    return { ...team, state, qualified: `${team.key}-${state.toLowerCase()}` };
  };
  return matches.map((m) => ({ ...m, home: resolve(m.home), away: resolve(m.away) }));
}

let cache: { dir: string; dataset: Dataset } | undefined;

/** Returns the cached dataset for `dataDir`, loading it on first use. */
export function getDataset(dataDir: string = DEFAULT_DATA_DIR): Dataset {
  if (!cache || cache.dir !== dataDir) {
    cache = { dir: dataDir, dataset: loadDataset(dataDir) };
  }
  return cache.dataset;
}
