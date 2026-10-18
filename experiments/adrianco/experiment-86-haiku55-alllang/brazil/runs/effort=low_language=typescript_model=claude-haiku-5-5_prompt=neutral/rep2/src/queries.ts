/**
 * Context: pure query functions over a loaded Dataset. The MCP tools in
 * tools.ts are thin wrappers around these, so the behaviour can be tested
 * without a transport. Nothing here touches the filesystem.
 */
import { normalizeCompetition, normalizeTeam, teamMatches, foldText, type CompetitionName, type TeamIdentity } from './normalize.js';
import type { Dataset, Match, MatchFilter, Player } from './types.js';

export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: Match[];
  winsA: number;
  winsB: number;
  draws: number;
  goalsA: number;
  goalsB: number;
}

export interface StandingRow {
  position: number;
  team: string;
  points: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}

export interface RankedTeam {
  team: string;
  value: number;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

export type RankMetric = 'win_rate' | 'wins' | 'goals_for' | 'goal_difference' | 'points_per_match';

/** The side of a match a team played, from its perspective. */
interface Perspective {
  match: Match;
  isHome: boolean;
  goalsFor: number;
  goalsAgainst: number;
  opponent: TeamIdentity;
  team: TeamIdentity;
}

function perspective(match: Match, team: TeamIdentity): Perspective | undefined {
  if (teamMatches(team, match.home)) {
    return { match, isHome: true, goalsFor: match.homeGoals, goalsAgainst: match.awayGoals, opponent: match.away, team: match.home };
  }
  if (teamMatches(team, match.away)) {
    return { match, isHome: false, goalsFor: match.awayGoals, goalsAgainst: match.homeGoals, opponent: match.home, team: match.away };
  }
  return undefined;
}

function resultOf(p: Perspective): 'W' | 'D' | 'L' {
  if (p.goalsFor > p.goalsAgainst) return 'W';
  if (p.goalsFor < p.goalsAgainst) return 'L';
  return 'D';
}

function lastCupSeasonRound(matches: Match[], competition: CompetitionName, season: number): string | undefined {
  const rounds = matches
    .filter((m) => m.competition === competition && m.season === season && m.round !== undefined)
    .map((m) => Number(m.round))
    .filter((n) => Number.isFinite(n));
  return rounds.length ? String(Math.max(...rounds)) : undefined;
}

function resolveCompetition(raw: string | undefined): CompetitionName | undefined {
  if (!raw) return undefined;
  return normalizeCompetition(raw);
}

/** Applies match-level filters. Team filters use the venue setting (home, away, or either). */
export function filterMatches(dataset: Dataset, filter: MatchFilter = {}): Match[] {
  const team = filter.team ? normalizeTeam(filter.team) : undefined;
  const opponent = filter.opponent ? normalizeTeam(filter.opponent) : undefined;
  const competition = filter.competition ? resolveCompetition(filter.competition) : undefined;
  if (filter.competition && !competition) return [];
  const venue = filter.venue ?? 'any';

  let matches = dataset.matches.filter((m) => {
    if (competition && m.competition !== competition) return false;
    if (filter.season !== undefined && m.season !== filter.season) return false;
    if (filter.seasonFrom !== undefined && m.season < filter.seasonFrom) return false;
    if (filter.seasonTo !== undefined && m.season > filter.seasonTo) return false;
    if (filter.dateFrom && m.date < filter.dateFrom) return false;
    if (filter.dateTo && m.date > filter.dateTo) return false;

    if (team) {
      const asHome = teamMatches(team, m.home);
      const asAway = teamMatches(team, m.away);
      if (venue === 'home' && !asHome) return false;
      if (venue === 'away' && !asAway) return false;
      if (venue === 'any' && !asHome && !asAway) return false;
    }
    if (opponent) {
      const oppHome = teamMatches(opponent, m.home);
      const oppAway = teamMatches(opponent, m.away);
      if (!oppHome && !oppAway) return false;
      if (team && !(teamMatches(team, m.home) && oppAway) && !(teamMatches(team, m.away) && oppHome)) return false;
    }
    return true;
  });

  if (filter.finalOnly) {
    matches = matches.filter((m) => {
      if (m.stage !== undefined) return foldText(m.stage) === 'final';
      if (m.round === undefined) return false;
      return m.round === lastCupSeasonRound(dataset.matches, m.competition, m.season);
    });
  }

  return matches.sort((a, b) => b.date.localeCompare(a.date));
}

/** Win/draw/loss and goal totals for one team, from the perspective of the selected venue. */
export function teamRecord(dataset: Dataset, team: string, filter: MatchFilter = {}): TeamRecord {
  const identity = normalizeTeam(team);
  const sides = filterMatches(dataset, { ...filter, team, opponent: undefined })
    .map((m) => perspective(m, identity))
    .filter((p): p is Perspective => p !== undefined);

  const record: TeamRecord = {
    team: sides[0]?.team.name ?? identity.name,
    matches: sides.length,
    wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, winRate: 0,
  };
  for (const p of sides) {
    const result = resultOf(p);
    if (result === 'W') record.wins++;
    else if (result === 'D') record.draws++;
    else record.losses++;
    record.goalsFor += p.goalsFor;
    record.goalsAgainst += p.goalsAgainst;
  }
  record.winRate = record.matches ? record.wins / record.matches : 0;
  return record;
}

/** All meetings between two teams, with win/draw totals from `teamA`'s perspective. */
export function headToHead(dataset: Dataset, teamA: string, teamB: string, filter: MatchFilter = {}): HeadToHead {
  const a = normalizeTeam(teamA);
  const b = normalizeTeam(teamB);
  const matches = filterMatches(dataset, { ...filter, team: teamA, opponent: teamB, venue: 'any' });
  const result: HeadToHead = { teamA: a.name, teamB: b.name, matches, winsA: 0, winsB: 0, draws: 0, goalsA: 0, goalsB: 0 };
  for (const m of matches) {
    const pa = perspective(m, a);
    if (!pa) continue;
    result.goalsA += pa.goalsFor;
    result.goalsB += pa.goalsAgainst;
    const outcome = resultOf(pa);
    if (outcome === 'W') result.winsA++;
    else if (outcome === 'L') result.winsB++;
    else result.draws++;
  }
  return result;
}

/** Points table for one competition and season. Ties break on wins, goal difference, then goals for. */
export function standings(dataset: Dataset, competition: string, season: number): StandingRow[] {
  const matches = filterMatches(dataset, { competition, season });
  const table = new Map<string, StandingRow & { gd: number }>();
  const ensure = (team: TeamIdentity): StandingRow & { gd: number } => {
    let row = table.get(team.qualified);
    if (!row) {
      row = { position: 0, team: team.name, points: 0, played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, gd: 0 };
      table.set(team.qualified, row);
    }
    return row;
  };

  for (const m of matches) {
    const home = ensure(m.home);
    const away = ensure(m.away);
    home.played++; away.played++;
    home.goalsFor += m.homeGoals; home.goalsAgainst += m.awayGoals;
    away.goalsFor += m.awayGoals; away.goalsAgainst += m.homeGoals;
    if (m.homeGoals > m.awayGoals) {
      home.wins++; home.points += 3; away.losses++;
    } else if (m.homeGoals < m.awayGoals) {
      away.wins++; away.points += 3; home.losses++;
    } else {
      home.draws++; away.draws++; home.points++; away.points++;
    }
  }

  const rows = [...table.values()].map((r) => ({ ...r, gd: r.goalsFor - r.goalsAgainst }));
  rows.sort((x, y) =>
    y.points - x.points || y.wins - x.wins || y.gd - x.gd || y.goalsFor - x.goalsFor || x.team.localeCompare(y.team),
  );
  return rows.map(({ gd: _gd, ...row }, i) => ({ ...row, position: i + 1 }));
}

/** Ranks teams by a metric over the filtered matches. Teams need at least `minMatches` games. */
export function rankTeams(
  dataset: Dataset,
  metric: RankMetric,
  filter: MatchFilter = {},
  minMatches = 1,
  limit = 10,
): RankedTeam[] {
  const matches = filterMatches(dataset, filter);
  const teams = new Map<string, { identity: TeamIdentity; sides: Perspective[] }>();
  for (const m of matches) {
    for (const identity of [m.home, m.away]) {
      if (filter.venue === 'home' && identity !== m.home) continue;
      if (filter.venue === 'away' && identity !== m.away) continue;
      const entry = teams.get(identity.qualified) ?? { identity, sides: [] };
      const p = perspective(m, identity);
      if (p) entry.sides.push(p);
      teams.set(identity.qualified, entry);
    }
  }

  const ranked: RankedTeam[] = [];
  for (const { identity, sides } of teams.values()) {
    if (sides.length < minMatches) continue;
    const r = { team: identity.name, matches: sides.length, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
    for (const p of sides) {
      const outcome = resultOf(p);
      if (outcome === 'W') r.wins++;
      else if (outcome === 'D') r.draws++;
      else r.losses++;
      r.goalsFor += p.goalsFor;
      r.goalsAgainst += p.goalsAgainst;
    }
    const winRate = r.wins / r.matches;
    const value = {
      win_rate: winRate,
      wins: r.wins,
      goals_for: r.goalsFor,
      goal_difference: r.goalsFor - r.goalsAgainst,
      points_per_match: (r.wins * 3 + r.draws) / r.matches,
    }[metric];
    ranked.push({ ...r, value, winRate });
  }

  ranked.sort((a, b) => b.value - a.value || b.matches - a.matches || a.team.localeCompare(b.team));
  return ranked.slice(0, limit);
}

export interface LeagueStats {
  matches: number;
  totalGoals: number;
  goalsPerMatch: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
}

export function leagueStats(dataset: Dataset, filter: MatchFilter = {}): LeagueStats {
  const matches = filterMatches(dataset, filter);
  let homeWins = 0, draws = 0, awayWins = 0, totalGoals = 0;
  for (const m of matches) {
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }
  const n = matches.length;
  const pct = (x: number) => (n ? x / n : 0);
  return {
    matches: n,
    totalGoals,
    goalsPerMatch: n ? totalGoals / n : 0,
    homeWinRate: pct(homeWins),
    drawRate: pct(draws),
    awayWinRate: pct(awayWins),
  };
}

/** Largest winning margins; ties break on total goals, then most recent date. */
export function biggestWins(dataset: Dataset, filter: MatchFilter = {}, limit = 5): Match[] {
  const margin = (m: Match) => Math.abs(m.homeGoals - m.awayGoals);
  return filterMatches(dataset, filter)
    .filter((m) => margin(m) > 0)
    .sort((a, b) =>
      margin(b) - margin(a) ||
      (b.homeGoals + b.awayGoals) - (a.homeGoals + a.awayGoals) ||
      b.date.localeCompare(a.date),
    )
    .slice(0, limit);
}

export interface PlayerQuery {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  sortBy?: 'overall' | 'potential' | 'age';
  limit?: number;
}

/** Player search. Name, nationality, club, and position match case- and accent-insensitively. */
export function searchPlayers(dataset: Dataset, query: PlayerQuery = {}): Player[] {
  const name = query.name ? foldText(query.name) : undefined;
  const nationality = query.nationality ? foldText(query.nationality) : undefined;
  const club = query.club ? normalizeTeam(query.club).key : undefined;
  const position = query.position ? query.position.toUpperCase() : undefined;

  const players = dataset.players.filter((p) => {
    if (name && !foldText(p.name).includes(name)) return false;
    if (nationality && foldText(p.nationality) !== nationality) return false;
    if (club && !foldText(p.club).includes(club)) return false;
    if (position && !(p.position ?? '').toUpperCase().split(/\s*\/\s*|,/).includes(position)) return false;
    if (query.minOverall !== undefined && (p.overall ?? 0) < query.minOverall) return false;
    return true;
  });

  const sortBy = query.sortBy ?? 'overall';
  players.sort((a, b) => {
    if (sortBy === 'age') return (a.age ?? Infinity) - (b.age ?? Infinity);
    return (b[sortBy] ?? 0) - (a[sortBy] ?? 0) || a.name.localeCompare(b.name);
  });
  return players.slice(0, query.limit ?? 10);
}

export interface ClubSummary {
  club: string;
  players: number;
  averageOverall: number;
}

/** Player counts and average overall rating per club, for one nationality (optional). */
export function clubSummary(dataset: Dataset, nationality?: string): ClubSummary[] {
  const nat = nationality ? foldText(nationality) : undefined;
  const groups = new Map<string, { name: string; total: number; count: number; players: number }>();
  for (const p of dataset.players) {
    if (nat && foldText(p.nationality) !== nat) continue;
    const g = groups.get(p.clubKey) ?? { name: normalizeTeam(p.club).name, total: 0, count: 0, players: 0 };
    g.players++;
    if (p.overall !== undefined) { g.total += p.overall; g.count++; }
    groups.set(p.clubKey, g);
  }
  return [...groups.values()]
    .map((g) => ({ club: g.name, players: g.players, averageOverall: g.count ? g.total / g.count : 0 }))
    .sort((a, b) => b.players - a.players || a.club.localeCompare(b.club));
}

/** Team summary combining match history with squad members from the FIFA file. */
export function teamProfile(dataset: Dataset, team: string): { record: TeamRecord; players: Player[] } {
  const key = normalizeTeam(team).key;
  const players = dataset.players
    .filter((p) => foldText(p.club).includes(key) && key.length > 0)
    .sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0) || a.name.localeCompare(b.name));
  return { record: teamRecord(dataset, team), players };
}
