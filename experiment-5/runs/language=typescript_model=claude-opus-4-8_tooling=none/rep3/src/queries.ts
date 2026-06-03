/**
 * ============================================================================
 * Context: Brazilian Soccer MCP Server — Query Engine
 * ----------------------------------------------------------------------------
 * Purpose : Pure, side-effect-free query functions over the in-memory dataset.
 *           Implements the five capability areas from the spec: match search,
 *           team statistics, head-to-head, player search, competition
 *           standings, and aggregate statistical analysis. Kept free of MCP /
 *           I/O concerns so it is trivially unit-testable (see tests/) and
 *           reusable by the MCP tool handlers in server.ts.
 * Consumers: server.ts (tool handlers), tests (BDD scenarios).
 * ============================================================================
 */

import type { Match, Player, StandingRow, TeamRecord } from "./types.js";
import { looseIncludes, normalizeKey, teamMatches } from "./normalize.js";

// --- Match search ---------------------------------------------------------

export interface MatchFilter {
  /** Match if this team is involved (home or away), unless `home`/`away` set. */
  team?: string;
  /** Restrict `team` to home fixtures. */
  homeOnly?: boolean;
  /** Restrict `team` to away fixtures. */
  awayOnly?: boolean;
  /** Second team — when set with `team`, only fixtures between the two. */
  opponent?: string;
  /** Canonical or partial competition name. */
  competition?: string;
  /** Season year. */
  season?: number;
  /** Inclusive ISO date lower bound (YYYY-MM-DD). */
  fromDate?: string;
  /** Inclusive ISO date upper bound (YYYY-MM-DD). */
  toDate?: string;
}

/** Filter matches by the supplied criteria. Results are date-sorted descending. */
export function searchMatches(matches: Match[], filter: MatchFilter): Match[] {
  const result = matches.filter((m) => {
    if (filter.competition && !looseIncludes(m.competition, filter.competition)) return false;
    if (filter.season !== undefined && m.season !== filter.season) return false;
    if (filter.fromDate && (!m.date || m.date < filter.fromDate)) return false;
    if (filter.toDate && (!m.date || m.date > filter.toDate)) return false;

    if (filter.team) {
      const homeHit = teamMatches(m.homeTeam, filter.team);
      const awayHit = teamMatches(m.awayTeam, filter.team);
      if (filter.homeOnly && !homeHit) return false;
      if (filter.awayOnly && !awayHit) return false;
      if (!filter.homeOnly && !filter.awayOnly && !homeHit && !awayHit) return false;

      if (filter.opponent) {
        const oppHome = teamMatches(m.homeTeam, filter.opponent);
        const oppAway = teamMatches(m.awayTeam, filter.opponent);
        // The two named teams must be the two participants.
        const isPairing = (homeHit && oppAway) || (awayHit && oppHome);
        if (!isPairing) return false;
      }
    }
    return true;
  });

  return sortByDateDesc(result);
}

function sortByDateDesc(matches: Match[]): Match[] {
  return [...matches].sort((a, b) => {
    if (a.date && b.date) return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
    if (a.date) return -1;
    if (b.date) return 1;
    return 0;
  });
}

// --- Team statistics ------------------------------------------------------

export interface TeamStatsFilter {
  team: string;
  season?: number;
  competition?: string;
  /** "home" | "away" | "all" (default). */
  venue?: "home" | "away" | "all";
}

/**
 * Aggregate a team's win/draw/loss and goal record over the matches matching
 * the filter. Only matches with a known score contribute.
 */
export function teamStats(matches: Match[], filter: TeamStatsFilter): TeamRecord {
  const venue = filter.venue ?? "all";
  const record: TeamRecord = {
    team: filter.team,
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    points: 0,
    winRate: 0,
  };

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    if (filter.season !== undefined && m.season !== filter.season) continue;
    if (filter.competition && !looseIncludes(m.competition, filter.competition)) continue;

    const isHome = teamMatches(m.homeTeam, filter.team);
    const isAway = teamMatches(m.awayTeam, filter.team);
    if (!isHome && !isAway) continue;
    if (venue === "home" && !isHome) continue;
    if (venue === "away" && !isAway) continue;
    // If the same team somehow matches both sides, treat as home.
    const playingHome = isHome;

    const gf = playingHome ? m.homeGoals : m.awayGoals;
    const ga = playingHome ? m.awayGoals : m.homeGoals;

    record.matches += 1;
    record.goalsFor += gf;
    record.goalsAgainst += ga;
    if (gf > ga) record.wins += 1;
    else if (gf < ga) record.losses += 1;
    else record.draws += 1;
  }

  record.points = record.wins * 3 + record.draws;
  record.winRate = record.matches > 0 ? record.wins / record.matches : 0;
  return record;
}

// --- Head-to-head ---------------------------------------------------------

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

/** Compute the head-to-head record between two teams across all competitions. */
export function headToHead(matches: Match[], teamA: string, teamB: string): HeadToHead {
  const fixtures = searchMatches(matches, { team: teamA, opponent: teamB });
  const h2h: HeadToHead = {
    teamA,
    teamB,
    matches: fixtures,
    teamAWins: 0,
    teamBWins: 0,
    draws: 0,
    teamAGoals: 0,
    teamBGoals: 0,
  };

  for (const m of fixtures) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const aIsHome = teamMatches(m.homeTeam, teamA);
    const aGoals = aIsHome ? m.homeGoals : m.awayGoals;
    const bGoals = aIsHome ? m.awayGoals : m.homeGoals;
    h2h.teamAGoals += aGoals;
    h2h.teamBGoals += bGoals;
    if (aGoals > bGoals) h2h.teamAWins += 1;
    else if (aGoals < bGoals) h2h.teamBWins += 1;
    else h2h.draws += 1;
  }

  return h2h;
}

// --- Player search --------------------------------------------------------

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  /** Max results (default 50). */
  limit?: number;
}

/** Search players, sorted by Overall rating descending. */
export function searchPlayers(players: Player[], filter: PlayerFilter): Player[] {
  const limit = filter.limit ?? 50;
  const result = players.filter((p) => {
    if (filter.name && !looseIncludes(p.name, filter.name)) return false;
    if (filter.nationality && !looseIncludes(p.nationality, filter.nationality)) return false;
    if (filter.club && !looseIncludes(p.club, filter.club)) return false;
    if (filter.position && !looseIncludes(p.position, filter.position)) return false;
    if (filter.minOverall !== undefined && (p.overall ?? -1) < filter.minOverall) return false;
    return true;
  });

  result.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  return result.slice(0, limit);
}

// --- Competition standings ------------------------------------------------

/**
 * Compute a league table for a competition + season from match results.
 * Standard 3-1-0 points; ties broken by goal difference then goals for.
 */
export function standings(
  matches: Match[],
  competition: string,
  season: number
): StandingRow[] {
  const table = new Map<string, TeamRecord & { display: string }>();

  const ensure = (display: string): TeamRecord & { display: string } => {
    const key = normalizeKey(display);
    let row = table.get(key);
    if (!row) {
      row = {
        display,
        team: display,
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        points: 0,
        winRate: 0,
      };
      table.set(key, row);
    }
    return row;
  };

  for (const m of matches) {
    if (m.season !== season) continue;
    if (!looseIncludes(m.competition, competition)) continue;
    if (m.homeGoals === null || m.awayGoals === null) continue;

    const home = ensure(m.homeTeam);
    const away = ensure(m.awayTeam);

    home.matches += 1;
    away.matches += 1;
    home.goalsFor += m.homeGoals;
    home.goalsAgainst += m.awayGoals;
    away.goalsFor += m.awayGoals;
    away.goalsAgainst += m.homeGoals;

    if (m.homeGoals > m.awayGoals) {
      home.wins += 1;
      away.losses += 1;
    } else if (m.homeGoals < m.awayGoals) {
      away.wins += 1;
      home.losses += 1;
    } else {
      home.draws += 1;
      away.draws += 1;
    }
  }

  const rows = Array.from(table.values()).map((r) => {
    r.points = r.wins * 3 + r.draws;
    r.winRate = r.matches > 0 ? r.wins / r.matches : 0;
    return r;
  });

  rows.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    const gdA = a.goalsFor - a.goalsAgainst;
    const gdB = b.goalsFor - b.goalsAgainst;
    if (gdB !== gdA) return gdB - gdA;
    if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
    return a.team.localeCompare(b.team);
  });

  return rows.map((r, i) => ({
    position: i + 1,
    team: r.team,
    matches: r.matches,
    wins: r.wins,
    draws: r.draws,
    losses: r.losses,
    goalsFor: r.goalsFor,
    goalsAgainst: r.goalsAgainst,
    goalDifference: r.goalsFor - r.goalsAgainst,
    points: r.points,
    winRate: r.winRate,
  }));
}

// --- Aggregate statistics -------------------------------------------------

export interface AggregateStats {
  matches: number;
  matchesWithScore: number;
  totalGoals: number;
  goalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

/** Compute aggregate statistics over an arbitrary set of matches. */
export function aggregateStats(matches: Match[]): AggregateStats {
  let scored = 0;
  let goals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    scored += 1;
    goals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins += 1;
    else if (m.homeGoals < m.awayGoals) awayWins += 1;
    else draws += 1;
  }

  return {
    matches: matches.length,
    matchesWithScore: scored,
    totalGoals: goals,
    goalsPerMatch: scored > 0 ? goals / scored : 0,
    homeWins,
    awayWins,
    draws,
    homeWinRate: scored > 0 ? homeWins / scored : 0,
    awayWinRate: scored > 0 ? awayWins / scored : 0,
    drawRate: scored > 0 ? draws / scored : 0,
  };
}

/** Return the matches with the largest goal margin, descending. */
export function biggestWins(matches: Match[], limit = 10): Match[] {
  return matches
    .filter((m) => m.homeGoals !== null && m.awayGoals !== null)
    .map((m) => ({ m, margin: Math.abs((m.homeGoals as number) - (m.awayGoals as number)) }))
    .sort((a, b) => {
      if (b.margin !== a.margin) return b.margin - a.margin;
      const tA = (a.m.homeGoals as number) + (a.m.awayGoals as number);
      const tB = (b.m.homeGoals as number) + (b.m.awayGoals as number);
      return tB - tA;
    })
    .slice(0, limit)
    .map((x) => x.m);
}

export interface TeamRanking {
  team: string;
  value: number;
  record: TeamRecord;
}

/**
 * Rank teams by a metric over a slice of matches. Useful for "best home
 * record", "most goals scored", etc. `metric` selects the sort value.
 */
export function rankTeams(
  matches: Match[],
  opts: {
    season?: number;
    competition?: string;
    venue?: "home" | "away" | "all";
    metric: "wins" | "points" | "goalsFor" | "winRate";
    minMatches?: number;
    limit?: number;
  }
): TeamRanking[] {
  const minMatches = opts.minMatches ?? 1;
  const limit = opts.limit ?? 10;

  // Collect candidate team display names from the relevant matches.
  const teams = new Map<string, string>();
  for (const m of matches) {
    if (opts.season !== undefined && m.season !== opts.season) continue;
    if (opts.competition && !looseIncludes(m.competition, opts.competition)) continue;
    teams.set(normalizeKey(m.homeTeam), m.homeTeam);
    teams.set(normalizeKey(m.awayTeam), m.awayTeam);
  }

  const rankings: TeamRanking[] = [];
  for (const display of teams.values()) {
    const record = teamStats(matches, {
      team: display,
      season: opts.season,
      competition: opts.competition,
      venue: opts.venue ?? "all",
    });
    if (record.matches < minMatches) continue;
    const value =
      opts.metric === "wins"
        ? record.wins
        : opts.metric === "points"
        ? record.points
        : opts.metric === "goalsFor"
        ? record.goalsFor
        : record.winRate;
    rankings.push({ team: display, value, record });
  }

  rankings.sort((a, b) => b.value - a.value || b.record.wins - a.record.wins);
  return rankings.slice(0, limit);
}

/** List the distinct competitions a team has appeared in. */
export function competitionsForTeam(matches: Match[], team: string): string[] {
  const set = new Set<string>();
  for (const m of matches) {
    if (teamMatches(m.homeTeam, team) || teamMatches(m.awayTeam, team)) {
      set.add(m.competition);
    }
  }
  return Array.from(set).sort();
}
