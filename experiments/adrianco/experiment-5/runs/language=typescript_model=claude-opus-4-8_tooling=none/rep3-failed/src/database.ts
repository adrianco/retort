/**
 * ============================================================================
 * Context Block
 * ----------------------------------------------------------------------------
 * File:    src/database.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: The in-memory query engine ("knowledge graph") over the normalized
 *          matches and players. Exposes the analytical operations the MCP tools
 *          and the BDD tests depend on: match search, team records, head-to-head
 *          comparisons, computed league standings, league-wide statistics and
 *          player search.
 *
 * Why in-memory (not Neo4j): the datasets are small (~24k matches, ~18k
 *          players) and fit comfortably in memory, giving sub-millisecond
 *          queries with zero external dependencies — well within the spec's
 *          "< 2s simple / < 5s aggregate" performance budget and making the
 *          server trivially runnable for the demo/benchmark use case.
 *
 * Deduplication: several sources overlap (e.g. the historical and modern
 *          Brasileirão files cover 2012-2019). `searchMatches` de-duplicates
 *          identical matches across sources; `standings`/`teamStats` select a
 *          single best source per (competition, season) so aggregates are not
 *          double-counted.
 * ============================================================================
 */

import type {
  Match,
  Player,
  StandingRow,
  TeamRecord,
} from './types.js';
import { teamKey, teamBaseKey, teamKeyMatches, normalizeText } from './normalize.js';

export interface MatchQuery {
  /** A team that must be involved (either home or away). */
  team?: string;
  /** A second team; combined with `team` this finds head-to-head fixtures. */
  opponent?: string;
  competition?: string;
  season?: number;
  /** Inclusive ISO lower bound on date. */
  dateFrom?: string;
  /** Inclusive ISO upper bound on date. */
  dateTo?: string;
  /** Restrict `team` to matches it played at home / away. */
  venue?: 'home' | 'away';
  limit?: number;
}

export interface PlayerQuery {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  sortBy?: 'overall' | 'potential' | 'age' | 'name';
  limit?: number;
}

function competitionMatches(matchComp: string, query: string): boolean {
  const a = normalizeText(matchComp);
  const b = normalizeText(query);
  if (!b) return true;
  // Accept common aliases.
  if ((b === 'serie a' || b === 'brasileirao') &&
      (a === 'brasileirao' || a === 'serie a')) {
    return true;
  }
  if ((b === 'libertadores') && a.includes('libertadores')) return true;
  return a.includes(b) || b.includes(a);
}

/** Does a team key match the given side of a match (state-aware base match)? */
function sideMatches(matchKey: string, queryKey: string): boolean {
  return teamKeyMatches(matchKey, queryKey);
}

export class SoccerDatabase {
  readonly matches: Match[];
  readonly players: Player[];
  readonly sourceCounts: Record<string, number>;

  constructor(data: {
    matches: Match[];
    players: Player[];
    sourceCounts?: Record<string, number>;
  }) {
    this.matches = data.matches;
    this.players = data.players;
    this.sourceCounts = data.sourceCounts ?? {};
  }

  // --------------------------------------------------------------------------
  // Diagnostics / metadata
  // --------------------------------------------------------------------------

  summary() {
    const seasons = new Set<number>();
    const competitions = new Map<string, number>();
    for (const m of this.matches) {
      seasons.add(m.season);
      competitions.set(m.competition, (competitions.get(m.competition) ?? 0) + 1);
    }
    return {
      totalMatches: this.matches.length,
      totalPlayers: this.players.length,
      seasonRange: seasons.size
        ? [Math.min(...seasons), Math.max(...seasons)]
        : [],
      competitions: [...competitions.entries()]
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count),
      sourceCounts: this.sourceCounts,
    };
  }

  listCompetitions() {
    const byComp = new Map<string, { seasons: Set<number>; count: number }>();
    for (const m of this.matches) {
      const entry = byComp.get(m.competition) ?? { seasons: new Set(), count: 0 };
      entry.seasons.add(m.season);
      entry.count += 1;
      byComp.set(m.competition, entry);
    }
    return [...byComp.entries()]
      .map(([name, { seasons, count }]) => ({
        name,
        matches: count,
        seasons: [...seasons].sort((a, b) => a - b),
        firstSeason: Math.min(...seasons),
        lastSeason: Math.max(...seasons),
      }))
      .sort((a, b) => b.matches - a.matches);
  }

  // --------------------------------------------------------------------------
  // Match queries
  // --------------------------------------------------------------------------

  /** Raw filtered match search with cross-source de-duplication. */
  searchMatches(query: MatchQuery): Match[] {
    const teamK = query.team ? teamKey(query.team) : undefined;
    const oppK = query.opponent ? teamKey(query.opponent) : undefined;

    const filtered = this.matches.filter((m) => {
      if (query.competition && !competitionMatches(m.competition, query.competition)) {
        return false;
      }
      if (query.season != null && m.season !== query.season) return false;
      if (query.dateFrom && (!m.date || m.date < query.dateFrom)) return false;
      if (query.dateTo && (!m.date || m.date > query.dateTo)) return false;

      if (teamK) {
        const home = sideMatches(m.homeKey, teamK);
        const away = sideMatches(m.awayKey, teamK);
        if (query.venue === 'home' && !home) return false;
        if (query.venue === 'away' && !away) return false;
        if (!query.venue && !home && !away) return false;
      }
      if (oppK) {
        const involved = sideMatches(m.homeKey, oppK) || sideMatches(m.awayKey, oppK);
        if (!involved) return false;
      }
      return true;
    });

    const deduped = dedupeMatches(filtered);
    deduped.sort(byDateDesc);
    return typeof query.limit === 'number' ? deduped.slice(0, query.limit) : deduped;
  }

  /** Head-to-head record between two teams, optionally within a competition. */
  headToHead(team1: string, team2: string, competition?: string) {
    const k1 = teamKey(team1);
    const k2 = teamKey(team2);
    const matches = dedupeMatches(
      this.matches.filter((m) => {
        if (competition && !competitionMatches(m.competition, competition)) return false;
        const home1 = sideMatches(m.homeKey, k1);
        const away1 = sideMatches(m.awayKey, k1);
        const home2 = sideMatches(m.homeKey, k2);
        const away2 = sideMatches(m.awayKey, k2);
        return (home1 && away2) || (home2 && away1);
      }),
    );

    let team1Wins = 0;
    let team2Wins = 0;
    let draws = 0;
    let team1Goals = 0;
    let team2Goals = 0;
    for (const m of matches) {
      const t1Home = sideMatches(m.homeKey, k1);
      const t1For = t1Home ? m.homeGoal : m.awayGoal;
      const t2For = t1Home ? m.awayGoal : m.homeGoal;
      team1Goals += t1For;
      team2Goals += t2For;
      if (t1For > t2For) team1Wins += 1;
      else if (t2For > t1For) team2Wins += 1;
      else draws += 1;
    }

    matches.sort(byDateDesc);
    return {
      team1,
      team2,
      competition: competition ?? 'all competitions',
      totalMatches: matches.length,
      team1Wins,
      team2Wins,
      draws,
      team1Goals,
      team2Goals,
      matches,
    };
  }

  // --------------------------------------------------------------------------
  // Team statistics
  // --------------------------------------------------------------------------

  teamStats(
    team: string,
    opts: { season?: number; competition?: string; venue?: 'home' | 'away' } = {},
  ): TeamRecord {
    const k = teamKey(team);
    // Use a single best source per (competition, season) to avoid double counts.
    const pool = this.dedupeForAggregates(opts.competition, opts.season);

    let matches = 0;
    let wins = 0;
    let draws = 0;
    let losses = 0;
    let goalsFor = 0;
    let goalsAgainst = 0;

    for (const m of pool) {
      const home = sideMatches(m.homeKey, k);
      const away = sideMatches(m.awayKey, k);
      if (!home && !away) continue;
      if (opts.venue === 'home' && !home) continue;
      if (opts.venue === 'away' && !away) continue;

      const isHome = home;
      const gf = isHome ? m.homeGoal : m.awayGoal;
      const ga = isHome ? m.awayGoal : m.homeGoal;
      matches += 1;
      goalsFor += gf;
      goalsAgainst += ga;
      if (gf > ga) wins += 1;
      else if (gf < ga) losses += 1;
      else draws += 1;
    }

    return {
      team,
      matches,
      wins,
      draws,
      losses,
      goalsFor,
      goalsAgainst,
      points: wins * 3 + draws,
      winRate: matches ? round1((wins / matches) * 100) : 0,
    };
  }

  // --------------------------------------------------------------------------
  // Competition standings
  // --------------------------------------------------------------------------

  /** Compute a league table for a competition/season from match results. */
  standings(competition: string, season: number): StandingRow[] {
    const pool = this.dedupeForAggregates(competition, season);
    const table = new Map<string, TeamRecord & { goalDifference: number }>();

    const ensure = (display: string, key: string) => {
      let row = table.get(key);
      if (!row) {
        row = {
          team: display,
          matches: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          points: 0,
          winRate: 0,
          goalDifference: 0,
        };
        table.set(key, row);
      }
      return row;
    };

    for (const m of pool) {
      const home = ensure(m.homeTeam, m.homeKey);
      const away = ensure(m.awayTeam, m.awayKey);
      home.matches += 1;
      away.matches += 1;
      home.goalsFor += m.homeGoal;
      home.goalsAgainst += m.awayGoal;
      away.goalsFor += m.awayGoal;
      away.goalsAgainst += m.homeGoal;
      if (m.homeGoal > m.awayGoal) {
        home.wins += 1;
        away.losses += 1;
      } else if (m.homeGoal < m.awayGoal) {
        away.wins += 1;
        home.losses += 1;
      } else {
        home.draws += 1;
        away.draws += 1;
      }
    }

    const rows = [...table.values()].map((r) => {
      r.points = r.wins * 3 + r.draws;
      r.goalDifference = r.goalsFor - r.goalsAgainst;
      r.winRate = r.matches ? round1((r.wins / r.matches) * 100) : 0;
      return r;
    });

    rows.sort(
      (a, b) =>
        b.points - a.points ||
        b.goalDifference - a.goalDifference ||
        b.goalsFor - a.goalsFor ||
        a.team.localeCompare(b.team),
    );

    return rows.map((r, i) => ({ ...r, position: i + 1 }));
  }

  // --------------------------------------------------------------------------
  // League-wide statistics
  // --------------------------------------------------------------------------

  leagueStats(opts: { competition?: string; season?: number } = {}) {
    const pool = this.dedupeForAggregates(opts.competition, opts.season);
    let totalGoals = 0;
    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;
    for (const m of pool) {
      totalGoals += m.homeGoal + m.awayGoal;
      if (m.homeGoal > m.awayGoal) homeWins += 1;
      else if (m.homeGoal < m.awayGoal) awayWins += 1;
      else draws += 1;
    }
    const n = pool.length;
    return {
      competition: opts.competition ?? 'all competitions',
      season: opts.season ?? 'all seasons',
      matches: n,
      totalGoals,
      avgGoalsPerMatch: n ? round2(totalGoals / n) : 0,
      homeWins,
      awayWins,
      draws,
      homeWinRate: n ? round1((homeWins / n) * 100) : 0,
      awayWinRate: n ? round1((awayWins / n) * 100) : 0,
      drawRate: n ? round1((draws / n) * 100) : 0,
    };
  }

  /** Largest goal-margin victories, optionally filtered. */
  biggestWins(opts: { competition?: string; season?: number; limit?: number } = {}) {
    const pool = this.dedupeForAggregates(opts.competition, opts.season);
    const sorted = [...pool].sort((a, b) => {
      const ma = Math.abs(a.homeGoal - a.awayGoal);
      const mb = Math.abs(b.homeGoal - b.awayGoal);
      return mb - ma || b.homeGoal + b.awayGoal - (a.homeGoal + a.awayGoal);
    });
    return sorted.slice(0, opts.limit ?? 10);
  }

  // --------------------------------------------------------------------------
  // Player queries
  // --------------------------------------------------------------------------

  searchPlayers(query: PlayerQuery): Player[] {
    const nameQ = query.name ? normalizeText(query.name) : undefined;
    const natQ = query.nationality ? normalizeText(query.nationality) : undefined;
    const clubQ = query.club ? teamKey(query.club) : undefined;
    const posQ = query.position ? normalizeText(query.position) : undefined;

    let result = this.players.filter((p) => {
      if (nameQ && !normalizeText(p.name).includes(nameQ)) return false;
      if (natQ && normalizeText(p.nationality) !== natQ &&
          !normalizeText(p.nationality).includes(natQ)) {
        return false;
      }
      if (clubQ && !p.clubKey.includes(clubQ)) return false;
      if (posQ && normalizeText(p.position) !== posQ) return false;
      if (query.minOverall != null && (p.overall ?? 0) < query.minOverall) return false;
      return true;
    });

    const sortBy = query.sortBy ?? 'overall';
    result = result.sort((a, b) => {
      switch (sortBy) {
        case 'potential':
          return (b.potential ?? 0) - (a.potential ?? 0);
        case 'age':
          return (a.age ?? 999) - (b.age ?? 999);
        case 'name':
          return a.name.localeCompare(b.name);
        case 'overall':
        default:
          return (b.overall ?? 0) - (a.overall ?? 0);
      }
    });

    return typeof query.limit === 'number' ? result.slice(0, query.limit) : result;
  }

  /** Aggregate Brazilian (or any-nationality) players by club. */
  playersByClub(opts: { nationality?: string; minPlayers?: number } = {}) {
    const natQ = opts.nationality ? normalizeText(opts.nationality) : undefined;
    const byClub = new Map<string, { club: string; ratings: number[] }>();
    for (const p of this.players) {
      if (!p.club) continue;
      if (natQ && normalizeText(p.nationality) !== natQ) continue;
      const entry = byClub.get(p.clubKey) ?? { club: p.club, ratings: [] };
      if (p.overall != null) entry.ratings.push(p.overall);
      byClub.set(p.clubKey, entry);
    }
    return [...byClub.values()]
      .map((e) => ({
        club: e.club,
        players: e.ratings.length,
        avgRating: e.ratings.length
          ? round1(e.ratings.reduce((s, r) => s + r, 0) / e.ratings.length)
          : 0,
      }))
      .filter((e) => e.players >= (opts.minPlayers ?? 1))
      .sort((a, b) => b.players - a.players || b.avgRating - a.avgRating);
  }

  // --------------------------------------------------------------------------
  // Internal helpers
  // --------------------------------------------------------------------------

  /**
   * For aggregate calculations (standings, stats), choose a single source per
   * (competition, season) so overlapping datasets are not double-counted. The
   * source with the most matches for a slice is treated as the most complete.
   */
  private dedupeForAggregates(competition?: string, season?: number): Match[] {
    const filtered = this.matches.filter((m) => {
      if (competition && !competitionMatches(m.competition, competition)) return false;
      if (season != null && m.season !== season) return false;
      return true;
    });

    // Group by competition+season, then keep only the dominant source.
    const groups = new Map<string, Map<string, Match[]>>();
    for (const m of filtered) {
      const gkey = `${m.competition}__${m.season}`;
      const bySource = groups.get(gkey) ?? new Map<string, Match[]>();
      const arr = bySource.get(m.source) ?? [];
      arr.push(m);
      bySource.set(m.source, arr);
      groups.set(gkey, bySource);
    }

    const out: Match[] = [];
    for (const bySource of groups.values()) {
      let best: Match[] = [];
      for (const arr of bySource.values()) {
        if (arr.length > best.length) best = arr;
      }
      out.push(...best);
    }
    return out;
  }
}

// ----------------------------------------------------------------------------
// Module-local helpers
// ----------------------------------------------------------------------------

function byDateDesc(a: Match, b: Match): number {
  const da = a.date ?? '';
  const db = b.date ?? '';
  if (da === db) return 0;
  return da < db ? 1 : -1;
}

/** Remove cross-source duplicates of the same fixture. */
function dedupeMatches(matches: Match[]): Match[] {
  const seen = new Set<string>();
  const out: Match[] = [];
  for (const m of matches) {
    // Use base keys so the same fixture recorded as "Palmeiras-SP" in one
    // source and "Palmeiras" in another collapses to a single entry.
    const key = [
      normalizeText(m.competition),
      m.season,
      m.date ?? '',
      teamBaseKey(m.homeKey),
      teamBaseKey(m.awayKey),
      m.homeGoal,
      m.awayGoal,
    ].join('|');
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(m);
  }
  return out;
}

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}
function round2(n: number): number {
  return Math.round(n * 100) / 100;
}
