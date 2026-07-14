/**
 * Context
 * -------
 * The query engine. Pure functions that take a `DataStore` plus query
 * parameters and return structured results (no formatting). These power both
 * the MCP tools (via `format.ts`) and the BDD test suite directly, so they are
 * deliberately framework-agnostic and side-effect free.
 *
 * Covers the five capability areas from the spec: match queries, team queries,
 * player queries, competition standings, and statistical analysis. Team name
 * matching is accent-insensitive and tolerant of state/country suffixes via
 * `normalize.ts`.
 */

import type { DataStore } from "./dataStore.js";
import type { Competition, Match, Player, Record } from "./types.js";
import { canonicalKey, stripAccents, teamMatches } from "./normalize.js";

const COMPETITION_ALIASES: Array<[RegExp, Competition]> = [
  [/serie a|s[ée]rie a|brasileir[ãa]o|brasileirao/i, "Brasileirão Série A"],
  [/serie b|s[ée]rie b/i, "Brasileirão Série B"],
  [/serie c|s[ée]rie c/i, "Brasileirão Série C"],
  [/copa do brasil|cup/i, "Copa do Brasil"],
  [/libertadores/i, "Copa Libertadores"],
];

/** Resolve a free-text competition name to a canonical Competition. */
export function resolveCompetition(name?: string | null): Competition | null {
  if (!name) return null;
  for (const [re, comp] of COMPETITION_ALIASES) {
    if (re.test(name)) return comp;
  }
  return null;
}

export interface MatchFilter {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  /** Find matches between these two teams (either may be home). */
  opponent?: string;
  competition?: string;
  season?: number;
  startDate?: string;
  endDate?: string;
  limit?: number;
}

/** Sort matches by date descending (most recent first); nulls sort last. */
function byDateDesc(a: Match, b: Match): number {
  if (a.date && b.date) return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
  if (a.date) return -1;
  if (b.date) return 1;
  return 0;
}

/** Find matches by any combination of team / competition / season / date. */
export function findMatches(store: DataStore, filter: MatchFilter): Match[] {
  const comp = resolveCompetition(filter.competition);
  let results = store.matches.filter((m) => {
    if (comp && m.competition !== comp) return false;
    if (filter.season != null && m.season !== filter.season) return false;
    if (filter.startDate && (!m.date || m.date < filter.startDate)) return false;
    if (filter.endDate && (!m.date || m.date > filter.endDate)) return false;

    if (filter.team && !(teamMatches(m.homeTeamRaw, filter.team) || teamMatches(m.awayTeamRaw, filter.team)))
      return false;
    if (filter.homeTeam && !teamMatches(m.homeTeamRaw, filter.homeTeam)) return false;
    if (filter.awayTeam && !teamMatches(m.awayTeamRaw, filter.awayTeam)) return false;

    // opponent + team together => head to head between the two.
    if (filter.opponent) {
      const t = filter.team ?? filter.homeTeam ?? filter.awayTeam;
      if (!t) return false;
      const aIsT = teamMatches(m.homeTeamRaw, t) || teamMatches(m.awayTeamRaw, t);
      const aIsOpp =
        teamMatches(m.homeTeamRaw, filter.opponent) || teamMatches(m.awayTeamRaw, filter.opponent);
      const oneHomeOneAway =
        (teamMatches(m.homeTeamRaw, t) && teamMatches(m.awayTeamRaw, filter.opponent)) ||
        (teamMatches(m.homeTeamRaw, filter.opponent) && teamMatches(m.awayTeamRaw, t));
      if (!(aIsT && aIsOpp && oneHomeOneAway)) return false;
    }
    return true;
  });

  results = results.sort(byDateDesc);
  if (filter.limit != null) results = results.slice(0, filter.limit);
  return results;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: Match[];
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
}

/** Head-to-head record between two teams across all competitions. */
export function headToHead(store: DataStore, teamA: string, teamB: string): HeadToHead {
  const matches = findMatches(store, { team: teamA, opponent: teamB }).filter(
    (m) => m.homeGoal != null && m.awayGoal != null,
  );
  let teamAWins = 0;
  let teamBWins = 0;
  let draws = 0;
  let teamAGoals = 0;
  let teamBGoals = 0;

  for (const m of matches) {
    const aIsHome = teamMatches(m.homeTeamRaw, teamA);
    const aGoals = aIsHome ? m.homeGoal! : m.awayGoal!;
    const bGoals = aIsHome ? m.awayGoal! : m.homeGoal!;
    teamAGoals += aGoals;
    teamBGoals += bGoals;
    if (aGoals > bGoals) teamAWins++;
    else if (bGoals > aGoals) teamBWins++;
    else draws++;
  }

  return {
    teamA: displayName(matches, teamA, "A") ?? teamA,
    teamB: displayName(matches, teamB, "B") ?? teamB,
    matches,
    teamAWins,
    teamBWins,
    draws,
    teamAGoals,
    teamBGoals,
  };
}

function displayName(matches: Match[], query: string, _which: "A" | "B"): string | null {
  for (const m of matches) {
    if (teamMatches(m.homeTeamRaw, query)) return m.homeTeam;
    if (teamMatches(m.awayTeamRaw, query)) return m.awayTeam;
  }
  return null;
}

export interface TeamStats {
  team: string;
  competition: Competition | null;
  season: number | null;
  overall: Record;
  home: Record;
  away: Record;
  winRate: number;
}

function emptyRecord(): Record {
  return { played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
}

function applyResult(rec: Record, gf: number, ga: number): void {
  rec.played++;
  rec.goalsFor += gf;
  rec.goalsAgainst += ga;
  if (gf > ga) rec.wins++;
  else if (gf < ga) rec.losses++;
  else rec.draws++;
}

/** Compute a team's win/draw/loss + goals record (optionally scoped). */
export function teamStats(
  store: DataStore,
  team: string,
  opts: { competition?: string; season?: number } = {},
): TeamStats {
  const comp = resolveCompetition(opts.competition);
  const overall = emptyRecord();
  const home = emptyRecord();
  const away = emptyRecord();
  let resolvedName = team;

  for (const m of store.matches) {
    if (comp && m.competition !== comp) continue;
    if (opts.season != null && m.season !== opts.season) continue;
    if (m.homeGoal == null || m.awayGoal == null) continue;

    const isHome = teamMatches(m.homeTeamRaw, team);
    const isAway = teamMatches(m.awayTeamRaw, team);
    if (!isHome && !isAway) continue;

    if (isHome) {
      resolvedName = m.homeTeam;
      applyResult(overall, m.homeGoal, m.awayGoal);
      applyResult(home, m.homeGoal, m.awayGoal);
    } else {
      resolvedName = m.awayTeam;
      applyResult(overall, m.awayGoal, m.homeGoal);
      applyResult(away, m.awayGoal, m.homeGoal);
    }
  }

  const winRate = overall.played > 0 ? (overall.wins / overall.played) * 100 : 0;
  return {
    team: resolvedName,
    competition: comp,
    season: opts.season ?? null,
    overall,
    home,
    away,
    winRate,
  };
}

export interface StandingRow {
  team: string;
  points: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
}

/**
 * Compute a league table for a competition + season from match results.
 * 3 points per win, 1 per draw. Sorted by points, then GD, then goals for.
 */
export function standings(
  store: DataStore,
  competition: string,
  season: number,
): StandingRow[] {
  const comp = resolveCompetition(competition);
  const table = new Map<string, StandingRow>();

  const get = (name: string): StandingRow => {
    const key = canonicalKey(name);
    let row = table.get(key);
    if (!row) {
      row = {
        team: name,
        points: 0,
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDifference: 0,
      };
      table.set(key, row);
    }
    return row;
  };

  for (const m of store.matches) {
    if (comp && m.competition !== comp) continue;
    if (m.season !== season) continue;
    if (m.homeGoal == null || m.awayGoal == null) continue;

    const h = get(m.homeTeam);
    const a = get(m.awayTeam);
    h.played++;
    a.played++;
    h.goalsFor += m.homeGoal;
    h.goalsAgainst += m.awayGoal;
    a.goalsFor += m.awayGoal;
    a.goalsAgainst += m.homeGoal;
    if (m.homeGoal > m.awayGoal) {
      h.wins++;
      h.points += 3;
      a.losses++;
    } else if (m.homeGoal < m.awayGoal) {
      a.wins++;
      a.points += 3;
      h.losses++;
    } else {
      h.draws++;
      a.draws++;
      h.points++;
      a.points++;
    }
  }

  const rows = [...table.values()];
  for (const r of rows) r.goalDifference = r.goalsFor - r.goalsAgainst;
  rows.sort(
    (x, y) =>
      y.points - x.points ||
      y.goalDifference - x.goalDifference ||
      y.goalsFor - x.goalsFor ||
      x.team.localeCompare(y.team),
  );
  return rows;
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

/** Search FIFA players by name / nationality / club / position. */
export function findPlayers(store: DataStore, filter: PlayerFilter): Player[] {
  const nameKey = filter.name ? stripAccents(filter.name) : null;
  const natKey = filter.nationality ? stripAccents(filter.nationality) : null;
  const clubKey = filter.club ? stripAccents(filter.club) : null;
  const posKey = filter.position ? stripAccents(filter.position) : null;

  let results = store.players.filter((p) => {
    if (nameKey && !stripAccents(p.name).includes(nameKey)) return false;
    if (natKey && stripAccents(p.nationality) !== natKey && !stripAccents(p.nationality).includes(natKey))
      return false;
    if (clubKey && !stripAccents(p.club).includes(clubKey)) return false;
    if (posKey && stripAccents(p.position) !== posKey) return false;
    if (filter.minOverall != null && (p.overall ?? 0) < filter.minOverall) return false;
    return true;
  });

  results = results.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  if (filter.limit != null) results = results.slice(0, filter.limit);
  return results;
}

export interface CompetitionStats {
  competition: Competition | null;
  season: number | null;
  totalMatches: number;
  matchesWithScores: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
}

/** Aggregate statistical summary for a competition/season (or everything). */
export function competitionStats(
  store: DataStore,
  opts: { competition?: string; season?: number } = {},
): CompetitionStats {
  const comp = resolveCompetition(opts.competition);
  let total = 0;
  let scored = 0;
  let goals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;

  for (const m of store.matches) {
    if (comp && m.competition !== comp) continue;
    if (opts.season != null && m.season !== opts.season) continue;
    total++;
    if (m.homeGoal == null || m.awayGoal == null) continue;
    scored++;
    goals += m.homeGoal + m.awayGoal;
    if (m.homeGoal > m.awayGoal) homeWins++;
    else if (m.homeGoal < m.awayGoal) awayWins++;
    else draws++;
  }

  return {
    competition: comp,
    season: opts.season ?? null,
    totalMatches: total,
    matchesWithScores: scored,
    totalGoals: goals,
    averageGoalsPerMatch: scored > 0 ? goals / scored : 0,
    homeWins,
    awayWins,
    draws,
    homeWinRate: scored > 0 ? (homeWins / scored) * 100 : 0,
  };
}

export interface BigWin {
  match: Match;
  margin: number;
}

/** Largest goal-margin victories, optionally scoped to competition/season. */
export function biggestWins(
  store: DataStore,
  opts: { competition?: string; season?: number; limit?: number } = {},
): BigWin[] {
  const comp = resolveCompetition(opts.competition);
  const wins: BigWin[] = [];
  for (const m of store.matches) {
    if (comp && m.competition !== comp) continue;
    if (opts.season != null && m.season !== opts.season) continue;
    if (m.homeGoal == null || m.awayGoal == null) continue;
    wins.push({ match: m, margin: Math.abs(m.homeGoal - m.awayGoal) });
  }
  wins.sort(
    (a, b) =>
      b.margin - a.margin ||
      b.match.homeGoal! + b.match.awayGoal! - (a.match.homeGoal! + a.match.awayGoal!),
  );
  return wins.slice(0, opts.limit ?? 10);
}

/** Total goals scored by each team in a competition/season, sorted desc. */
export function topScoringTeams(
  store: DataStore,
  opts: { competition?: string; season?: number; limit?: number } = {},
): Array<{ team: string; goals: number }> {
  const comp = resolveCompetition(opts.competition);
  const tally = new Map<string, { team: string; goals: number }>();
  const add = (name: string, goals: number) => {
    const key = canonicalKey(name);
    const cur = tally.get(key) ?? { team: name, goals: 0 };
    cur.goals += goals;
    tally.set(key, cur);
  };
  for (const m of store.matches) {
    if (comp && m.competition !== comp) continue;
    if (opts.season != null && m.season !== opts.season) continue;
    if (m.homeGoal == null || m.awayGoal == null) continue;
    add(m.homeTeam, m.homeGoal);
    add(m.awayTeam, m.awayGoal);
  }
  return [...tally.values()].sort((a, b) => b.goals - a.goals).slice(0, opts.limit ?? 10);
}

/** Which competitions a team has appeared in (with match counts). */
export function teamCompetitions(
  store: DataStore,
  team: string,
): Array<{ competition: Competition; matches: number }> {
  const counts = new Map<Competition, number>();
  for (const m of store.matches) {
    if (teamMatches(m.homeTeamRaw, team) || teamMatches(m.awayTeamRaw, team)) {
      counts.set(m.competition, (counts.get(m.competition) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([competition, matches]) => ({ competition, matches }))
    .sort((a, b) => b.matches - a.matches);
}
