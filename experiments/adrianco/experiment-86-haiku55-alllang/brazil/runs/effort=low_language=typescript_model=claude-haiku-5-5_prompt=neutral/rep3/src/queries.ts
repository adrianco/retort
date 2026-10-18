/*
 * Context: Pure query functions over the in-memory Dataset. Each function takes a
 * Dataset plus structured filters and returns plain data; formatting for the LLM lives in
 * format.ts and MCP wiring in server.ts. Team names are resolved through normalize.ts so
 * "Palmeiras-SP", "Palmeiras" and "Sociedade Esportiva Palmeiras" are the same team.
 * Related: dataset.ts, normalize.ts, format.ts, server.ts.
 */
import { foldText, matchesText, teamKey } from './normalize.js';
import { COMPETITION } from './dataset.js';
import type { Dataset, Match, Player, Venue } from './types.js';

/** User-facing error: message is returned to the LLM verbatim. */
export class QueryError extends Error {}

export interface MatchFilter {
  competition?: string;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  dateFrom?: string;
  dateTo?: string;
}

export interface Resolved {
  key: string;
  name: string;
}

/** Resolve free-text team input to a canonical team key, with exact → alias → substring fallback. */
export function resolveTeam(ds: Dataset, input: string): Resolved {
  const key = teamKey(input);
  if (ds.teams.has(key)) return { key, name: ds.teams.get(key)! };

  const candidates = [...ds.teams.entries()].filter(
    ([k, name]) => k.includes(key) || matchesText(name, input),
  );
  if (candidates.length === 1) return { key: candidates[0][0], name: candidates[0][1] };
  if (candidates.length === 0) throw new QueryError(`No team matching "${input}" found in the datasets.`);
  const names = candidates.slice(0, 10).map(([, n]) => n).join(', ');
  throw new QueryError(`"${input}" is ambiguous. Did you mean one of: ${names}?`);
}

/** Resolve a competition filter ("brasileirao", "copa do brasil", "libertadores", ...). */
export function competitionFilter(m: Match, competition?: string): boolean {
  return !competition || matchesText(m.competition, competition);
}

export function matchFilter(m: Match, f: MatchFilter): boolean {
  if (!competitionFilter(m, f.competition)) return false;
  if (f.season !== undefined && m.season !== f.season) return false;
  if (f.seasonFrom !== undefined && (m.season ?? 0) < f.seasonFrom) return false;
  if (f.seasonTo !== undefined && (m.season ?? 0) > f.seasonTo) return false;
  if (f.dateFrom && m.date < f.dateFrom) return false;
  if (f.dateTo && m.date > f.dateTo) return false;
  return true;
}

export type Outcome = 'W' | 'D' | 'L';

export interface TeamMatch {
  match: Match;
  venue: 'home' | 'away';
  goalsFor: number;
  goalsAgainst: number;
  opponent: string;
  result: Outcome;
}

/** Express a match from one team's perspective. */
export function perspective(m: Match, teamKeyValue: string): TeamMatch | null {
  const isHome = m.homeKey === teamKeyValue;
  const isAway = m.awayKey === teamKeyValue;
  if (!isHome && !isAway) return null;
  const goalsFor = isHome ? m.homeGoals : m.awayGoals;
  const goalsAgainst = isHome ? m.awayGoals : m.homeGoals;
  const result: Outcome = goalsFor > goalsAgainst ? 'W' : goalsFor < goalsAgainst ? 'L' : 'D';
  return {
    match: m,
    venue: isHome ? 'home' : 'away',
    goalsFor,
    goalsAgainst,
    opponent: isHome ? m.away : m.home,
    result,
  };
}

const byDateDesc = (a: Match, b: Match) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0);
const byDateAsc = (a: Match, b: Match) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0);

export interface MatchSearch {
  team?: string;
  opponent?: string;
  venue?: Venue;
  limit?: number;
  filter?: MatchFilter;
}

export interface MatchSearchResult {
  total: number;
  matches: Match[];
  team?: Resolved;
  opponent?: Resolved;
}

/** Find matches by team (home/away/either), opponent, competition, season and date range. */
export function searchMatches(ds: Dataset, q: MatchSearch): MatchSearchResult {
  const team = q.team ? resolveTeam(ds, q.team) : undefined;
  const opponent = q.opponent ? resolveTeam(ds, q.opponent) : undefined;
  const venue = q.venue ?? 'any';
  const found = ds.matches.filter((m) => {
    if (q.filter && !matchFilter(m, q.filter)) return false;
    if (team && !involves(m, team.key, venue)) return false;
    if (opponent && !involves(m, opponent.key, 'any')) return false;
    if (team && opponent && !(m.homeKey === team.key && m.awayKey === opponent.key) &&
        !(m.homeKey === opponent.key && m.awayKey === team.key)) return false;
    return true;
  });
  found.sort(byDateDesc);
  return { total: found.length, matches: found.slice(0, q.limit ?? 20), team, opponent };
}

function involves(m: Match, key: string, venue: Venue): boolean {
  if (venue === 'home') return m.homeKey === key;
  if (venue === 'away') return m.awayKey === key;
  return m.homeKey === key || m.awayKey === key;
}

export interface TallyRecord {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number; // percentage, one decimal
}

export interface TeamStats extends TallyRecord {
  team: Resolved;
  venue: Venue;
  filter: MatchFilter;
  matches: TeamMatch[];
}

function tally(rows: TeamMatch[]): TallyRecord {
  const wins = rows.filter((r) => r.result === 'W').length;
  const draws = rows.filter((r) => r.result === 'D').length;
  const losses = rows.filter((r) => r.result === 'L').length;
  const played = rows.length;
  return {
    played,
    wins,
    draws,
    losses,
    goalsFor: rows.reduce((s, r) => s + r.goalsFor, 0),
    goalsAgainst: rows.reduce((s, r) => s + r.goalsAgainst, 0),
    winRate: played ? Math.round((wins / played) * 1000) / 10 : 0,
  };
}

/** Wins/losses/draws/goals for one team, optionally restricted by competition, season, and venue. */
export function teamStats(
  ds: Dataset,
  team: string,
  opts: { venue?: Venue; filter?: MatchFilter } = {},
): TeamStats {
  const resolved = resolveTeam(ds, team);
  const venue = opts.venue ?? 'any';
  const filter = opts.filter ?? {};
  const rows = ds.matches
    .filter((m) => matchFilter(m, filter) && involves(m, resolved.key, venue))
    .map((m) => perspective(m, resolved.key)!)
    .sort((a, b) => byDateAsc(a.match, b.match));
  return { team: resolved, venue, filter, ...tally(rows), matches: rows };
}

export interface HeadToHead extends TallyRecord {
  teamA: Resolved;
  teamB: Resolved;
  lastMeeting: Match | null;
  meetings: Match[];
}

/** Head-to-head record from teamA's perspective. */
export function headToHead(ds: Dataset, a: string, b: string, filter: MatchFilter = {}): HeadToHead {
  const teamA = resolveTeam(ds, a);
  const teamB = resolveTeam(ds, b);
  if (teamA.key === teamB.key) throw new QueryError('Head-to-head needs two different teams.');
  const meetings = ds.matches
    .filter((m) => matchFilter(m, filter) && (m.homeKey === teamA.key || m.awayKey === teamA.key) &&
      (m.homeKey === teamB.key || m.awayKey === teamB.key))
    .sort(byDateAsc);
  const rows = meetings.map((m) => perspective(m, teamA.key)!);
  return {
    teamA,
    teamB,
    ...tally(rows),
    lastMeeting: meetings.length ? meetings[meetings.length - 1] : null,
    meetings,
  };
}

export interface StandingRow extends TallyRecord {
  position: number;
  team: string;
  key: string;
  points: number;
  goalDifference: number;
}

/** League table calculated from match results (3 pts win, 1 draw). */
export function standings(ds: Dataset, season: number, competition: string = COMPETITION.SERIE_A): StandingRow[] {
  const matches = ds.matches.filter((m) => matchFilter(m, { season, competition }));
  const keys = new Set<string>();
  matches.forEach((m) => { keys.add(m.homeKey); keys.add(m.awayKey); });
  const rows: StandingRow[] = [...keys].map((key) => {
    const games = matches.map((m) => perspective(m, key)).filter((x): x is TeamMatch => x !== null);
    const rec = tally(games);
    return {
      ...rec,
      position: 0,
      key,
      team: ds.teams.get(key) ?? key,
      points: rec.wins * 3 + rec.draws,
      goalDifference: rec.goalsFor - rec.goalsAgainst,
    };
  });
  rows.sort((x, y) => y.points - x.points || y.wins - x.wins || y.goalDifference - x.goalDifference ||
    y.goalsFor - x.goalsFor || x.team.localeCompare(y.team));
  rows.forEach((r, i) => (r.position = i + 1));
  return rows;
}

/** Largest margins of victory, ties broken by total goals then recency. */
export function biggestWins(ds: Dataset, filter: MatchFilter = {}, limit = 10): Match[] {
  return ds.matches
    .filter((m) => matchFilter(m, filter))
    .sort((a, b) => {
      const ma = Math.abs(a.homeGoals - a.awayGoals);
      const mb = Math.abs(b.homeGoals - b.awayGoals);
      return mb - ma || (b.homeGoals + b.awayGoals) - (a.homeGoals + a.awayGoals) || byDateDesc(a, b);
    })
    .slice(0, limit);
}

export interface AggregateStats {
  matches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
}

/** League-wide aggregates; pass different seasons in two calls to compare seasons. */
export function aggregateStats(ds: Dataset, filter: MatchFilter = {}): AggregateStats {
  const ms = ds.matches.filter((m) => matchFilter(m, filter));
  const n = ms.length;
  const pct = (x: number) => (n ? Math.round((x / n) * 1000) / 10 : 0);
  const homeWins = ms.filter((m) => m.homeGoals > m.awayGoals).length;
  const draws = ms.filter((m) => m.homeGoals === m.awayGoals).length;
  const totalGoals = ms.reduce((s, m) => s + m.homeGoals + m.awayGoals, 0);
  return {
    matches: n,
    totalGoals,
    avgGoalsPerMatch: n ? Math.round((totalGoals / n) * 100) / 100 : 0,
    homeWinRate: pct(homeWins),
    drawRate: pct(draws),
    awayWinRate: pct(ms.filter((m) => m.homeGoals < m.awayGoals).length),
  };
}

export interface PlayerSearch {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  sortBy?: 'overall' | 'potential' | 'age';
  limit?: number;
}

/** Search FIFA players by name, nationality, club, position and rating. */
export function searchPlayers(ds: Dataset, q: PlayerSearch): { total: number; players: Player[] } {
  const found = ds.players.filter((p) => {
    if (q.name && !matchesText(p.name, q.name)) return false;
    if (q.nationality && !matchesText(p.nationality, q.nationality)) return false;
    if (q.club && !matchesText(p.club, q.club)) return false;
    if (q.position && foldText(p.position) !== foldText(q.position)) return false;
    if (q.minOverall !== undefined && (p.overall ?? 0) < q.minOverall) return false;
    return true;
  });
  const sortBy = q.sortBy ?? 'overall';
  found.sort((a, b) => {
    if (sortBy === 'age') return (a.age ?? Infinity) - (b.age ?? Infinity);
    return ((b[sortBy] ?? 0) - (a[sortBy] ?? 0)) || a.name.localeCompare(b.name);
  });
  return { total: found.length, players: found.slice(0, q.limit ?? 20) };
}

export interface ClubSummary {
  club: string;
  players: number;
  avgOverall: number;
  isBrazilianClub: boolean;
  topPlayer: Player | null;
}

/**
 * Squad summary per club. "Brazilian clubs" are clubs whose names appear in the match datasets
 * (cross-file join), so the player data is grouped against the same team keys.
 */
export function clubSummaries(
  ds: Dataset,
  opts: { nationality?: string; brazilianClubsOnly?: boolean; limit?: number } = {},
): ClubSummary[] {
  const groups = new Map<string, Player[]>();
  for (const p of ds.players) {
    if (!p.clubKey) continue;
    if (opts.nationality && !matchesText(p.nationality, opts.nationality)) continue;
    if (opts.brazilianClubsOnly && !ds.teams.has(p.clubKey)) continue;
    const list = groups.get(p.clubKey) ?? [];
    list.push(p);
    groups.set(p.clubKey, list);
  }
  const out: ClubSummary[] = [...groups.entries()].map(([key, players]) => {
    const sorted = [...players].sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    const ratings = players.map((p) => p.overall ?? 0);
    return {
      club: players[0].club,
      players: players.length,
      avgOverall: Math.round((ratings.reduce((s, r) => s + r, 0) / players.length) * 10) / 10,
      isBrazilianClub: ds.teams.has(key),
      topPlayer: sorted[0] ?? null,
    };
  });
  out.sort((a, b) => b.avgOverall - a.avgOverall || a.club.localeCompare(b.club));
  return out.slice(0, opts.limit ?? 20);
}
