/**
 * Brazilian Soccer MCP — Query store
 * ----------------------------------
 * Context: The `SoccerStore` is the analytical heart of the server. It holds
 * the fully-normalized matches and players in memory and exposes pure,
 * synchronous query methods that the MCP tool layer calls: match search,
 * head-to-head, team records, computed league standings, aggregate competition
 * statistics, and player search.
 *
 * Everything here is deterministic and side-effect free, which makes it
 * directly unit-testable without spinning up the MCP transport. Team names from
 * user queries are resolved through the same `normalize` canonicalization used
 * at load time, so "Sao Paulo", "São Paulo-SP" and "São Paulo" all hit the
 * same records.
 */

import type { Competition, Match, Outcome, Player } from "./types.js";
import { canonicalTeam, stripDiacritics } from "./normalize.js";

export interface MatchFilter {
  /** Team on either side (home or away) unless `venue` narrows it. */
  team?: string;
  /** Opponent team (used together with `team`). */
  opponent?: string;
  /** Restrict `team` to matches where it played home / away. */
  venue?: "home" | "away" | "either";
  competition?: string;
  season?: number;
  startDate?: string;
  endDate?: string;
  /** Only matches with a recorded score. */
  decidedOnly?: boolean;
}

export interface TeamRecord {
  teamId: string;
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
  winRate: number;
}

export interface StandingRow extends TeamRecord {
  rank: number;
  goalDiff: number;
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  sortBy?: "overall" | "potential" | "age" | "name";
  limit?: number;
}

function outcome(m: Match): Outcome | null {
  if (m.homeGoals === null || m.awayGoals === null) return null;
  if (m.homeGoals > m.awayGoals) return "home";
  if (m.homeGoals < m.awayGoals) return "away";
  return "draw";
}

export class SoccerStore {
  readonly matches: Match[];
  readonly players: Player[];

  /** team id -> set of display names seen, for resolution & listing. */
  private readonly teamDisplays = new Map<string, string>();
  private readonly competitions = new Set<Competition>();

  constructor(matches: Match[], players: Player[]) {
    this.matches = matches;
    this.players = players;
    for (const m of matches) {
      this.teamDisplays.set(m.homeTeamId, m.homeTeam);
      this.teamDisplays.set(m.awayTeamId, m.awayTeam);
      this.competitions.add(m.competition);
    }
  }

  // ---- Team name resolution ------------------------------------------------

  /**
   * Resolve a user-supplied team string to canonical team ids that exist in the
   * data. Tries: exact canonical id, then substring match against ids/displays.
   * Returns an ordered, de-duplicated list (best/most-exact first).
   */
  resolveTeams(query: string): { id: string; display: string }[] {
    const canon = canonicalTeam(query);
    const results: { id: string; display: string }[] = [];
    const seen = new Set<string>();

    if (this.teamDisplays.has(canon.id)) {
      results.push({ id: canon.id, display: this.teamDisplays.get(canon.id)! });
      seen.add(canon.id);
    }

    const needle = stripDiacritics(query).toLowerCase().trim();
    if (needle.length >= 2) {
      for (const [id, display] of this.teamDisplays) {
        if (seen.has(id)) continue;
        const hayId = id.replace(/-/g, " ");
        const hayDisplay = stripDiacritics(display).toLowerCase();
        if (hayId.includes(needle) || hayDisplay.includes(needle)) {
          results.push({ id, display });
          seen.add(id);
        }
      }
    }
    return results;
  }

  /** Resolve to a single best team id, or null if nothing matches. */
  resolveTeam(query: string): { id: string; display: string } | null {
    return this.resolveTeams(query)[0] ?? null;
  }

  // ---- Match queries -------------------------------------------------------

  findMatches(filter: MatchFilter = {}): Match[] {
    const teamId = filter.team ? this.resolveTeam(filter.team)?.id ?? "\0none" : null;
    const oppId = filter.opponent ? this.resolveTeam(filter.opponent)?.id ?? "\0none" : null;
    const compNeedle = filter.competition
      ? stripDiacritics(filter.competition).toLowerCase()
      : null;
    const venue = filter.venue ?? "either";

    const out = this.matches.filter((m) => {
      if (teamId) {
        const isHome = m.homeTeamId === teamId;
        const isAway = m.awayTeamId === teamId;
        if (venue === "home" && !isHome) return false;
        if (venue === "away" && !isAway) return false;
        if (venue === "either" && !isHome && !isAway) return false;
      }
      if (oppId) {
        if (m.homeTeamId !== oppId && m.awayTeamId !== oppId) return false;
      }
      if (compNeedle && !stripDiacritics(m.competition).toLowerCase().includes(compNeedle)) {
        return false;
      }
      if (filter.season !== undefined && m.season !== filter.season) return false;
      if (filter.startDate && (!m.date || m.date < filter.startDate)) return false;
      if (filter.endDate && (!m.date || m.date > filter.endDate)) return false;
      if (filter.decidedOnly && outcome(m) === null) return false;
      return true;
    });

    out.sort((a, b) => (a.date ?? "").localeCompare(b.date ?? ""));
    return out;
  }

  // ---- Head to head --------------------------------------------------------

  headToHead(
    teamA: string,
    teamB: string,
    filter: Omit<MatchFilter, "team" | "opponent" | "venue"> = {},
  ): {
    teamA: { id: string; display: string } | null;
    teamB: { id: string; display: string } | null;
    matches: Match[];
    aWins: number;
    bWins: number;
    draws: number;
    aGoals: number;
    bGoals: number;
  } {
    const a = this.resolveTeam(teamA);
    const b = this.resolveTeam(teamB);
    if (!a || !b) {
      return { teamA: a, teamB: b, matches: [], aWins: 0, bWins: 0, draws: 0, aGoals: 0, bGoals: 0 };
    }
    const matches = this.findMatches({ ...filter, team: a.id, opponent: b.id }).filter(
      (m) =>
        (m.homeTeamId === a.id && m.awayTeamId === b.id) ||
        (m.homeTeamId === b.id && m.awayTeamId === a.id),
    );

    let aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;
    for (const m of matches) {
      const res = outcome(m);
      if (res === null) continue;
      const aIsHome = m.homeTeamId === a.id;
      const aScore = aIsHome ? m.homeGoals! : m.awayGoals!;
      const bScore = aIsHome ? m.awayGoals! : m.homeGoals!;
      aGoals += aScore;
      bGoals += bScore;
      if (aScore > bScore) aWins++;
      else if (aScore < bScore) bWins++;
      else draws++;
    }
    return { teamA: a, teamB: b, matches, aWins, bWins, draws, aGoals, bGoals };
  }

  // ---- Team record ---------------------------------------------------------

  /**
   * Aggregate a team's results. `venue` restricts to home-only or away-only
   * games; `either` (default) counts both.
   */
  teamRecord(team: string, filter: MatchFilter = {}): TeamRecord | null {
    const resolved = this.resolveTeam(team);
    if (!resolved) return null;
    const venue = filter.venue ?? "either";
    const matches = this.findMatches({ ...filter, team: resolved.id, venue, decidedOnly: true });
    return this.recordFromMatches(resolved.id, resolved.display, matches);
  }

  private recordFromMatches(teamId: string, team: string, matches: Match[]): TeamRecord {
    let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0, played = 0;
    for (const m of matches) {
      const res = outcome(m);
      if (res === null) continue;
      played++;
      const isHome = m.homeTeamId === teamId;
      const gf = isHome ? m.homeGoals! : m.awayGoals!;
      const ga = isHome ? m.awayGoals! : m.homeGoals!;
      goalsFor += gf;
      goalsAgainst += ga;
      if (gf > ga) wins++;
      else if (gf < ga) losses++;
      else draws++;
    }
    return {
      teamId,
      team,
      played,
      wins,
      draws,
      losses,
      goalsFor,
      goalsAgainst,
      points: wins * 3 + draws,
      winRate: played ? wins / played : 0,
    };
  }

  // ---- Standings -----------------------------------------------------------

  /**
   * Compute a league table for a competition+season directly from match
   * results (3 points per win, 1 per draw). Tie-break: points, then goal
   * difference, then goals for, then name.
   */
  standings(competition: string, season: number): StandingRow[] {
    const matches = this.findMatches({ competition, season, decidedOnly: true });
    const byTeam = new Map<string, Match[]>();
    for (const m of matches) {
      (byTeam.get(m.homeTeamId) ?? byTeam.set(m.homeTeamId, []).get(m.homeTeamId)!).push(m);
      (byTeam.get(m.awayTeamId) ?? byTeam.set(m.awayTeamId, []).get(m.awayTeamId)!).push(m);
    }
    const rows: StandingRow[] = [];
    for (const [id, ms] of byTeam) {
      const rec = this.recordFromMatches(id, this.teamDisplays.get(id) ?? id, ms);
      rows.push({ ...rec, rank: 0, goalDiff: rec.goalsFor - rec.goalsAgainst });
    }
    rows.sort(
      (a, b) =>
        b.points - a.points ||
        b.goalDiff - a.goalDiff ||
        b.goalsFor - a.goalsFor ||
        a.team.localeCompare(b.team),
    );
    rows.forEach((r, i) => (r.rank = i + 1));
    return rows;
  }

  // ---- Aggregate competition statistics ------------------------------------

  competitionStats(filter: MatchFilter = {}): {
    matches: number;
    decided: number;
    totalGoals: number;
    avgGoals: number;
    homeWins: number;
    awayWins: number;
    draws: number;
    homeWinRate: number;
    biggestMargins: Match[];
  } {
    const matches = this.findMatches(filter);
    let totalGoals = 0, decided = 0, homeWins = 0, awayWins = 0, draws = 0;
    for (const m of matches) {
      const res = outcome(m);
      if (res === null) continue;
      decided++;
      totalGoals += m.homeGoals! + m.awayGoals!;
      if (res === "home") homeWins++;
      else if (res === "away") awayWins++;
      else draws++;
    }
    const biggestMargins = [...matches]
      .filter((m) => outcome(m) !== null)
      .sort(
        (a, b) =>
          Math.abs(b.homeGoals! - b.awayGoals!) - Math.abs(a.homeGoals! - a.awayGoals!) ||
          b.homeGoals! + b.awayGoals! - (a.homeGoals! + a.awayGoals!),
      )
      .slice(0, 10);
    return {
      matches: matches.length,
      decided,
      totalGoals,
      avgGoals: decided ? totalGoals / decided : 0,
      homeWins,
      awayWins,
      draws,
      homeWinRate: decided ? homeWins / decided : 0,
      biggestMargins,
    };
  }

  // ---- Player queries ------------------------------------------------------

  searchPlayers(filter: PlayerFilter = {}): Player[] {
    const name = filter.name ? stripDiacritics(filter.name).toLowerCase() : null;
    const nat = filter.nationality ? stripDiacritics(filter.nationality).toLowerCase() : null;
    const pos = filter.position ? filter.position.toUpperCase() : null;
    const clubId = filter.club ? canonicalTeam(filter.club).id : null;
    const clubNeedle = filter.club ? stripDiacritics(filter.club).toLowerCase() : null;

    let out = this.players.filter((p) => {
      if (name && !stripDiacritics(p.name).toLowerCase().includes(name)) return false;
      if (nat && !stripDiacritics(p.nationality).toLowerCase().includes(nat)) return false;
      if (pos && p.position.toUpperCase() !== pos) return false;
      if (clubNeedle) {
        const matchesId = clubId !== null && p.clubId === clubId;
        const matchesName = stripDiacritics(p.club).toLowerCase().includes(clubNeedle);
        if (!matchesId && !matchesName) return false;
      }
      if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) return false;
      return true;
    });

    const sortBy = filter.sortBy ?? "overall";
    out = out.sort((a, b) => {
      switch (sortBy) {
        case "name":
          return a.name.localeCompare(b.name);
        case "age":
          return (a.age ?? 999) - (b.age ?? 999);
        case "potential":
          return (b.potential ?? 0) - (a.potential ?? 0);
        case "overall":
        default:
          return (b.overall ?? 0) - (a.overall ?? 0);
      }
    });

    return filter.limit ? out.slice(0, filter.limit) : out;
  }

  /** Group a set of players by their canonical club, with average rating. */
  clubBreakdown(players: Player[]): { club: string; count: number; avgOverall: number }[] {
    const byClub = new Map<string, { sum: number; count: number; label: string }>();
    for (const p of players) {
      if (!p.club) continue;
      const entry = byClub.get(p.club) ?? { sum: 0, count: 0, label: p.club };
      entry.sum += p.overall ?? 0;
      entry.count++;
      byClub.set(p.club, entry);
    }
    return [...byClub.values()]
      .map((e) => ({ club: e.label, count: e.count, avgOverall: e.count ? e.sum / e.count : 0 }))
      .sort((a, b) => b.count - a.count || b.avgOverall - a.avgOverall);
  }

  // ---- Introspection helpers ----------------------------------------------

  listCompetitions(): Competition[] {
    return [...this.competitions].sort();
  }

  seasonsFor(competition: string): number[] {
    const compNeedle = stripDiacritics(competition).toLowerCase();
    const seasons = new Set<number>();
    for (const m of this.matches) {
      if (m.season === null) continue;
      if (stripDiacritics(m.competition).toLowerCase().includes(compNeedle)) {
        seasons.add(m.season);
      }
    }
    return [...seasons].sort((a, b) => a - b);
  }

  teamCount(): number {
    return this.teamDisplays.size;
  }
}
