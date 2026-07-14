/**
 * ============================================================================
 * Context Block
 * ----------------------------------------------------------------------------
 * File:    src/dataLoader.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: Read the six Kaggle CSV files from `data/kaggle/` and project each
 *          heterogeneous row into the unified `Match` / `Player` domain types
 *          (see src/types.ts). Each source has its own columns, encoding and
 *          quirks; the per-file loaders below isolate that mess so the rest of
 *          the codebase only ever sees normalized records.
 *
 * Sources handled:
 *   - Brasileirao_Matches.csv         -> Brasileirão (with state suffixes)
 *   - Brazilian_Cup_Matches.csv       -> Copa do Brasil
 *   - Libertadores_Matches.csv        -> Copa Libertadores (with stage)
 *   - BR-Football-Dataset.csv         -> mixed tournaments + extended stats
 *   - novo_campeonato_brasileiro.csv  -> historical Brasileirão (2003-2019)
 *   - fifa_data.csv                   -> FIFA player database
 *
 * Notes:
 *   - Files are read as UTF-8 to preserve Portuguese accents/cedillas.
 *   - The historical Brasileirão file overlaps in years with the newer
 *     Brasileirão file; both are loaded and tagged by `source` so callers can
 *     deduplicate if needed. Standings/stat helpers operate per (competition,
 *     season) and prefer a single source to avoid double counting.
 * ============================================================================
 */

import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { parse } from 'csv-parse/sync';
import type { Match, Player } from './types.js';
import {
  teamKey,
  displayTeamName,
  parseDate,
  parseYear,
  parseGoals,
  parseIntField,
} from './normalize.js';

type Row = Record<string, string>;

function readCsv(path: string): Row[] {
  const text = readFileSync(path, 'utf-8').replace(/^﻿/, '');
  return parse(text, {
    columns: true,
    skip_empty_lines: true,
    relax_quotes: true,
    relax_column_count: true,
    trim: true,
    bom: true,
  }) as Row[];
}

function makeMatch(
  partial: Omit<Match, 'homeKey' | 'awayKey'> & {
    homeKey?: string;
    awayKey?: string;
  },
): Match | null {
  if (!partial.homeTeam || !partial.awayTeam) return null;
  if (partial.homeGoal == null || partial.awayGoal == null) return null;
  return {
    ...partial,
    homeKey: teamKey(partial.homeTeam),
    awayKey: teamKey(partial.awayTeam),
  };
}

function loadBrasileirao(path: string): Match[] {
  const out: Match[] = [];
  for (const r of readCsv(path)) {
    const homeGoal = parseGoals(r.home_goal);
    const awayGoal = parseGoals(r.away_goal);
    const season = parseYear(r.season);
    if (homeGoal == null || awayGoal == null || season == null) continue;
    const m = makeMatch({
      competition: 'Brasileirão',
      season,
      date: parseDate(r.datetime),
      round: parseIntField(r.round),
      stage: null,
      homeTeam: displayTeamName(r.home_team),
      awayTeam: displayTeamName(r.away_team),
      homeGoal,
      awayGoal,
      homeState: r.home_team_state || null,
      awayState: r.away_team_state || null,
      arena: null,
      source: 'Brasileirao_Matches.csv',
    });
    if (m) out.push(m);
  }
  return out;
}

function loadCup(path: string): Match[] {
  const out: Match[] = [];
  for (const r of readCsv(path)) {
    const homeGoal = parseGoals(r.home_goal);
    const awayGoal = parseGoals(r.away_goal);
    const season = parseYear(r.season);
    if (homeGoal == null || awayGoal == null || season == null) continue;
    const m = makeMatch({
      competition: 'Copa do Brasil',
      season,
      date: parseDate(r.datetime),
      round: parseIntField(r.round),
      stage: r.round || null,
      homeTeam: displayTeamName(r.home_team),
      awayTeam: displayTeamName(r.away_team),
      homeGoal,
      awayGoal,
      homeState: null,
      awayState: null,
      arena: null,
      source: 'Brazilian_Cup_Matches.csv',
    });
    if (m) out.push(m);
  }
  return out;
}

function loadLibertadores(path: string): Match[] {
  const out: Match[] = [];
  for (const r of readCsv(path)) {
    const homeGoal = parseGoals(r.home_goal);
    const awayGoal = parseGoals(r.away_goal);
    const season = parseYear(r.season);
    if (homeGoal == null || awayGoal == null || season == null) continue;
    const m = makeMatch({
      competition: 'Copa Libertadores',
      season,
      date: parseDate(r.datetime),
      round: null,
      stage: r.stage || null,
      homeTeam: displayTeamName(r.home_team),
      awayTeam: displayTeamName(r.away_team),
      homeGoal,
      awayGoal,
      homeState: null,
      awayState: null,
      arena: null,
      source: 'Libertadores_Matches.csv',
    });
    if (m) out.push(m);
  }
  return out;
}

/** Map the BR-Football "tournament" values to canonical competition names. */
function canonicalTournament(value: string): string {
  const t = (value || '').trim().toLowerCase();
  if (t === 'serie a') return 'Brasileirão';
  if (t === 'copa do brasil') return 'Copa do Brasil';
  if (t === 'serie b') return 'Serie B';
  if (t === 'serie c') return 'Serie C';
  return value || 'Unknown';
}

function loadBrFootball(path: string): Match[] {
  const out: Match[] = [];
  for (const r of readCsv(path)) {
    const homeGoal = parseGoals(r.home_goal);
    const awayGoal = parseGoals(r.away_goal);
    const date = parseDate(r.date);
    const season = parseYear(r.date);
    if (homeGoal == null || awayGoal == null || season == null) continue;
    const m = makeMatch({
      competition: canonicalTournament(r.tournament),
      season,
      date,
      round: null,
      stage: null,
      homeTeam: (r.home || '').trim(),
      awayTeam: (r.away || '').trim(),
      homeGoal,
      awayGoal,
      homeState: null,
      awayState: null,
      arena: null,
      source: 'BR-Football-Dataset.csv',
    });
    if (m) out.push(m);
  }
  return out;
}

function loadHistorical(path: string): Match[] {
  const out: Match[] = [];
  for (const r of readCsv(path)) {
    const homeGoal = parseGoals(r.Gols_mandante);
    const awayGoal = parseGoals(r.Gols_visitante);
    const season = parseYear(r.Ano) ?? parseYear(r.Data);
    if (homeGoal == null || awayGoal == null || season == null) continue;
    const m = makeMatch({
      competition: 'Brasileirão',
      season,
      date: parseDate(r.Data),
      round: parseIntField(r.Rodada),
      stage: null,
      homeTeam: displayTeamName(r.Equipe_mandante),
      awayTeam: displayTeamName(r.Equipe_visitante),
      homeGoal,
      awayGoal,
      homeState: r.Mandante_UF || null,
      awayState: r.Visitante_UF || null,
      arena: r.Arena || null,
      source: 'novo_campeonato_brasileiro.csv',
    });
    if (m) out.push(m);
  }
  return out;
}

function loadPlayers(path: string): Player[] {
  const out: Player[] = [];
  for (const r of readCsv(path)) {
    const id = parseIntField(r.ID);
    const name = (r.Name || '').trim();
    if (id == null || !name) continue;
    const club = (r.Club || '').trim();
    out.push({
      id,
      name,
      age: parseIntField(r.Age),
      nationality: (r.Nationality || '').trim(),
      overall: parseIntField(r.Overall),
      potential: parseIntField(r.Potential),
      club,
      position: (r.Position || '').trim(),
      jerseyNumber: parseIntField(r['Jersey Number']),
      height: r.Height ? r.Height.trim() : null,
      weight: r.Weight ? r.Weight.trim() : null,
      clubKey: teamKey(club),
    });
  }
  return out;
}

export interface SoccerData {
  matches: Match[];
  players: Player[];
  /** Per-source match counts, for diagnostics. */
  sourceCounts: Record<string, number>;
}

/**
 * Load every dataset under `dataDir/kaggle`. Missing files are skipped (so the
 * server still starts with partial data) but absence is reflected in counts.
 */
export function loadAllData(dataDir: string): SoccerData {
  const kaggle = join(dataDir, 'kaggle');
  const matches: Match[] = [];
  const sourceCounts: Record<string, number> = {};

  const matchFiles: Array<[string, (p: string) => Match[]]> = [
    ['Brasileirao_Matches.csv', loadBrasileirao],
    ['Brazilian_Cup_Matches.csv', loadCup],
    ['Libertadores_Matches.csv', loadLibertadores],
    ['BR-Football-Dataset.csv', loadBrFootball],
    ['novo_campeonato_brasileiro.csv', loadHistorical],
  ];

  for (const [file, loader] of matchFiles) {
    const path = join(kaggle, file);
    if (!existsSync(path)) {
      sourceCounts[file] = 0;
      continue;
    }
    const loaded = loader(path);
    sourceCounts[file] = loaded.length;
    matches.push(...loaded);
  }

  let players: Player[] = [];
  const playerPath = join(kaggle, 'fifa_data.csv');
  if (existsSync(playerPath)) {
    players = loadPlayers(playerPath);
  }
  sourceCounts['fifa_data.csv'] = players.length;

  return { matches, players, sourceCounts };
}
