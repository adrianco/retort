/**
 * Win/draw/loss records, league tables and head-to-heads, all calculated
 * from match results (3 points for a win, 1 for a draw).
 */
import { rate, round } from '../text.js';
import type { Match } from './model.js';

export interface TeamRecord {
  team: string; // key
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  winRate: number;
}

export type Venue = 'home' | 'away' | 'all';

export function emptyRecord(team: string): TeamRecord {
  return { team, played: 0, won: 0, drawn: 0, lost: 0, goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0, winRate: 0 };
}

function add(record: TeamRecord, scored: number, conceded: number): void {
  record.played++;
  record.goalsFor += scored;
  record.goalsAgainst += conceded;
  if (scored > conceded) record.won++;
  else if (scored === conceded) record.drawn++;
  else record.lost++;
  record.goalDifference = record.goalsFor - record.goalsAgainst;
  record.points = record.won * 3 + record.drawn;
  record.winRate = rate(record.won, record.played);
}

export function recordFor(team: string, matches: Match[], venue: Venue = 'all'): TeamRecord {
  const record = emptyRecord(team);
  for (const m of matches) {
    if (m.home === team && venue !== 'away') add(record, m.homeGoals, m.awayGoals);
    else if (m.away === team && venue !== 'home') add(record, m.awayGoals, m.homeGoals);
  }
  return record;
}

/** Records for every team appearing in the matches. */
export function recordsFor(matches: Match[], venue: Venue = 'all'): TeamRecord[] {
  const records = new Map<string, TeamRecord>();
  const get = (team: string) => {
    const existing = records.get(team);
    if (existing) return existing;
    const created = emptyRecord(team);
    records.set(team, created);
    return created;
  };
  for (const m of matches) {
    if (venue !== 'away') add(get(m.home), m.homeGoals, m.awayGoals);
    if (venue !== 'home') add(get(m.away), m.awayGoals, m.homeGoals);
  }
  return [...records.values()];
}

/** League order: points, then wins, then goal difference, then goals scored. */
export function leagueTable(matches: Match[], nameOf: (key: string) => string): (TeamRecord & { position: number })[] {
  return recordsFor(matches)
    .sort((a, b) =>
      b.points - a.points ||
      b.won - a.won ||
      b.goalDifference - a.goalDifference ||
      b.goalsFor - a.goalsFor ||
      nameOf(a.team).localeCompare(nameOf(b.team)))
    .map((r, i) => ({ ...r, position: i + 1 }));
}

export interface HeadToHead {
  played: number;
  teamWins: number;
  opponentWins: number;
  draws: number;
  teamGoals: number;
  opponentGoals: number;
}

export function headToHead(team: string, opponent: string, matches: Match[]): HeadToHead {
  const r = recordFor(team, matches.filter((m) => (m.home === team && m.away === opponent) || (m.home === opponent && m.away === team)));
  return { played: r.played, teamWins: r.won, opponentWins: r.lost, draws: r.drawn, teamGoals: r.goalsFor, opponentGoals: r.goalsAgainst };
}

export interface MatchSummary {
  matches: number;
  goals: number;
  averageGoals: number;
  homeWins: number;
  draws: number;
  awayWins: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
}

export function summarise(matches: Match[]): MatchSummary {
  const goals = matches.reduce((sum, m) => sum + m.homeGoals + m.awayGoals, 0);
  const homeWins = matches.filter((m) => m.homeGoals > m.awayGoals).length;
  const awayWins = matches.filter((m) => m.awayGoals > m.homeGoals).length;
  const draws = matches.length - homeWins - awayWins;
  return {
    matches: matches.length,
    goals,
    averageGoals: matches.length ? round(goals / matches.length, 2) : 0,
    homeWins,
    draws,
    awayWins,
    homeWinRate: rate(homeWins, matches.length),
    drawRate: rate(draws, matches.length),
    awayWinRate: rate(awayWins, matches.length),
  };
}
