/**
 * In-memory query engine over the combined Brazilian Soccer corpus.
 *
 * `SoccerDatabase` wraps the loaded matches and players and exposes the query
 * primitives the MCP tools build on: finding matches by team/competition/season/
 * date, head-to-head records, team aggregates, league standings computed from
 * results, descriptive statistics and player search. All team matching goes
 * through the normalization layer so naming variations resolve consistently.
 */

import { canonicalMatches, type Corpus } from "./loader.js";
import type { Match, Player, TeamRecord } from "./types.js";
import { teamMatches, normalizeName, normalizeTeamName } from "./normalize.js";

export interface MatchQuery {
  /** A team that must be involved (home or away). */
  team?: string;
  /** A second team; when set, results are restricted to games between the two. */
  team2?: string;
  /** Restrict to matches where this team played at home. */
  homeTeam?: string;
  /** Restrict to matches where this team played away. */
  awayTeam?: string;
  /** Competition name or fragment (e.g. "Libertadores"). */
  competition?: string;
  season?: number;
  from?: Date;
  to?: Date;
  limit?: number;
}

export interface TeamRecordOptions {
  season?: number;
  competition?: string;
  /** Restrict the record to home or away games. */
  venue?: "home" | "away" | "all";
}

export interface StatsQuery {
  competition?: string;
  season?: number;
  team?: string;
}

export interface Statistics {
  totalMatches: number;
  totalGoals: number;
  averageGoals: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

export interface PlayerQuery {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

export interface ClubGroup {
  club: string;
  count: number;
  averageOverall: number;
}

export class SoccerDatabase {
  readonly matches: Match[];
  readonly players: Player[];
  /** Normalized keys of clubs that appear in domestic Brazilian competitions. */
  private readonly domesticTeamKeys: Set<string>;

  constructor(corpus: Corpus) {
    // Collapse overlapping datasets to one canonical source per
    // (competition, season) so standings and statistics are not double-counted.
    this.matches = canonicalMatches(corpus.matches);
    this.players = corpus.players;
    this.domesticTeamKeys = new Set();
    for (const m of this.matches) {
      if (
        m.competition.startsWith("Brasileirão") ||
        m.competition === "Copa do Brasil"
      ) {
        this.domesticTeamKeys.add(m.homeKey);
        this.domesticTeamKeys.add(m.awayKey);
      }
    }
  }

  /** Does a match involve the given team on either side? */
  private involves(m: Match, query: string): boolean {
    return teamMatches(m.homeTeam, query) || teamMatches(m.awayTeam, query);
  }

  /** Find matches matching all supplied criteria, sorted most-recent first. */
  findMatches(q: MatchQuery): Match[] {
    const compKey = q.competition ? normalizeName(q.competition) : null;

    let result = this.matches.filter((m) => {
      if (q.team && !this.involves(m, q.team)) return false;
      if (q.team2) {
        // Both teams must be present (in either arrangement).
        if (!this.involves(m, q.team2)) return false;
      }
      if (q.homeTeam && !teamMatches(m.homeTeam, q.homeTeam)) return false;
      if (q.awayTeam && !teamMatches(m.awayTeam, q.awayTeam)) return false;
      if (compKey && !normalizeName(m.competition).includes(compKey)) return false;
      if (q.season != null && m.season !== q.season) return false;
      if (q.from && (!m.date || m.date < q.from)) return false;
      if (q.to && (!m.date || m.date > q.to)) return false;
      return true;
    });

    result = result.sort((a, b) => {
      const ta = a.date ? a.date.getTime() : 0;
      const tb = b.date ? b.date.getTime() : 0;
      return tb - ta;
    });

    return q.limit != null ? result.slice(0, q.limit) : result;
  }

  /** Head-to-head record between two teams across all matches. */
  headToHead(teamA: string, teamB: string) {
    const games = this.findMatches({ team: teamA, team2: teamB });
    let teamAWins = 0;
    let teamBWins = 0;
    let draws = 0;
    for (const m of games) {
      const aHome = teamMatches(m.homeTeam, teamA);
      const aGoals = aHome ? m.homeGoals : m.awayGoals;
      const bGoals = aHome ? m.awayGoals : m.homeGoals;
      if (aGoals > bGoals) teamAWins++;
      else if (bGoals > aGoals) teamBWins++;
      else draws++;
    }
    return { teamA, teamB, matches: games.length, teamAWins, teamBWins, draws, games };
  }

  /** Aggregate a single team's record over a filtered set of matches. */
  teamRecord(team: string, opts: TeamRecordOptions = {}): TeamRecord {
    const venue = opts.venue ?? "all";
    const rec: TeamRecord = {
      team,
      matches: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goalsFor: 0,
      goalsAgainst: 0,
      points: 0,
    };
    const compKey = opts.competition ? normalizeName(opts.competition) : null;

    for (const m of this.matches) {
      if (opts.season != null && m.season !== opts.season) continue;
      if (compKey && !normalizeName(m.competition).includes(compKey)) continue;

      const isHome = teamMatches(m.homeTeam, team);
      const isAway = teamMatches(m.awayTeam, team);
      if (!isHome && !isAway) continue;
      if (venue === "home" && !isHome) continue;
      if (venue === "away" && !isAway) continue;
      // A team cannot play itself; if both matched (shouldn't happen) prefer home.
      const playedHome = isHome;
      const gf = playedHome ? m.homeGoals : m.awayGoals;
      const ga = playedHome ? m.awayGoals : m.homeGoals;

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
    }
    return rec;
  }

  /** Compute a points table for a competition and season from match results. */
  standings(competition: string, season: number): TeamRecord[] {
    const compKey = normalizeName(competition);
    const table = new Map<string, TeamRecord>();

    const ensure = (key: string, display: string): TeamRecord => {
      let r = table.get(key);
      if (!r) {
        r = {
          team: display,
          matches: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          points: 0,
        };
        table.set(key, r);
      }
      return r;
    };

    const apply = (r: TeamRecord, gf: number, ga: number) => {
      r.matches++;
      r.goalsFor += gf;
      r.goalsAgainst += ga;
      if (gf > ga) {
        r.wins++;
        r.points += 3;
      } else if (gf === ga) {
        r.draws++;
        r.points += 1;
      } else {
        r.losses++;
      }
    };

    for (const m of this.matches) {
      if (m.season !== season) continue;
      if (!normalizeName(m.competition).includes(compKey)) continue;
      apply(ensure(m.homeKey, m.homeTeam), m.homeGoals, m.awayGoals);
      apply(ensure(m.awayKey, m.awayTeam), m.awayGoals, m.homeGoals);
    }

    return [...table.values()].sort((a, b) => {
      if (b.points !== a.points) return b.points - a.points;
      const gdA = a.goalsFor - a.goalsAgainst;
      const gdB = b.goalsFor - b.goalsAgainst;
      if (gdB !== gdA) return gdB - gdA;
      return b.goalsFor - a.goalsFor;
    });
  }

  /** Descriptive statistics over a filtered set of matches. */
  statistics(q: StatsQuery = {}): Statistics {
    const matches = this.findMatches({
      competition: q.competition,
      season: q.season,
      team: q.team,
    });
    let totalGoals = 0;
    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;
    for (const m of matches) {
      totalGoals += m.homeGoals + m.awayGoals;
      if (m.homeGoals > m.awayGoals) homeWins++;
      else if (m.awayGoals > m.homeGoals) awayWins++;
      else draws++;
    }
    const n = matches.length;
    return {
      totalMatches: n,
      totalGoals,
      averageGoals: n ? totalGoals / n : 0,
      homeWins,
      awayWins,
      draws,
      homeWinRate: n ? homeWins / n : 0,
      awayWinRate: n ? awayWins / n : 0,
      drawRate: n ? draws / n : 0,
    };
  }

  /** Matches with the largest goal margin, biggest first. */
  biggestWins(q: StatsQuery & { limit?: number } = {}): Match[] {
    const matches = this.findMatches({
      competition: q.competition,
      season: q.season,
      team: q.team,
    });
    const sorted = [...matches].sort(
      (a, b) =>
        Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals)
    );
    return q.limit != null ? sorted.slice(0, q.limit) : sorted;
  }

  /** Search players, sorted by overall rating descending. */
  findPlayers(q: PlayerQuery): Player[] {
    const nameKey = q.name ? normalizeName(q.name) : null;
    const natKey = q.nationality ? normalizeName(q.nationality) : null;
    const posKey = q.position ? normalizeName(q.position) : null;

    let result = this.players.filter((p) => {
      if (nameKey && !p.nameKey.includes(nameKey)) return false;
      if (natKey && !normalizeName(p.nationality).includes(natKey)) return false;
      if (q.club && !teamMatches(p.club, q.club)) return false;
      if (posKey && normalizeName(p.position) !== posKey) return false;
      if (q.minOverall != null && (p.overall ?? 0) < q.minOverall) return false;
      return true;
    });

    result = result.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    return q.limit != null ? result.slice(0, q.limit) : result;
  }

  /**
   * Group Brazilian-nationality players at Brazilian clubs (clubs that appear in
   * domestic competitions), with per-club counts and average rating, ordered by
   * descending player count.
   */
  brazilianPlayersByClub(): ClubGroup[] {
    const byClub = new Map<string, { display: string; ratings: number[] }>();
    for (const p of this.players) {
      if (normalizeName(p.nationality) !== "brazil") continue;
      if (!this.domesticTeamKeys.has(p.clubKey)) continue;
      let g = byClub.get(p.clubKey);
      if (!g) {
        g = { display: p.club, ratings: [] };
        byClub.set(p.clubKey, g);
      }
      if (p.overall != null) g.ratings.push(p.overall);
    }
    return [...byClub.values()]
      .map((g) => ({
        club: g.display,
        count: g.ratings.length,
        averageOverall:
          g.ratings.length
            ? g.ratings.reduce((a, b) => a + b, 0) / g.ratings.length
            : 0,
      }))
      .sort((a, b) => b.count - a.count);
  }
}
