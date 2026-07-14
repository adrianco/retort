import { parse } from 'csv-parse/sync';
import * as fs from 'fs';
import * as path from 'path';

export interface BrasileiraoMatch {
  datetime: string;
  home_team: string;
  home_team_state: string;
  away_team: string;
  away_team_state: string;
  home_goal: number;
  away_goal: number;
  season: number;
  round: number;
  source: 'brasileirao';
}

export interface CupMatch {
  round: string;
  datetime: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  source: 'copa_brasil';
}

export interface LibertadoresMatch {
  datetime: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  stage: string;
  source: 'libertadores';
}

export interface ExtendedMatch {
  tournament: string;
  home: string;
  away: string;
  home_goal: number;
  away_goal: number;
  home_corner: number;
  away_corner: number;
  home_attack: number;
  away_attack: number;
  home_shots: number;
  away_shots: number;
  time: string;
  date: string;
  ht_result: string;
  at_result: string;
  total_corners: number;
  source: 'extended';
}

export interface HistoricalMatch {
  id: string;
  date: string;
  year: number;
  round: number;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  home_state: string;
  away_state: string;
  winner: string;
  arena: string;
  source: 'historical';
}

export interface FifaPlayer {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jersey_number: string;
  height: string;
  weight: string;
  value: string;
  wage: string;
  preferred_foot: string;
  crossing: number;
  finishing: number;
  dribbling: number;
  sprint_speed: number;
  stamina: number;
}

export type AnyMatch = BrasileiraoMatch | CupMatch | LibertadoresMatch | ExtendedMatch | HistoricalMatch;

export interface DataStore {
  brasileirao: BrasileiraoMatch[];
  copa: CupMatch[];
  libertadores: LibertadoresMatch[];
  extended: ExtendedMatch[];
  historical: HistoricalMatch[];
  players: FifaPlayer[];
}

const DATA_DIR = path.join(__dirname, '..', 'data', 'kaggle');

function parseNum(val: string | undefined): number {
  if (!val || val.trim() === '') return 0;
  const n = parseFloat(val.trim());
  return isNaN(n) ? 0 : n;
}

function parseIntSafe(val: string | undefined): number {
  if (!val || val.trim() === '') return 0;
  const n = parseInt(val.trim(), 10);
  return isNaN(n) ? 0 : n;
}

export function normalizeTeamName(name: string): string {
  if (!name) return '';
  // Remove state suffixes like "-SP", "-RJ", "- RJ", " - SP"
  let normalized = name.trim();
  normalized = normalized.replace(/\s*-\s*[A-Z]{2}$/, '');
  // Remove parenthetical notes like "(antigo ...)"
  normalized = normalized.replace(/\s*\([^)]+\)\s*/g, '').trim();
  // Remove trailing " - RJ" style with spaces
  normalized = normalized.replace(/\s+-\s+[A-Z]{2}$/, '');
  return normalized.trim();
}

function loadCSV(filename: string): Record<string, string>[] {
  const filePath = path.join(DATA_DIR, filename);
  const content = fs.readFileSync(filePath, 'utf-8');
  // Remove BOM if present
  const cleaned = content.replace(/^﻿/, '');
  return parse(cleaned, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_quotes: true,
  });
}

export function loadBrasileiraoMatches(): BrasileiraoMatch[] {
  const rows = loadCSV('Brasileirao_Matches.csv');
  return rows.map(r => ({
    datetime: r['datetime'] || '',
    home_team: normalizeTeamName(r['home_team'] || ''),
    home_team_state: r['home_team_state'] || '',
    away_team: normalizeTeamName(r['away_team'] || ''),
    away_team_state: r['away_team_state'] || '',
    home_goal: parseNum(r['home_goal']),
    away_goal: parseNum(r['away_goal']),
    season: parseIntSafe(r['season']),
    round: parseIntSafe(r['round']),
    source: 'brasileirao' as const,
  }));
}

export function loadCupMatches(): CupMatch[] {
  const rows = loadCSV('Brazilian_Cup_Matches.csv');
  return rows.map(r => ({
    round: r['round'] || '',
    datetime: r['datetime'] || '',
    home_team: normalizeTeamName(r['home_team'] || ''),
    away_team: normalizeTeamName(r['away_team'] || ''),
    home_goal: parseNum(r['home_goal']),
    away_goal: parseNum(r['away_goal']),
    season: parseIntSafe(r['season']),
    source: 'copa_brasil' as const,
  }));
}

export function loadLibertadoresMatches(): LibertadoresMatch[] {
  const rows = loadCSV('Libertadores_Matches.csv');
  return rows.map(r => ({
    datetime: r['datetime'] || '',
    home_team: normalizeTeamName(r['home_team'] || ''),
    away_team: normalizeTeamName(r['away_team'] || ''),
    home_goal: parseNum(r['home_goal']),
    away_goal: parseNum(r['away_goal']),
    season: parseIntSafe(r['season']),
    stage: r['stage'] || '',
    source: 'libertadores' as const,
  }));
}

export function loadExtendedMatches(): ExtendedMatch[] {
  const rows = loadCSV('BR-Football-Dataset.csv');
  return rows.map(r => ({
    tournament: r['tournament'] || '',
    home: normalizeTeamName(r['home'] || ''),
    away: normalizeTeamName(r['away'] || ''),
    home_goal: parseNum(r['home_goal']),
    away_goal: parseNum(r['away_goal']),
    home_corner: parseNum(r['home_corner']),
    away_corner: parseNum(r['away_corner']),
    home_attack: parseNum(r['home_attack']),
    away_attack: parseNum(r['away_attack']),
    home_shots: parseNum(r['home_shots']),
    away_shots: parseNum(r['away_shots']),
    time: r['time'] || '',
    date: r['date'] || '',
    ht_result: r['ht_result'] || '',
    at_result: r['at_result'] || '',
    total_corners: parseNum(r['total_corners']),
    source: 'extended' as const,
  }));
}

export function loadHistoricalMatches(): HistoricalMatch[] {
  const rows = loadCSV('novo_campeonato_brasileiro.csv');
  return rows.map(r => ({
    id: r['ID'] || '',
    date: r['Data'] || '',
    year: parseIntSafe(r['Ano']),
    round: parseIntSafe(r['Rodada']),
    home_team: normalizeTeamName(r['Equipe_mandante'] || ''),
    away_team: normalizeTeamName(r['Equipe_visitante'] || ''),
    home_goal: parseNum(r['Gols_mandante']),
    away_goal: parseNum(r['Gols_visitante']),
    home_state: r['Mandante_UF'] || '',
    away_state: r['Visitante_UF'] || '',
    winner: r['Vencedor'] || '',
    arena: r['Arena'] || '',
    source: 'historical' as const,
  }));
}

function parseSkillRating(val: string | undefined): number {
  if (!val || val.trim() === '') return 0;
  // Ratings may be like "88+2" — take base value
  const base = val.split('+')[0].split('-')[0];
  const n = parseInt(base.trim(), 10);
  return isNaN(n) ? 0 : n;
}

export function loadFifaPlayers(): FifaPlayer[] {
  const rows = loadCSV('fifa_data.csv');
  return rows.map(r => ({
    id: parseIntSafe(r['ID']),
    name: r['Name'] || '',
    age: parseIntSafe(r['Age']),
    nationality: r['Nationality'] || '',
    overall: parseIntSafe(r['Overall']),
    potential: parseIntSafe(r['Potential']),
    club: r['Club'] || '',
    position: r['Position'] || '',
    jersey_number: r['Jersey Number'] || '',
    height: r['Height'] || '',
    weight: r['Weight'] || '',
    value: r['Value'] || '',
    wage: r['Wage'] || '',
    preferred_foot: r['Preferred Foot'] || '',
    crossing: parseSkillRating(r['Crossing']),
    finishing: parseSkillRating(r['Finishing']),
    dribbling: parseSkillRating(r['Dribbling']),
    sprint_speed: parseSkillRating(r['SprintSpeed']),
    stamina: parseSkillRating(r['Stamina']),
  }));
}

let cachedStore: DataStore | null = null;

export function loadAllData(): DataStore {
  if (cachedStore) return cachedStore;
  cachedStore = {
    brasileirao: loadBrasileiraoMatches(),
    copa: loadCupMatches(),
    libertadores: loadLibertadoresMatches(),
    extended: loadExtendedMatches(),
    historical: loadHistoricalMatches(),
    players: loadFifaPlayers(),
  };
  return cachedStore;
}
