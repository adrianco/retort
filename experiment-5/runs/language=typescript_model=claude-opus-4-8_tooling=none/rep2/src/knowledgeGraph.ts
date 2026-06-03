/**
 * ============================================================================
 * File: src/knowledgeGraph.ts
 * Project: Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * Context:
 *   The in-memory knowledge graph. Teams are nodes; matches are edges between
 *   two team nodes; players are linked to their club team node by normalized
 *   key. On construction it indexes all matches (by team key) and players
 *   (by club key) so the query methods below run well within the spec's
 *   performance budget (simple < 2s, aggregate < 5s).
 *
 *   This class is the single query surface used by both the test suite
 *   (tests/) and the MCP tool layer (src/server.ts). It returns plain data
 *   structures; human-readable formatting lives in src/format.ts.
 *
 *   Query categories implemented (per spec):
 *     1. Match queries      - findMatches, headToHead
 *     2. Team queries       - teamRecord, teamCompetitions
 *     3. Player queries     - findPlayers
 *     4. Competition queries - standings
 *     5. Statistical analysis - competitionStats, biggestWins
 * ============================================================================
 */

import type { LoadedData } from "./loader.js";
import { loadAll } from "./loader.js";
import { teamKey } from "./normalize.js";
import type { Match, Player, Record as TeamRecord, Team } from "./types.js";

export interface MatchFilter {
  /** Match if either home or away team matches this name. */
  team?: string;
  /** Restrict to matches where `team` played at home / away. */
  venue?: "home" | "away" | "either";
  /** Second team (for fixtures between two specific teams). */
  opponent?: string;
  competition?: string;
  season?: number;
  /** Inclusive ISO date lower bound (YYYY-MM-DD). */
  from?: string;
  /** Inclusive ISO date upper bound (YYYY-MM-DD). */
  to?: string;
  /** Cap the number of returned matches (most recent first). */
  limit?: number;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  totalMatches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  matches: Match[];
}

export interface StandingRow {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

export interface CompetitionStats {
  competition: string;
  season?: number;
  matches: number;
  matchesWithScores: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

const EMPTY_RECORD = (): TeamRecord => ({
  matches: 0,
  wins: 0,
  draws: 0,
  losses: 0,
  goalsFor: 0,
  goalsAgainst: 0,
});

/** Returns true when both goal values are present (a decided/recorded match). */
function hasScore(m: Match): boolean {
  return m.homeGoals !== null && m.awayGoals !== null;
}

/** Sort comparator: most recent date first, nulls last. */
function byDateDesc(a: Match, b: Match): number {
  if (a.date && b.date) return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
  if (a.date) return -1;
  if (b.date) return 1;
  return 0;
}

export class KnowledgeGraph {
  readonly matches: Match[];
  readonly players: Player[];
  private readonly teams = new Map<string, Team>();
  private readonly matchesByTeam = new Map<string, Match[]>();
  private readonly playersByClub = new Map<string, Player[]>();

  constructor(data: LoadedData) {
    this.matches = data.matches;
    this.players = data.players;
    this.index();
  }

  /** Convenience constructor that loads from a data/kaggle directory. */
  static fromDirectory(dir: string): KnowledgeGraph {
    return new KnowledgeGraph(loadAll(dir));
  }

  private touchTeam(key: string, name: string, state?: string, competition?: string): void {
    let team = this.teams.get(key);
    if (!team) {
      team = { key, name, states: new Set(), competitions: new Set() };
      this.teams.set(key, team);
    }
    // Prefer the shortest non-empty display name as canonical.
    if (name && (team.name.length === 0 || name.length < team.name.length)) {
      team.name = name;
    }
    if (state) team.states.add(state);
    if (competition) team.competitions.add(competition);
  }

  private index(): void {
    for (const m of this.matches) {
      this.touchTeam(m.homeTeamKey, m.homeTeam, m.homeState, m.competition);
      this.touchTeam(m.awayTeamKey, m.awayTeam, m.awayState, m.competition);
      this.push(this.matchesByTeam, m.homeTeamKey, m);
      this.push(this.matchesByTeam, m.awayTeamKey, m);
    }
    for (const p of this.players) {
      if (p.clubKey) this.push(this.playersByClub, p.clubKey, p);
    }
  }

  private push<T>(map: Map<string, T[]>, key: string, value: T): void {
    const list = map.get(key);
    if (list) list.push(value);
    else map.set(key, [value]);
  }

  /** Resolve a free-text team name to its canonical display name, if known. */
  resolveTeam(name: string): Team | undefined {
    return this.teams.get(teamKey(name));
  }

  listTeams(): Team[] {
    return [...this.teams.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  // --- 1. Match queries ----------------------------------------------------

  findMatches(filter: MatchFilter): Match[] {
    let candidates: Match[];
    if (filter.team) {
      candidates = this.matchesByTeam.get(teamKey(filter.team)) ?? [];
    } else {
      candidates = this.matches;
    }

    const teamK = filter.team ? teamKey(filter.team) : undefined;
    const oppK = filter.opponent ? teamKey(filter.opponent) : undefined;
    const venue = filter.venue ?? "either";

    const out = candidates.filter((m) => {
      if (teamK) {
        const isHome = m.homeTeamKey === teamK;
        const isAway = m.awayTeamKey === teamK;
        if (venue === "home" && !isHome) return false;
        if (venue === "away" && !isAway) return false;
        if (venue === "either" && !isHome && !isAway) return false;
      }
      if (oppK) {
        if (m.homeTeamKey !== oppK && m.awayTeamKey !== oppK) return false;
        // When both team & opponent are given, ensure they are the two sides.
        if (teamK && !((m.homeTeamKey === teamK && m.awayTeamKey === oppK) ||
          (m.homeTeamKey === oppK && m.awayTeamKey === teamK))) {
          return false;
        }
      }
      if (filter.competition && m.competition !== filter.competition) return false;
      if (filter.season !== undefined && m.season !== filter.season) return false;
      if (filter.from && (!m.date || m.date < filter.from)) return false;
      if (filter.to && (!m.date || m.date > filter.to)) return false;
      return true;
    });

    out.sort(byDateDesc);
    return filter.limit ? out.slice(0, filter.limit) : out;
  }

  headToHead(teamA: string, teamB: string, competition?: string): HeadToHead {
    const keyA = teamKey(teamA);
    const keyB = teamKey(teamB);
    const matches = this.findMatches({ team: teamA, opponent: teamB, competition });

    let aWins = 0;
    let bWins = 0;
    let draws = 0;
    let aGoals = 0;
    let bGoals = 0;
    for (const m of matches) {
      if (!hasScore(m)) continue;
      const aIsHome = m.homeTeamKey === keyA;
      const aFor = aIsHome ? m.homeGoals! : m.awayGoals!;
      const bFor = aIsHome ? m.awayGoals! : m.homeGoals!;
      aGoals += aFor;
      bGoals += bFor;
      if (aFor > bFor) aWins++;
      else if (bFor > aFor) bWins++;
      else draws++;
    }

    return {
      teamA: this.teams.get(keyA)?.name ?? teamA,
      teamB: this.teams.get(keyB)?.name ?? teamB,
      totalMatches: matches.length,
      teamAWins: aWins,
      teamBWins: bWins,
      draws,
      teamAGoals: aGoals,
      teamBGoals: bGoals,
      matches,
    };
  }

  // --- 2. Team queries -----------------------------------------------------

  teamRecord(
    team: string,
    opts: { competition?: string; season?: number; venue?: "home" | "away" | "either" } = {},
  ): TeamRecord {
    const key = teamKey(team);
    const matches = this.findMatches({
      team,
      competition: opts.competition,
      season: opts.season,
      venue: opts.venue ?? "either",
    });
    const rec = EMPTY_RECORD();
    for (const m of matches) {
      if (!hasScore(m)) continue;
      const isHome = m.homeTeamKey === key;
      const gf = isHome ? m.homeGoals! : m.awayGoals!;
      const ga = isHome ? m.awayGoals! : m.homeGoals!;
      rec.matches++;
      rec.goalsFor += gf;
      rec.goalsAgainst += ga;
      if (gf > ga) rec.wins++;
      else if (gf < ga) rec.losses++;
      else rec.draws++;
    }
    return rec;
  }

  teamCompetitions(team: string): string[] {
    return [...(this.resolveTeam(team)?.competitions ?? [])].sort();
  }

  // --- 3. Player queries ---------------------------------------------------

  findPlayers(filter: PlayerFilter): Player[] {
    let candidates: Player[];
    if (filter.club) {
      candidates = this.playersByClub.get(teamKey(filter.club)) ?? [];
    } else {
      candidates = this.players;
    }

    const nameNeedle = filter.name?.toLowerCase();
    const natNeedle = filter.nationality?.toLowerCase();
    const posNeedle = filter.position?.toLowerCase();

    const out = candidates.filter((p) => {
      if (nameNeedle && !p.name.toLowerCase().includes(nameNeedle)) return false;
      if (natNeedle && p.nationality.toLowerCase() !== natNeedle) return false;
      if (posNeedle && p.position.toLowerCase() !== posNeedle) return false;
      if (filter.minOverall !== undefined && (p.overall ?? 0) < filter.minOverall) return false;
      return true;
    });

    out.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    return filter.limit ? out.slice(0, filter.limit) : out;
  }

  // --- 4. Competition queries ---------------------------------------------

  /** Build a league table for a competition/season from match results. */
  standings(competition: string, season: number): StandingRow[] {
    const table = new Map<string, StandingRow & { key: string }>();
    const ensure = (key: string, name: string) => {
      let row = table.get(key);
      if (!row) {
        row = {
          key,
          team: name,
          played: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          goalDifference: 0,
          points: 0,
        };
        table.set(key, row);
      }
      return row;
    };

    for (const m of this.matches) {
      if (m.competition !== competition || m.season !== season || !hasScore(m)) continue;
      const home = ensure(m.homeTeamKey, m.homeTeam);
      const away = ensure(m.awayTeamKey, m.awayTeam);
      home.played++;
      away.played++;
      home.goalsFor += m.homeGoals!;
      home.goalsAgainst += m.awayGoals!;
      away.goalsFor += m.awayGoals!;
      away.goalsAgainst += m.homeGoals!;
      if (m.homeGoals! > m.awayGoals!) {
        home.wins++;
        home.points += 3;
        away.losses++;
      } else if (m.homeGoals! < m.awayGoals!) {
        away.wins++;
        away.points += 3;
        home.losses++;
      } else {
        home.draws++;
        away.draws++;
        home.points += 1;
        away.points += 1;
      }
    }

    const rows = [...table.values()];
    for (const r of rows) r.goalDifference = r.goalsFor - r.goalsAgainst;
    rows.sort(
      (a, b) =>
        b.points - a.points ||
        b.goalDifference - a.goalDifference ||
        b.goalsFor - a.goalsFor ||
        a.team.localeCompare(b.team),
    );
    return rows.map(({ key, ...rest }) => rest);
  }

  /** Distinct seasons available for a competition (ascending). */
  seasons(competition?: string): number[] {
    const set = new Set<number>();
    for (const m of this.matches) {
      if (competition && m.competition !== competition) continue;
      if (m.season !== null) set.add(m.season);
    }
    return [...set].sort((a, b) => a - b);
  }

  listCompetitions(): string[] {
    const set = new Set<string>();
    for (const m of this.matches) set.add(m.competition);
    return [...set].sort();
  }

  // --- 5. Statistical analysis --------------------------------------------

  competitionStats(competition?: string, season?: number): CompetitionStats {
    let matches = 0;
    let scored = 0;
    let goals = 0;
    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;
    for (const m of this.matches) {
      if (competition && m.competition !== competition) continue;
      if (season !== undefined && m.season !== season) continue;
      matches++;
      if (!hasScore(m)) continue;
      scored++;
      goals += m.homeGoals! + m.awayGoals!;
      if (m.homeGoals! > m.awayGoals!) homeWins++;
      else if (m.homeGoals! < m.awayGoals!) awayWins++;
      else draws++;
    }
    const denom = scored || 1;
    return {
      competition: competition ?? "All competitions",
      season,
      matches,
      matchesWithScores: scored,
      totalGoals: goals,
      averageGoalsPerMatch: scored ? goals / scored : 0,
      homeWins,
      awayWins,
      draws,
      homeWinRate: homeWins / denom,
      awayWinRate: awayWins / denom,
      drawRate: draws / denom,
    };
  }

  /** Matches sorted by goal margin (largest first). */
  biggestWins(opts: { competition?: string; season?: number; limit?: number } = {}): Match[] {
    const out = this.matches.filter((m) => {
      if (!hasScore(m)) return false;
      if (opts.competition && m.competition !== opts.competition) return false;
      if (opts.season !== undefined && m.season !== opts.season) return false;
      return Math.abs(m.homeGoals! - m.awayGoals!) > 0;
    });
    out.sort((a, b) => {
      const ma = Math.abs(a.homeGoals! - a.awayGoals!);
      const mb = Math.abs(b.homeGoals! - b.awayGoals!);
      return mb - ma || b.homeGoals! + b.awayGoals! - (a.homeGoals! + a.awayGoals!);
    });
    return out.slice(0, opts.limit ?? 10);
  }
}
