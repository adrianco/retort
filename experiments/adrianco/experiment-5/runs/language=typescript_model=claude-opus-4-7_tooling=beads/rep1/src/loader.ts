import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'csv-parse/sync';
import type { Match, Player, Competition } from './types.js';
import {
  normalizeTeamName,
  parseDate,
  parseNumber,
  parseOptionalNumber,
  parseSeason,
} from './normalize.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

function defaultDataDir(): string {
  if (process.env.SOCCER_DATA_DIR) return process.env.SOCCER_DATA_DIR;
  return resolve(__dirname, '..', 'data', 'kaggle');
}

function readCsv(path: string): Record<string, string>[] {
  const raw = readFileSync(path, 'utf8');
  return parse(raw, {
    columns: true,
    skip_empty_lines: true,
    relax_quotes: true,
    relax_column_count: true,
    trim: true,
    bom: true,
  }) as Record<string, string>[];
}

function detectTournament(name: string): Competition {
  const n = name.toLowerCase();
  if (n.includes('libertadores')) return 'Copa Libertadores';
  if (n.includes('copa do brasil') || n.includes('brazilian cup')) return 'Copa do Brasil';
  if (n.includes('brasileir') || n.includes('serie a') || n.includes('série a')) return 'Brasileirão';
  return 'Other';
}

function buildBrasileirao(rows: Record<string, string>[]): Match[] {
  return rows.map((r): Match => {
    const date = parseDate(r.datetime);
    const season = parseSeason(r.season, date);
    return {
      competition: 'Brasileirão',
      source: 'Brasileirao_Matches.csv',
      date,
      season,
      round: r.round,
      homeTeamRaw: r.home_team,
      awayTeamRaw: r.away_team,
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeTeamState: r.home_team_state || undefined,
      awayTeamState: r.away_team_state || undefined,
      homeGoals: parseNumber(r.home_goal),
      awayGoals: parseNumber(r.away_goal),
    };
  });
}

function buildCopaBrasil(rows: Record<string, string>[]): Match[] {
  return rows.map((r): Match => {
    const date = parseDate(r.datetime);
    const season = parseSeason(r.season, date);
    return {
      competition: 'Copa do Brasil',
      source: 'Brazilian_Cup_Matches.csv',
      date,
      season,
      round: r.round,
      homeTeamRaw: r.home_team,
      awayTeamRaw: r.away_team,
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeGoals: parseNumber(r.home_goal),
      awayGoals: parseNumber(r.away_goal),
    };
  });
}

function buildLibertadores(rows: Record<string, string>[]): Match[] {
  return rows.map((r): Match => {
    const date = parseDate(r.datetime);
    const season = parseSeason(r.season, date);
    return {
      competition: 'Copa Libertadores',
      source: 'Libertadores_Matches.csv',
      date,
      season,
      stage: r.stage,
      homeTeamRaw: r.home_team,
      awayTeamRaw: r.away_team,
      homeTeam: normalizeTeamName(r.home_team),
      awayTeam: normalizeTeamName(r.away_team),
      homeGoals: parseNumber(r.home_goal),
      awayGoals: parseNumber(r.away_goal),
    };
  });
}

function buildExtended(rows: Record<string, string>[]): Match[] {
  return rows.map((r): Match => {
    const date = parseDate(r.date);
    const competition = detectTournament(r.tournament || '');
    const season = parseSeason(undefined, date);
    return {
      competition,
      source: 'BR-Football-Dataset.csv',
      date,
      season,
      homeTeamRaw: r.home,
      awayTeamRaw: r.away,
      homeTeam: normalizeTeamName(r.home),
      awayTeam: normalizeTeamName(r.away),
      homeGoals: parseNumber(r.home_goal),
      awayGoals: parseNumber(r.away_goal),
      stats: {
        homeCorners: parseOptionalNumber(r.home_corner),
        awayCorners: parseOptionalNumber(r.away_corner),
        totalCorners: parseOptionalNumber(r.total_corners),
        homeShots: parseOptionalNumber(r.home_shots),
        awayShots: parseOptionalNumber(r.away_shots),
        homeAttacks: parseOptionalNumber(r.home_attack),
        awayAttacks: parseOptionalNumber(r.away_attack),
        htHomeResult: r.ht_result || undefined,
        atAwayResult: r.at_result || undefined,
      },
    };
  });
}

function buildHistorical(rows: Record<string, string>[]): Match[] {
  return rows.map((r): Match => {
    const date = parseDate(r.Data);
    const season = parseSeason(r.Ano, date);
    return {
      competition: 'Brasileirão',
      source: 'novo_campeonato_brasileiro.csv',
      date,
      season,
      round: r.Rodada,
      homeTeamRaw: r.Equipe_mandante,
      awayTeamRaw: r.Equipe_visitante,
      homeTeam: normalizeTeamName(r.Equipe_mandante),
      awayTeam: normalizeTeamName(r.Equipe_visitante),
      homeTeamState: r.Mandante_UF || undefined,
      awayTeamState: r.Visitante_UF || undefined,
      homeGoals: parseNumber(r.Gols_mandante),
      awayGoals: parseNumber(r.Gols_visitante),
      arena: r.Arena || undefined,
    };
  });
}

function buildPlayers(rows: Record<string, string>[]): Player[] {
  return rows.map((r): Player => ({
    id: Number(r.ID),
    name: r.Name,
    age: parseOptionalNumber(r.Age),
    nationality: r.Nationality || undefined,
    overall: parseOptionalNumber(r.Overall),
    potential: parseOptionalNumber(r.Potential),
    club: r.Club || undefined,
    clubNormalized: r.Club ? normalizeTeamName(r.Club) : undefined,
    position: r.Position || undefined,
    jerseyNumber: parseOptionalNumber(r['Jersey Number']),
    height: r.Height || undefined,
    weight: r.Weight || undefined,
    preferredFoot: r['Preferred Foot'] || undefined,
    value: r.Value || undefined,
    wage: r.Wage || undefined,
    workRate: r['Work Rate'] || undefined,
    bodyType: r['Body Type'] || undefined,
  })).filter(p => p.name);
}

function shiftDate(date: string, days: number): string {
  if (!/^\d{4}-\d{2}-\d{2}/.test(date)) return date;
  const [y, m, d] = date.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + days);
  const yy = dt.getUTCFullYear();
  const mm = String(dt.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(dt.getUTCDate()).padStart(2, '0');
  return `${yy}-${mm}-${dd}`;
}

function score(x: Match): number {
  return (x.stats ? 5 : 0) + (x.arena ? 1 : 0) + (x.round !== undefined && x.round !== '' ? 1 : 0) + (x.stage ? 1 : 0);
}

function dedupeMatches(matches: Match[]): Match[] {
  const map = new Map<string, Match>();
  // Try exact date first, then ±1 day fuzz against existing entries.
  for (const m of matches) {
    if (!m.date || !m.homeTeam || !m.awayTeam) continue;
    const baseKey = `${m.competition}|${m.homeTeam}|${m.awayTeam}|${m.homeGoals}-${m.awayGoals}`;
    const candidates = [
      `${baseKey}|${m.date}`,
      `${baseKey}|${shiftDate(m.date, -1)}`,
      `${baseKey}|${shiftDate(m.date, 1)}`,
    ];
    let existingKey: string | undefined;
    for (const key of candidates) {
      if (map.has(key)) { existingKey = key; break; }
    }
    if (!existingKey) {
      map.set(candidates[0], m);
      continue;
    }
    const existing = map.get(existingKey)!;
    if (score(m) > score(existing)) {
      // Keep existing key (don't move) but enrich with new fields.
      map.set(existingKey, {
        ...existing,
        round: existing.round ?? m.round,
        stage: existing.stage ?? m.stage,
        arena: existing.arena ?? m.arena,
        stats: existing.stats ?? m.stats,
        homeTeamState: existing.homeTeamState ?? m.homeTeamState,
        awayTeamState: existing.awayTeamState ?? m.awayTeamState,
      });
    } else {
      // Existing wins — but fill in missing fields from candidate
      map.set(existingKey, {
        ...existing,
        round: existing.round ?? m.round,
        stage: existing.stage ?? m.stage,
        arena: existing.arena ?? m.arena,
        stats: existing.stats ?? m.stats,
        homeTeamState: existing.homeTeamState ?? m.homeTeamState,
        awayTeamState: existing.awayTeamState ?? m.awayTeamState,
      });
    }
  }
  return Array.from(map.values());
}

export interface SoccerData {
  matches: Match[];
  players: Player[];
  dataDir: string;
}

export function loadData(dataDir?: string): SoccerData {
  const dir = dataDir || defaultDataDir();
  const matches: Match[] = [];
  matches.push(...buildBrasileirao(readCsv(resolve(dir, 'Brasileirao_Matches.csv'))));
  matches.push(...buildCopaBrasil(readCsv(resolve(dir, 'Brazilian_Cup_Matches.csv'))));
  matches.push(...buildLibertadores(readCsv(resolve(dir, 'Libertadores_Matches.csv'))));
  matches.push(...buildExtended(readCsv(resolve(dir, 'BR-Football-Dataset.csv'))));
  matches.push(...buildHistorical(readCsv(resolve(dir, 'novo_campeonato_brasileiro.csv'))));
  const players = buildPlayers(readCsv(resolve(dir, 'fifa_data.csv')));
  return { matches: dedupeMatches(matches), players, dataDir: dir };
}

let cached: SoccerData | undefined;
export function getData(dataDir?: string): SoccerData {
  if (!cached || (dataDir && dataDir !== cached.dataDir)) {
    cached = loadData(dataDir);
  }
  return cached;
}
