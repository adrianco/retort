import { readFile } from 'node:fs/promises';
import { parse } from 'csv-parse/sync';
import { dirname, resolve as pathResolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  normalizeTeamName,
  parseDate,
  parseNumber,
  parseOptionalNumber,
  extractStateSuffix,
} from './normalize.js';
import { DataStore, Match, Player } from './types.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export function defaultDataDir(): string {
  // dist/loader.js -> project root/data/kaggle
  return pathResolve(__dirname, '..', 'data', 'kaggle');
}

async function readCsv(path: string): Promise<Record<string, string>[]> {
  const text = await readFile(path, 'utf8');
  return parse(text, {
    columns: true,
    skip_empty_lines: true,
    relax_quotes: true,
    relax_column_count: true,
    bom: true,
  }) as Record<string, string>[];
}

function makeMatch(args: {
  rawHome: string;
  rawAway: string;
  homeGoals: number;
  awayGoals: number;
  season: number;
  competition: Match['competition'];
  dateRaw: string;
  round?: string | number;
  stage?: string;
  arena?: string;
  homeState?: string;
  awayState?: string;
  homeCorner?: number;
  awayCorner?: number;
  homeShots?: number;
  awayShots?: number;
  homeAttack?: number;
  awayAttack?: number;
  htResult?: string;
  atResult?: string;
  totalCorners?: number;
}): Match {
  const { date, datetime } = parseDate(args.dateRaw);
  return {
    date,
    datetime,
    homeTeam: args.rawHome,
    homeTeamNorm: normalizeTeamName(args.rawHome),
    awayTeam: args.rawAway,
    awayTeamNorm: normalizeTeamName(args.rawAway),
    homeGoals: args.homeGoals,
    awayGoals: args.awayGoals,
    season: args.season,
    competition: args.competition,
    round: args.round,
    stage: args.stage,
    arena: args.arena,
    homeState: args.homeState,
    awayState: args.awayState,
    homeCorner: args.homeCorner,
    awayCorner: args.awayCorner,
    homeShots: args.homeShots,
    awayShots: args.awayShots,
    homeAttack: args.homeAttack,
    awayAttack: args.awayAttack,
    htResult: args.htResult,
    atResult: args.atResult,
    totalCorners: args.totalCorners,
  };
}

export async function loadBrasileirao(dataDir: string): Promise<Match[]> {
  const rows = await readCsv(`${dataDir}/Brasileirao_Matches.csv`);
  return rows.map((r) =>
    makeMatch({
      rawHome: r.home_team,
      rawAway: r.away_team,
      homeGoals: parseNumber(r.home_goal),
      awayGoals: parseNumber(r.away_goal),
      season: parseNumber(r.season),
      competition: 'Brasileirao',
      dateRaw: r.datetime,
      round: r.round,
      homeState: r.home_team_state || extractStateSuffix(r.home_team),
      awayState: r.away_team_state || extractStateSuffix(r.away_team),
    })
  );
}

export async function loadCopaDoBrasil(dataDir: string): Promise<Match[]> {
  const rows = await readCsv(`${dataDir}/Brazilian_Cup_Matches.csv`);
  return rows.map((r) =>
    makeMatch({
      rawHome: r.home_team,
      rawAway: r.away_team,
      homeGoals: parseNumber(r.home_goal),
      awayGoals: parseNumber(r.away_goal),
      season: parseNumber(r.season),
      competition: 'Copa do Brasil',
      dateRaw: r.datetime,
      round: r.round,
    })
  );
}

export async function loadLibertadores(dataDir: string): Promise<Match[]> {
  const rows = await readCsv(`${dataDir}/Libertadores_Matches.csv`);
  return rows.map((r) =>
    makeMatch({
      rawHome: r.home_team,
      rawAway: r.away_team,
      homeGoals: parseNumber(r.home_goal),
      awayGoals: parseNumber(r.away_goal),
      season: parseNumber(r.season),
      competition: 'Libertadores',
      dateRaw: r.datetime,
      stage: r.stage,
    })
  );
}

export async function loadBrFootball(dataDir: string): Promise<Match[]> {
  const rows = await readCsv(`${dataDir}/BR-Football-Dataset.csv`);
  return rows.map((r) => {
    const dateRaw = r.time ? `${r.date} ${r.time}` : r.date;
    const seasonMatch = r.date?.match(/^(\d{4})/);
    return makeMatch({
      rawHome: r.home,
      rawAway: r.away,
      homeGoals: parseNumber(r.home_goal),
      awayGoals: parseNumber(r.away_goal),
      season: seasonMatch ? Number(seasonMatch[1]) : 0,
      competition: 'BR-Football',
      dateRaw,
      stage: r.tournament,
      homeCorner: parseOptionalNumber(r.home_corner),
      awayCorner: parseOptionalNumber(r.away_corner),
      homeShots: parseOptionalNumber(r.home_shots),
      awayShots: parseOptionalNumber(r.away_shots),
      homeAttack: parseOptionalNumber(r.home_attack),
      awayAttack: parseOptionalNumber(r.away_attack),
      htResult: r.ht_result,
      atResult: r.at_result,
      totalCorners: parseOptionalNumber(r.total_corners),
    });
  });
}

export async function loadHistoricalBrasileirao(dataDir: string): Promise<Match[]> {
  const rows = await readCsv(`${dataDir}/novo_campeonato_brasileiro.csv`);
  return rows.map((r) =>
    makeMatch({
      rawHome: r.Equipe_mandante,
      rawAway: r.Equipe_visitante,
      homeGoals: parseNumber(r.Gols_mandante),
      awayGoals: parseNumber(r.Gols_visitante),
      season: parseNumber(r.Ano),
      competition: 'Historical',
      dateRaw: r.Data,
      round: r.Rodada,
      arena: r.Arena,
      homeState: r.Mandante_UF,
      awayState: r.Visitante_UF,
    })
  );
}

export async function loadPlayers(dataDir: string): Promise<Player[]> {
  const rows = await readCsv(`${dataDir}/fifa_data.csv`);
  return rows.map((r) => ({
    id: parseNumber(r.ID),
    name: r.Name,
    age: parseOptionalNumber(r.Age),
    nationality: r.Nationality,
    overall: parseOptionalNumber(r.Overall),
    potential: parseOptionalNumber(r.Potential),
    club: r.Club,
    clubNorm: normalizeTeamName(r.Club),
    position: r.Position,
    jerseyNumber: parseOptionalNumber(r['Jersey Number']),
    height: r.Height,
    weight: r.Weight,
    preferredFoot: r['Preferred Foot'],
    value: r.Value,
    wage: r.Wage,
  }));
}

export async function loadAll(dataDir = defaultDataDir()): Promise<DataStore> {
  const [bra, cup, lib, brf, hist, players] = await Promise.all([
    loadBrasileirao(dataDir),
    loadCopaDoBrasil(dataDir),
    loadLibertadores(dataDir),
    loadBrFootball(dataDir),
    loadHistoricalBrasileirao(dataDir),
    loadPlayers(dataDir),
  ]);
  return {
    matches: [...bra, ...cup, ...lib, ...brf, ...hist],
    players,
  };
}
