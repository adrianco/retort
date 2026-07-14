import { teamMatches } from "../normalize.js";
import type { Dataset, Match } from "../types.js";
import { findMatches } from "./matches.js";

export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
  winRate: number;
  goalDiff: number;
}

export interface TeamSplit {
  overall: TeamRecord;
  home: TeamRecord;
  away: TeamRecord;
}

function emptyRecord(team: string): TeamRecord {
  return {
    team,
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    points: 0,
    winRate: 0,
    goalDiff: 0,
  };
}

function applyResult(rec: TeamRecord, gf: number, ga: number) {
  rec.matches++;
  rec.goalsFor += gf;
  rec.goalsAgainst += ga;
  if (gf > ga) {
    rec.wins++;
    rec.points += 3;
  } else if (gf === ga) {
    rec.draws++;
    rec.points += 1;
  } else {
    rec.losses++;
  }
  rec.winRate = rec.matches > 0 ? rec.wins / rec.matches : 0;
  rec.goalDiff = rec.goalsFor - rec.goalsAgainst;
}

export function teamRecord(
  dataset: Dataset,
  team: string,
  opts: { competition?: string; season?: number; seasonFrom?: number; seasonTo?: number } = {},
): TeamSplit {
  const matches = findMatches(dataset, {
    team,
    competition: opts.competition,
    season: opts.season,
    seasonFrom: opts.seasonFrom,
    seasonTo: opts.seasonTo,
  });

  const overall = emptyRecord(team);
  const home = emptyRecord(team);
  const away = emptyRecord(team);

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const isHome = teamMatches(team, m.homeTeamRaw);
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    applyResult(overall, gf, ga);
    applyResult(isHome ? home : away, gf, ga);
  }
  return { overall, home, away };
}

export function listTeams(dataset: Dataset, opts: { competition?: string; season?: number } = {}): string[] {
  const matches = findMatches(dataset, opts);
  const set = new Set<string>();
  for (const m of matches) {
    if (m.homeTeam) set.add(m.homeTeam);
    if (m.awayTeam) set.add(m.awayTeam);
  }
  return [...set].sort();
}

export interface TopScoringTeam {
  team: string;
  goals: number;
  matches: number;
  goalsPerMatch: number;
}

export function topScoringTeams(
  dataset: Dataset,
  opts: { competition?: string; season?: number; limit?: number } = {},
): TopScoringTeam[] {
  const matches = findMatches(dataset, opts);
  const goals = new Map<string, { team: string; goals: number; matches: number }>();
  const inc = (raw: string, normalized: string, g: number) => {
    if (!normalized) return;
    if (!goals.has(normalized)) goals.set(normalized, { team: raw, goals: 0, matches: 0 });
    const r = goals.get(normalized)!;
    r.goals += g;
    r.matches++;
  };
  for (const m of matches) {
    if (m.homeGoals !== null) inc(m.homeTeamRaw, m.homeTeam, m.homeGoals);
    if (m.awayGoals !== null) inc(m.awayTeamRaw, m.awayTeam, m.awayGoals);
  }
  const list = [...goals.values()].map((v) => ({
    team: v.team,
    goals: v.goals,
    matches: v.matches,
    goalsPerMatch: v.matches > 0 ? v.goals / v.matches : 0,
  }));
  list.sort((a, b) => b.goals - a.goals);
  return list.slice(0, opts.limit ?? 10);
}

export interface StandingsRow extends TeamRecord {
  rank: number;
}

export function computeStandings(
  dataset: Dataset,
  opts: { competition?: string; season?: number } = {},
): StandingsRow[] {
  const matches = findMatches(dataset, opts);
  const table = new Map<string, TeamRecord>();
  const ensure = (normalized: string, raw: string): TeamRecord => {
    if (!table.has(normalized)) table.set(normalized, emptyRecord(raw));
    return table.get(normalized)!;
  };
  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const home = ensure(m.homeTeam, m.homeTeamRaw);
    const away = ensure(m.awayTeam, m.awayTeamRaw);
    applyResult(home, m.homeGoals, m.awayGoals);
    applyResult(away, m.awayGoals, m.homeGoals);
  }
  const rows = [...table.values()];
  rows.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.goalDiff !== a.goalDiff) return b.goalDiff - a.goalDiff;
    if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
    return a.team.localeCompare(b.team);
  });
  return rows.map((r, i) => ({ ...r, rank: i + 1 }));
}
