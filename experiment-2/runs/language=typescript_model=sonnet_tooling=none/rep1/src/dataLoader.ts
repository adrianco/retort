import { parse } from 'csv-parse/sync';
import * as fs from 'fs';
import * as path from 'path';
import {
  BrasileiraoMatch,
  CupMatch,
  LibertadoresMatch,
  BRFootballMatch,
  HistoricalMatch,
  FifaPlayer,
  NormalizedMatch,
} from './types';

const DATA_DIR = path.join(__dirname, '..', 'data', 'kaggle');

function readCsv(filename: string): any[] {
  const filePath = path.join(DATA_DIR, filename);
  const content = fs.readFileSync(filePath, 'utf-8');
  // Remove BOM if present
  const cleaned = content.replace(/^\uFEFF/, '');
  return parse(cleaned, {
    columns: true,
    skip_empty_lines: true,
    relax_quotes: true,
    relax_column_count: true,
    trim: true,
  });
}

function parseGoals(value: any): number {
  const n = parseInt(value, 10);
  return isNaN(n) ? 0 : n;
}

/**
 * Normalize date strings to ISO YYYY-MM-DD format.
 * Handles:
 *   - "2012-05-19 18:30:00"
 *   - "2012-05-19"
 *   - "29/03/2003"
 */
export function normalizeDate(raw: string): string {
  if (!raw) return '';
  raw = raw.trim();
  // DD/MM/YYYY
  const brMatch = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (brMatch) {
    return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;
  }
  // YYYY-MM-DD (with optional time)
  const isoMatch = raw.match(/^(\d{4}-\d{2}-\d{2})/);
  if (isoMatch) {
    return isoMatch[1];
  }
  return raw;
}

/**
 * Normalize team name: strip state suffix, trim, lowercase for comparison.
 * Returns the canonical display name (original casing, no suffix).
 */
export function normalizeTeamName(name: string): string {
  if (!name) return '';
  // Remove state suffix like "-SP", "-RJ", etc.
  return name.replace(/-[A-Z]{2}$/, '').trim();
}

export function teamMatches(teamName: string, candidate: string): boolean {
  const norm = (s: string) => normalizeTeamName(s).toLowerCase();
  const t = norm(teamName);
  const c = norm(candidate);
  return c.includes(t) || t.includes(c);
}

// ─── Loaders ────────────────────────────────────────────────────────────────

let _brasileirao: NormalizedMatch[] | null = null;
let _cup: NormalizedMatch[] | null = null;
let _libertadores: NormalizedMatch[] | null = null;
let _brFootball: BRFootballMatch[] | null = null;
let _historical: NormalizedMatch[] | null = null;
let _fifa: FifaPlayer[] | null = null;

export function loadBrasileiraoMatches(): NormalizedMatch[] {
  if (_brasileirao) return _brasileirao;
  const rows = readCsv('Brasileirao_Matches.csv');
  _brasileirao = rows.map((r: any): NormalizedMatch => ({
    date: normalizeDate(r.datetime),
    home_team: normalizeTeamName(r.home_team),
    away_team: normalizeTeamName(r.away_team),
    home_goal: parseGoals(r.home_goal),
    away_goal: parseGoals(r.away_goal),
    season: parseInt(r.season, 10),
    competition: 'Brasileirao',
    round: r.round,
  }));
  return _brasileirao;
}

export function loadCupMatches(): NormalizedMatch[] {
  if (_cup) return _cup;
  const rows = readCsv('Brazilian_Cup_Matches.csv');
  _cup = rows.map((r: any): NormalizedMatch => ({
    date: normalizeDate(r.datetime),
    home_team: normalizeTeamName(r.home_team),
    away_team: normalizeTeamName(r.away_team),
    home_goal: parseGoals(r.home_goal),
    away_goal: parseGoals(r.away_goal),
    season: parseInt(r.season, 10),
    competition: 'Copa do Brasil',
    round: r.round,
  }));
  return _cup;
}

export function loadLibertadoresMatches(): NormalizedMatch[] {
  if (_libertadores) return _libertadores;
  const rows = readCsv('Libertadores_Matches.csv');
  _libertadores = rows.map((r: any): NormalizedMatch => ({
    date: normalizeDate(r.datetime),
    home_team: normalizeTeamName(r.home_team),
    away_team: normalizeTeamName(r.away_team),
    home_goal: parseGoals(r.home_goal),
    away_goal: parseGoals(r.away_goal),
    season: parseInt(r.season, 10),
    competition: 'Libertadores',
    stage: r.stage,
  }));
  return _libertadores;
}

export function loadBRFootballMatches(): BRFootballMatch[] {
  if (_brFootball) return _brFootball;
  const rows = readCsv('BR-Football-Dataset.csv');
  _brFootball = rows.map((r: any): BRFootballMatch => ({
    tournament: r.tournament || '',
    home: normalizeTeamName(r.home || ''),
    away: normalizeTeamName(r.away || ''),
    home_goal: parseGoals(r.home_goal),
    away_goal: parseGoals(r.away_goal),
    home_corner: parseGoals(r.home_corner),
    away_corner: parseGoals(r.away_corner),
    home_attack: parseGoals(r.home_attack),
    away_attack: parseGoals(r.away_attack),
    home_shots: parseGoals(r.home_shots),
    away_shots: parseGoals(r.away_shots),
    time: r.time || '',
    date: normalizeDate(r.date),
    ht_result: r.ht_result || '',
    at_result: r.at_result || '',
    total_corners: parseGoals(r.total_corners),
  }));
  return _brFootball;
}

export function loadHistoricalMatches(): NormalizedMatch[] {
  if (_historical) return _historical;
  const rows = readCsv('novo_campeonato_brasileiro.csv');
  _historical = rows.map((r: any): NormalizedMatch => ({
    date: normalizeDate(r.Data),
    home_team: normalizeTeamName(r.Equipe_mandante || ''),
    away_team: normalizeTeamName(r.Equipe_visitante || ''),
    home_goal: parseGoals(r.Gols_mandante),
    away_goal: parseGoals(r.Gols_visitante),
    season: parseInt(r.Ano, 10),
    competition: 'Brasileirao (Historical)',
    round: r.Rodada,
    arena: r.Arena,
  }));
  return _historical;
}

export function loadFifaPlayers(): FifaPlayer[] {
  if (_fifa) return _fifa;
  const rows = readCsv('fifa_data.csv');
  _fifa = rows.map((r: any): FifaPlayer => ({
    ID: parseInt(r.ID, 10),
    Name: r.Name || '',
    Age: parseInt(r.Age, 10),
    Nationality: r.Nationality || '',
    Overall: parseInt(r.Overall, 10),
    Potential: parseInt(r.Potential, 10),
    Club: r.Club || '',
    Position: r.Position || '',
    JerseyNumber: parseInt(r['Jersey Number'], 10),
    Height: r.Height || '',
    Weight: r.Weight || '',
    Value: r.Value || '',
    Wage: r.Wage || '',
  }));
  return _fifa;
}

export function getAllMatches(): NormalizedMatch[] {
  return [
    ...loadBrasileiraoMatches(),
    ...loadCupMatches(),
    ...loadLibertadoresMatches(),
    ...loadHistoricalMatches(),
  ];
}

/** Clear cache (useful for tests) */
export function clearCache(): void {
  _brasileirao = null;
  _cup = null;
  _libertadores = null;
  _brFootball = null;
  _historical = null;
  _fifa = null;
}
