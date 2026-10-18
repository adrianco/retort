import { containsWords, normalizeTeamName, teamMatches } from "./normalize.js";
import type { Dataset, Match, Player } from "./model.js";

export const DEFAULT_LEAGUE = "Brasileirão Série A";
const DEFAULT_LIMIT = 20;

export interface MatchFilter {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  startDate?: string;
  endDate?: string;
}

export interface TeamRecord {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  /** Fraction in [0, 1]. */
  winRate: number;
}

export interface StandingRow extends TeamRecord {
  team: string;
  points: number;
  goalDifference: number;
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

export interface MatchStats {
  matches: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
  biggestWins: Match[];
}

/** Does a match fit the team/opponent/competition/season/date filter? */
function matchFits(m: Match, f: MatchFilter): boolean {
  if (f.competition && !containsWords(m.competition, f.competition)) return false;
  if (f.season !== undefined && m.season !== f.season) return false;
  if (f.startDate && m.date < f.startDate) return false;
  if (f.endDate && m.date > f.endDate) return false;
  if (f.team && f.opponent) {
    return (
      (teamMatches(m.home, f.team) && teamMatches(m.away, f.opponent)) ||
      (teamMatches(m.home, f.opponent) && teamMatches(m.away, f.team))
    );
  }
  if (f.team) return teamMatches(m.home, f.team) || teamMatches(m.away, f.team);
  if (f.opponent) return teamMatches(m.home, f.opponent) || teamMatches(m.away, f.opponent);
  return true;
}

function filterMatches(ds: Dataset, f: MatchFilter): Match[] {
  return ds.matches.filter((m) => matchFits(m, f));
}

/** Most recent first. */
function newestFirst(a: Match, b: Match): number {
  return b.date.localeCompare(a.date) || b.id.localeCompare(a.id);
}

export interface MatchSearchResult {
  total: number;
  matches: Match[];
}

/** Find matches by team, opponent, competition, season and/or date range. */
export function searchMatches(
  ds: Dataset,
  filter: MatchFilter & { limit?: number },
): MatchSearchResult {
  const found = filterMatches(ds, filter).sort(newestFirst);
  return { total: found.length, matches: found.slice(0, filter.limit ?? DEFAULT_LIMIT) };
}

function emptyRecord(): TeamRecord {
  return { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, winRate: 0 };
}

function addResult(rec: TeamRecord, goalsFor: number, goalsAgainst: number): void {
  rec.matches++;
  rec.goalsFor += goalsFor;
  rec.goalsAgainst += goalsAgainst;
  if (goalsFor > goalsAgainst) rec.wins++;
  else if (goalsFor === goalsAgainst) rec.draws++;
  else rec.losses++;
}

function finishRecord(rec: TeamRecord): TeamRecord {
  rec.winRate = rec.matches === 0 ? 0 : rec.wins / rec.matches;
  return rec;
}

export interface TeamRecordFilter {
  team: string;
  competition?: string;
  season?: number;
  venue?: "home" | "away" | "any";
}

/** Win/draw/loss and goals for one team, optionally restricted by venue. */
export function teamRecord(ds: Dataset, f: TeamRecordFilter): TeamRecord {
  const rec = emptyRecord();
  const venue = f.venue ?? "any";
  for (const m of filterMatches(ds, { competition: f.competition, season: f.season })) {
    if (venue !== "away" && teamMatches(m.home, f.team)) {
      addResult(rec, m.homeGoals, m.awayGoals);
    } else if (venue !== "home" && teamMatches(m.away, f.team)) {
      addResult(rec, m.awayGoals, m.homeGoals);
    }
  }
  return finishRecord(rec);
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  /** TeamRecord from teamA's perspective. */
  record: TeamRecord;
  winsB: number;
  matches: Match[];
}

/** All meetings between two teams, with the record from teamA's perspective. */
export function headToHead(
  ds: Dataset,
  f: { teamA: string; teamB: string; competition?: string },
): HeadToHead {
  const meetings = filterMatches(ds, {
    team: f.teamA,
    opponent: f.teamB,
    competition: f.competition,
  }).sort(newestFirst);

  const record = emptyRecord();
  let winsB = 0;
  for (const m of meetings) {
    const aIsHome = teamMatches(m.home, f.teamA);
    const aGoals = aIsHome ? m.homeGoals : m.awayGoals;
    const bGoals = aIsHome ? m.awayGoals : m.homeGoals;
    addResult(record, aGoals, bGoals);
    if (bGoals > aGoals) winsB++;
  }
  return { teamA: f.teamA, teamB: f.teamB, record: finishRecord(record), winsB, matches: meetings };
}

/**
 * League table for one season and competition, computed from results
 * (3 points for a win, 1 for a draw). Sorted by points, then goal difference,
 * then goals scored, then name.
 */
export function standings(
  ds: Dataset,
  f: { season: number; competition?: string },
): StandingRow[] {
  const rows = new Map<string, StandingRow>();
  const rowFor = (name: string): StandingRow => {
    const key = normalizeTeamName(name);
    let row = rows.get(key);
    if (!row) {
      row = {
        team: name,
        points: 0,
        goalDifference: 0,
        ...emptyRecord(),
      };
      rows.set(key, row);
    }
    return row;
  };

  const apply = (row: StandingRow, goalsFor: number, goalsAgainst: number): void => {
    addResult(row, goalsFor, goalsAgainst);
    row.goalDifference = row.goalsFor - row.goalsAgainst;
    row.points = row.wins * 3 + row.draws;
  };

  for (const m of filterMatches(ds, { season: f.season, competition: f.competition ?? DEFAULT_LEAGUE })) {
    apply(rowFor(m.home), m.homeGoals, m.awayGoals);
    apply(rowFor(m.away), m.awayGoals, m.homeGoals);
  }

  return [...rows.values()]
    .map((row) => ({ ...row, winRate: row.matches === 0 ? 0 : row.wins / row.matches }))
    .sort(
      (a, b) =>
        b.points - a.points ||
        b.goalDifference - a.goalDifference ||
        b.goalsFor - a.goalsFor ||
        a.team.localeCompare(b.team),
    );
}

function containsOrEmpty(value: string, query: string | undefined): boolean {
  return query === undefined || containsWords(value, query);
}

/** Players matching the filters, best overall rating first. */
export function searchPlayers(ds: Dataset, f: PlayerFilter): Player[] {
  const limit = f.limit ?? DEFAULT_LIMIT;
  const position = f.position?.trim().toUpperCase();
  return ds.players
    .filter(
      (p) =>
        containsOrEmpty(p.name, f.name) &&
        containsOrEmpty(p.nationality, f.nationality) &&
        containsOrEmpty(p.club, f.club) &&
        (position === undefined || p.position.toUpperCase() === position) &&
        (f.minOverall === undefined || p.overall >= f.minOverall),
    )
    .sort((a, b) => b.overall - a.overall || a.name.localeCompare(b.name))
    .slice(0, limit);
}

export interface ClubSummary {
  club: string;
  players: number;
  averageOverall: number;
}

/** Number of matching players and their average rating, grouped by club. */
export function clubSummary(ds: Dataset, f: { nationality?: string }): ClubSummary[] {
  const groups = new Map<string, { players: number; total: number }>();
  for (const p of ds.players) {
    if (!containsOrEmpty(p.nationality, f.nationality) || !p.club) continue;
    const g = groups.get(p.club) ?? { players: 0, total: 0 };
    g.players++;
    g.total += p.overall;
    groups.set(p.club, g);
  }
  return [...groups.entries()]
    .map(([club, g]) => ({
      club,
      players: g.players,
      averageOverall: Math.round((g.total / g.players) * 10) / 10,
    }))
    .sort((a, b) => b.players - a.players || a.club.localeCompare(b.club));
}

const round2 = (n: number): number => Math.round(n * 100) / 100;

/** Aggregate results for matches fitting the filter. */
export function matchStatistics(ds: Dataset, f: MatchFilter & { biggestWinsLimit?: number }): MatchStats {
  const matches = filterMatches(ds, f);
  if (matches.length === 0) {
    return {
      matches: 0,
      totalGoals: 0,
      averageGoalsPerMatch: 0,
      homeWinRate: 0,
      drawRate: 0,
      awayWinRate: 0,
      biggestWins: [],
    };
  }
  let totalGoals = 0;
  let homeWins = 0;
  let draws = 0;
  let awayWins = 0;
  for (const m of matches) {
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }
  const biggestWins = matches
    .filter((m) => m.homeGoals !== m.awayGoals)
    .sort((a, b) => {
      const marginA = Math.abs(a.homeGoals - a.awayGoals);
      const marginB = Math.abs(b.homeGoals - b.awayGoals);
      return marginB - marginA || b.date.localeCompare(a.date);
    })
    .slice(0, f.biggestWinsLimit ?? 5);

  const n = matches.length;
  return {
    matches: n,
    totalGoals,
    averageGoalsPerMatch: round2(totalGoals / n),
    homeWinRate: homeWins / n,
    drawRate: draws / n,
    awayWinRate: awayWins / n,
    biggestWins,
  };
}
