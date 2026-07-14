import fs from 'fs';
import path from 'path';
import { parse } from 'csv-parse/sync';
import { normalizeTeamName } from './teamNormalizer.js';

export interface BrazileiraoMatch {
  datetime: string;
  home_team: string;
  home_team_normalized: string;
  home_team_state: string;
  away_team: string;
  away_team_normalized: string;
  away_team_state: string;
  home_goal: number;
  away_goal: number;
  season: number;
  round: number;
  competition: 'Brasileirao';
}

export interface CupMatch {
  round: string;
  datetime: string;
  home_team: string;
  home_team_normalized: string;
  away_team: string;
  away_team_normalized: string;
  home_goal: number;
  away_goal: number;
  season: number;
  competition: 'Copa do Brasil';
}

export interface LibertadoresMatch {
  datetime: string;
  home_team: string;
  home_team_normalized: string;
  away_team: string;
  away_team_normalized: string;
  home_goal: number;
  away_goal: number;
  season: number;
  stage: string;
  competition: 'Libertadores';
}

export interface BRFootballMatch {
  tournament: string;
  home: string;
  home_normalized: string;
  away: string;
  away_normalized: string;
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
}

export interface HistoricalMatch {
  id: string;
  data: string;
  ano: number;
  rodada: number;
  equipe_mandante: string;
  equipe_mandante_normalized: string;
  equipe_visitante: string;
  equipe_visitante_normalized: string;
  gols_mandante: number;
  gols_visitante: number;
  mandante_uf: string;
  visitante_uf: string;
  vencedor: string;
  arena: string;
  competition: 'Brasileirao-Historical';
}

export interface FifaPlayer {
  id: string;
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
}

export interface AllData {
  brasileirao: BrazileiraoMatch[];
  copaBrasil: CupMatch[];
  libertadores: LibertadoresMatch[];
  brFootball: BRFootballMatch[];
  historical: HistoricalMatch[];
  fifaPlayers: FifaPlayer[];
}

function readCsv(filePath: string): Record<string, string>[] {
  const content = fs.readFileSync(filePath, { encoding: 'utf-8' });
  const cleaned = content.replace(/^﻿/, '');
  return parse(cleaned, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true,
  });
}

function toNum(v: string | undefined): number {
  if (v === undefined || v === null || v === '' || v === 'NA') return 0;
  const n = parseFloat(v);
  return isNaN(n) ? 0 : n;
}

export async function loadAllData(dataDir: string): Promise<AllData> {
  const brasileiraoRaw = readCsv(path.join(dataDir, 'Brasileirao_Matches.csv'));
  const brasileirao: BrazileiraoMatch[] = brasileiraoRaw.map(r => ({
    datetime: r['datetime'] ?? '',
    home_team: r['home_team'] ?? '',
    home_team_normalized: normalizeTeamName(r['home_team'] ?? ''),
    home_team_state: r['home_team_state'] ?? '',
    away_team: r['away_team'] ?? '',
    away_team_normalized: normalizeTeamName(r['away_team'] ?? ''),
    away_team_state: r['away_team_state'] ?? '',
    home_goal: toNum(r['home_goal']),
    away_goal: toNum(r['away_goal']),
    season: toNum(r['season']),
    round: toNum(r['round']),
    competition: 'Brasileirao',
  }));

  const cupRaw = readCsv(path.join(dataDir, 'Brazilian_Cup_Matches.csv'));
  const copaBrasil: CupMatch[] = cupRaw.map(r => ({
    round: r['round'] ?? '',
    datetime: r['datetime'] ?? '',
    home_team: r['home_team'] ?? '',
    home_team_normalized: normalizeTeamName(r['home_team'] ?? ''),
    away_team: r['away_team'] ?? '',
    away_team_normalized: normalizeTeamName(r['away_team'] ?? ''),
    home_goal: toNum(r['home_goal']),
    away_goal: toNum(r['away_goal']),
    season: toNum(r['season']),
    competition: 'Copa do Brasil',
  }));

  const libRaw = readCsv(path.join(dataDir, 'Libertadores_Matches.csv'));
  const libertadores: LibertadoresMatch[] = libRaw.map(r => ({
    datetime: r['datetime'] ?? '',
    home_team: r['home_team'] ?? '',
    home_team_normalized: normalizeTeamName(r['home_team'] ?? ''),
    away_team: r['away_team'] ?? '',
    away_team_normalized: normalizeTeamName(r['away_team'] ?? ''),
    home_goal: toNum(r['home_goal']),
    away_goal: toNum(r['away_goal']),
    season: toNum(r['season']),
    stage: r['stage'] ?? '',
    competition: 'Libertadores',
  }));

  const brRaw = readCsv(path.join(dataDir, 'BR-Football-Dataset.csv'));
  const brFootball: BRFootballMatch[] = brRaw.map(r => ({
    tournament: r['tournament'] ?? '',
    home: r['home'] ?? '',
    home_normalized: normalizeTeamName(r['home'] ?? ''),
    away: r['away'] ?? '',
    away_normalized: normalizeTeamName(r['away'] ?? ''),
    home_goal: toNum(r['home_goal']),
    away_goal: toNum(r['away_goal']),
    home_corner: toNum(r['home_corner']),
    away_corner: toNum(r['away_corner']),
    home_attack: toNum(r['home_attack']),
    away_attack: toNum(r['away_attack']),
    home_shots: toNum(r['home_shots']),
    away_shots: toNum(r['away_shots']),
    time: r['time'] ?? '',
    date: r['date'] ?? '',
    ht_result: r['ht_result'] ?? '',
    at_result: r['at_result'] ?? '',
    total_corners: toNum(r['total_corners']),
  }));

  const histRaw = readCsv(path.join(dataDir, 'novo_campeonato_brasileiro.csv'));
  const historical: HistoricalMatch[] = histRaw.map(r => ({
    id: r['ID'] ?? '',
    data: r['Data'] ?? '',
    ano: toNum(r['Ano']),
    rodada: toNum(r['Rodada']),
    equipe_mandante: r['Equipe_mandante'] ?? '',
    equipe_mandante_normalized: normalizeTeamName(r['Equipe_mandante'] ?? ''),
    equipe_visitante: r['Equipe_visitante'] ?? '',
    equipe_visitante_normalized: normalizeTeamName(r['Equipe_visitante'] ?? ''),
    gols_mandante: toNum(r['Gols_mandante']),
    gols_visitante: toNum(r['Gols_visitante']),
    mandante_uf: r['Mandante_UF'] ?? '',
    visitante_uf: r['Visitante_UF'] ?? '',
    vencedor: r['Vencedor'] ?? '',
    arena: r['Arena'] ?? '',
    competition: 'Brasileirao-Historical',
  }));

  const fifaRaw = readCsv(path.join(dataDir, 'fifa_data.csv'));
  const fifaPlayers: FifaPlayer[] = fifaRaw.map(r => ({
    id: r['ID'] ?? '',
    name: r['Name'] ?? '',
    age: toNum(r['Age']),
    nationality: r['Nationality'] ?? '',
    overall: toNum(r['Overall']),
    potential: toNum(r['Potential']),
    club: r['Club'] ?? '',
    position: r['Position'] ?? '',
    jersey_number: r['Jersey Number'] ?? '',
    height: r['Height'] ?? '',
    weight: r['Weight'] ?? '',
  }));

  return { brasileirao, copaBrasil, libertadores, brFootball, historical, fifaPlayers };
}
