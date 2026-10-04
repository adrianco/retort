/**
 * Query engine over the loaded dataset.
 *
 * Every public method returns plain structured data; `format.ts` turns the
 * results into the human-readable text returned by the MCP tools. Team
 * arguments are free text and are resolved through the TeamRegistry, so
 * "Sao Paulo", "São Paulo-SP" and "Sao Paulo FC" all work.
 */
import {
  COMPETITIONS,
  LEAGUES,
  type Competition,
  type Dataset,
  type Match,
  type Player,
} from "./data.js";
import { foldText, parseDate } from "./normalize.js";
import { derbyName, type Team } from "./teams.js";

export class QueryError extends Error {}

export interface TeamRecord {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

export const emptyRecord = (): TeamRecord => ({
  played: 0,
  wins: 0,
  draws: 0,
  losses: 0,
  goalsFor: 0,
  goalsAgainst: 0,
  points: 0,
});

export function addResult(rec: TeamRecord, gf: number, ga: number): void {
  rec.played++;
  rec.goalsFor += gf;
  rec.goalsAgainst += ga;
  if (gf > ga) {
    rec.wins++;
    rec.points += 3;
  } else if (gf === ga) {
    rec.draws++;
    rec.points += 1;
  } else rec.losses++;
}

export type Venue = "home" | "away" | "any";

export interface MatchFilter {
  team?: string;
  opponent?: string;
  venue?: Venue;
  competition?: string | string[];
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  dateFrom?: string;
  dateTo?: string;
  /** stage/round label, e.g. "final", "semifinals", "round of 16" */
  stage?: string;
  round?: number;
  derbiesOnly?: boolean;
}

interface ResolvedFilter {
  teamId?: string;
  opponentId?: string;
  venue: Venue;
  competitions?: Set<Competition>;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  dateFrom?: string;
  dateTo?: string;
  stage?: string;
  round?: number;
  derbiesOnly?: boolean;
}

const COMPETITION_ALIASES: [RegExp, Competition][] = [
  [/libertadores|libertad/, "libertadores"],
  [/copa do brasil|brazilian cup|brazil cup|copa brasil|^cup$|^copa$/, "copa-do-brasil"],
  [/serie b|series b|^b$|segunda/, "serie-b"],
  [/serie c|series c|^c$|terceira/, "serie-c"],
  [/serie a|series a|brasileirao|brasileiro|campeonato brasileiro|^league$|^a$/, "serie-a"],
];

/** Map user text ("Brasileirão", "Copa do Brasil", "serie-a") to a competition id. */
export function parseCompetition(input: string): Competition {
  const f = foldText(input).replace(/[-_]/g, " ");
  for (const [re, comp] of COMPETITION_ALIASES) if (re.test(f)) return comp;
  throw new QueryError(
    `Unknown competition "${input}". Use one of: ${Object.entries(COMPETITIONS)
      .map(([k, v]) => `${k} (${v})`)
      .join(", ")}`,
  );
}

export function parseCompetitions(input: string | string[] | undefined): Set<Competition> | undefined {
  if (input === undefined) return undefined;
  const list = (Array.isArray(input) ? input : [input]).filter((s) => s && foldText(s) !== "all");
  if (list.length === 0) return undefined;
  return new Set(list.map(parseCompetition));
}

const POSITION_GROUPS: Record<string, string[]> = {
  goalkeeper: ["GK"],
  defender: ["CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"],
  midfielder: ["CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"],
  forward: ["ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"],
};
const POSITION_ALIASES: Record<string, string> = {
  gk: "goalkeeper", goalkeeper: "goalkeeper", goalkeepers: "goalkeeper", keeper: "goalkeeper", goleiro: "goalkeeper",
  defender: "defender", defenders: "defender", defence: "defender", defense: "defender", zagueiro: "defender",
  midfielder: "midfielder", midfielders: "midfielder", midfield: "midfielder", meia: "midfielder",
  forward: "forward", forwards: "forward", attacker: "forward", attackers: "forward", striker: "forward",
  strikers: "forward", winger: "forward", wingers: "forward", atacante: "forward",
};

export function positionsFor(input: string): Set<string> {
  const parts = input.split(/[,\s/]+/).filter(Boolean);
  const out = new Set<string>();
  for (const p of parts) {
    const group = POSITION_ALIASES[foldText(p)];
    if (group) POSITION_GROUPS[group].forEach((x) => out.add(x));
    else out.add(p.toUpperCase());
  }
  return out;
}

export interface StandingRow extends TeamRecord {
  position: number;
  teamId: string;
  team: string;
  goalDifference: number;
}

export interface Tie {
  stage: string;
  teamA: string;
  teamB: string;
  teamAId: string;
  teamBId: string;
  legs: Match[];
  aggregateA: number;
  aggregateB: number;
  winnerId?: string;
  /** How the winner was determined */
  decidedBy?: "aggregate" | "progression" | "unknown";
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxAge?: number;
  brazilianClubsOnly?: boolean;
  sortBy?: "overall" | "potential" | "age" | "name";
  limit?: number;
}

export type RankingMetric =
  | "points"
  | "points_per_game"
  | "win_rate"
  | "home_win_rate"
  | "away_win_rate"
  | "goals_for"
  | "goals_against"
  | "goal_difference"
  | "goals_per_game"
  | "wins"
  | "clean_sheets";

export class SoccerQueries {
  private matchesByTeam = new Map<string, Match[]>();
  private matchCount = new Map<string, number>();

  constructor(readonly ds: Dataset) {
    for (const m of ds.matches) {
      for (const t of [m.homeId, m.awayId]) {
        const list = this.matchesByTeam.get(t) ?? [];
        list.push(m);
        this.matchesByTeam.set(t, list);
        this.matchCount.set(t, (this.matchCount.get(t) ?? 0) + 1);
      }
    }
  }

  // ---------------------------------------------------------------- teams

  teamName(id: string): string {
    return this.ds.teams.get(id)?.name ?? id;
  }

  /** Candidate teams for a free-text query, best first. */
  findTeams(query: string): Team[] {
    return this.ds.teams
      .search(query, (id) => this.matchCount.get(id) ?? 0)
      .filter((t) => (this.matchCount.get(t.id) ?? 0) > 0);
  }

  resolveTeam(query: string): Team {
    const exact = this.ds.teams.get(query);
    if (exact && this.matchCount.has(exact.id)) return exact;
    const hits = this.findTeams(query);
    if (hits.length === 0) {
      throw new QueryError(`No team matching "${query}" was found in the match data.`);
    }
    return hits[0];
  }

  // -------------------------------------------------------------- matches

  private resolveFilter(f: MatchFilter): ResolvedFilter {
    const r: ResolvedFilter = { venue: f.venue ?? "any" };
    if (f.team) r.teamId = this.resolveTeam(f.team).id;
    if (f.opponent) r.opponentId = this.resolveTeam(f.opponent).id;
    r.competitions = parseCompetitions(f.competition);
    r.season = f.season;
    r.seasonFrom = f.seasonFrom;
    r.seasonTo = f.seasonTo;
    if (f.dateFrom) {
      const d = parseDate(f.dateFrom);
      if (!d) throw new QueryError(`Unrecognised date "${f.dateFrom}" (use YYYY-MM-DD or DD/MM/YYYY)`);
      r.dateFrom = d.date;
    }
    if (f.dateTo) {
      const d = parseDate(f.dateTo);
      if (!d) throw new QueryError(`Unrecognised date "${f.dateTo}" (use YYYY-MM-DD or DD/MM/YYYY)`);
      // A bare year as an upper bound means the end of that year.
      r.dateTo = /^\d{4}$/.test(f.dateTo.trim()) ? `${f.dateTo.trim()}-12-31` : d.date;
    }
    r.stage = f.stage ? foldText(f.stage) : undefined;
    r.round = f.round;
    r.derbiesOnly = f.derbiesOnly;
    return r;
  }

  private matchesFor(r: ResolvedFilter): Match[] {
    const base = r.teamId ? this.matchesByTeam.get(r.teamId) ?? [] : this.ds.matches;
    return base.filter((m) => {
      if (r.teamId) {
        const isHome = m.homeId === r.teamId;
        if (r.venue === "home" && !isHome) return false;
        if (r.venue === "away" && isHome) return false;
        if (r.opponentId && (isHome ? m.awayId : m.homeId) !== r.opponentId) return false;
      } else if (r.opponentId && m.homeId !== r.opponentId && m.awayId !== r.opponentId) return false;
      if (r.competitions && !r.competitions.has(m.competition)) return false;
      if (r.season !== undefined && m.season !== r.season) return false;
      if (r.seasonFrom !== undefined && m.season < r.seasonFrom) return false;
      if (r.seasonTo !== undefined && m.season > r.seasonTo) return false;
      if (r.dateFrom && m.date < r.dateFrom) return false;
      if (r.dateTo && m.date > r.dateTo) return false;
      if (r.stage) {
        const st = foldText(m.stage ?? "");
        if (r.stage === "final" ? st !== "final" : !st.includes(r.stage)) return false;
      }
      if (r.round !== undefined && m.round !== r.round) return false;
      if (r.derbiesOnly && !derbyName(m.homeId, m.awayId)) return false;
      return true;
    });
  }

  /** Search matches. Results are newest first unless order = "asc". */
  searchMatches(f: MatchFilter, opts: { limit?: number; order?: "asc" | "desc" } = {}) {
    const r = this.resolveFilter(f);
    const all = this.matchesFor(r);
    const sorted = [...all].sort((a, b) =>
      opts.order === "asc" ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date),
    );
    const limit = opts.limit ?? 20;
    return {
      team: r.teamId ? this.teamName(r.teamId) : undefined,
      teamId: r.teamId,
      opponent: r.opponentId ? this.teamName(r.opponentId) : undefined,
      opponentId: r.opponentId,
      total: all.length,
      matches: sorted.slice(0, limit),
      summary: r.teamId ? this.recordFor(all, r.teamId) : undefined,
    };
  }

  recordFor(matches: Match[], teamId: string): TeamRecord {
    const rec = emptyRecord();
    for (const m of matches) {
      if (m.homeId === teamId) addResult(rec, m.homeGoals, m.awayGoals);
      else if (m.awayId === teamId) addResult(rec, m.awayGoals, m.homeGoals);
    }
    return rec;
  }

  // ----------------------------------------------------------- team stats

  teamRecord(team: string, f: Omit<MatchFilter, "team"> = {}) {
    const r = this.resolveFilter({ ...f, team });
    const id = r.teamId!;
    const all = this.matchesFor({ ...r, venue: "any" });
    const venueMatches = r.venue === "any" ? all : this.matchesFor(r);
    const home = this.recordFor(all.filter((m) => m.homeId === id), id);
    const away = this.recordFor(all.filter((m) => m.awayId === id), id);
    const byCompetition: { competition: Competition; name: string; record: TeamRecord; seasons: number[] }[] = [];
    for (const comp of Object.keys(COMPETITIONS) as Competition[]) {
      const ms = venueMatches.filter((m) => m.competition === comp);
      if (!ms.length) continue;
      byCompetition.push({
        competition: comp,
        name: COMPETITIONS[comp],
        record: this.recordFor(ms, id),
        seasons: [...new Set(ms.map((m) => m.season))].sort((a, b) => a - b),
      });
    }
    let biggestWin: Match | undefined;
    let worstDefeat: Match | undefined;
    for (const m of venueMatches) {
      const margin = m.homeId === id ? m.homeGoals - m.awayGoals : m.awayGoals - m.homeGoals;
      const bw = biggestWin ? (biggestWin.homeId === id ? 1 : -1) * (biggestWin.homeGoals - biggestWin.awayGoals) : -Infinity;
      const wd = worstDefeat ? (worstDefeat.homeId === id ? 1 : -1) * (worstDefeat.homeGoals - worstDefeat.awayGoals) : Infinity;
      if (margin > 0 && margin > bw) biggestWin = m;
      if (margin < 0 && margin < wd) worstDefeat = m;
    }
    return {
      teamId: id,
      team: this.teamName(id),
      venue: r.venue,
      record: this.recordFor(venueMatches, id),
      home,
      away,
      byCompetition,
      biggestWin,
      worstDefeat,
    };
  }

  headToHead(teamA: string, teamB: string, f: Omit<MatchFilter, "team" | "opponent"> = {}, limit = 10) {
    const r = this.resolveFilter({ ...f, team: teamA, opponent: teamB });
    if (r.teamId === r.opponentId) throw new QueryError("Head-to-head needs two different teams.");
    const ms = this.matchesFor(r).sort((a, b) => b.date.localeCompare(a.date));
    const recA = this.recordFor(ms, r.teamId!);
    const byCompetition = new Map<Competition, TeamRecord>();
    for (const m of ms) {
      const rec = byCompetition.get(m.competition) ?? emptyRecord();
      const isHome = m.homeId === r.teamId;
      addResult(rec, isHome ? m.homeGoals : m.awayGoals, isHome ? m.awayGoals : m.homeGoals);
      byCompetition.set(m.competition, rec);
    }
    return {
      teamAId: r.teamId!,
      teamBId: r.opponentId!,
      teamA: this.teamName(r.teamId!),
      teamB: this.teamName(r.opponentId!),
      derby: derbyName(r.teamId!, r.opponentId!),
      total: ms.length,
      winsA: recA.wins,
      winsB: recA.losses,
      draws: recA.draws,
      goalsA: recA.goalsFor,
      goalsB: recA.goalsAgainst,
      byCompetition: [...byCompetition.entries()].map(([c, rec]) => ({ competition: c, name: COMPETITIONS[c], record: rec })),
      matches: ms.slice(0, limit),
      lastMatch: ms[0],
    };
  }

  // ----------------------------------------------------------- standings

  standings(competition: string = "serie-a", season: number): { competition: Competition; season: number; rows: StandingRow[]; matches: number; complete: boolean } {
    const comp = parseCompetition(competition);
    if (!LEAGUES.includes(comp)) {
      throw new QueryError(`${COMPETITIONS[comp]} is a knockout competition; use the bracket tool instead of standings.`);
    }
    const ms = this.ds.matches.filter((m) => m.competition === comp && m.season === season);
    if (!ms.length) {
      const seasons = this.seasons(comp);
      throw new QueryError(`No ${COMPETITIONS[comp]} matches for ${season}. Seasons available: ${seasons[0]}-${seasons[seasons.length - 1]}.`);
    }
    const table = new Map<string, TeamRecord>();
    for (const m of ms) {
      const h = table.get(m.homeId) ?? emptyRecord();
      const a = table.get(m.awayId) ?? emptyRecord();
      addResult(h, m.homeGoals, m.awayGoals);
      addResult(a, m.awayGoals, m.homeGoals);
      table.set(m.homeId, h);
      table.set(m.awayId, a);
    }
    // CBF tie-breakers: points, wins, goal difference, goals scored.
    const rows = [...table.entries()]
      .map(([teamId, rec]) => ({ ...rec, teamId, team: this.teamName(teamId), goalDifference: rec.goalsFor - rec.goalsAgainst, position: 0 }))
      .sort(
        (a, b) =>
          b.points - a.points ||
          b.wins - a.wins ||
          b.goalDifference - a.goalDifference ||
          b.goalsFor - a.goalsFor ||
          a.team.localeCompare(b.team),
      );
    rows.forEach((r, i) => (r.position = i + 1));
    const n = rows.length;
    const complete = ms.length >= n * (n - 1); // double round-robin
    return { competition: comp, season, rows, matches: ms.length, complete };
  }

  seasons(comp?: Competition): number[] {
    const s = new Set<number>();
    for (const m of this.ds.matches) if (!comp || m.competition === comp) s.add(m.season);
    return [...s].sort((a, b) => a - b);
  }

  // --------------------------------------------------------- knockouts

  /** Knockout ties for a cup season, grouped by stage, winners inferred. */
  bracket(competition: string, season: number, includeGroupStage = false) {
    const comp = parseCompetition(competition);
    if (LEAGUES.includes(comp)) throw new QueryError(`${COMPETITIONS[comp]} is a league; use the standings tool.`);
    const ms = this.ds.matches.filter((m) => m.competition === comp && m.season === season);
    if (!ms.length) {
      const seasons = this.seasons(comp);
      throw new QueryError(`No ${COMPETITIONS[comp]} matches for ${season}. Seasons available: ${seasons[0]}-${seasons[seasons.length - 1]}.`);
    }
    const stageOrder = (s: string) => {
      const f = foldText(s);
      if (f === "group stage") return 0;
      const rm = f.match(/^round (\d+)$/);
      if (rm) return +rm[1];
      if (f === "round of 16") return 100;
      if (f.startsWith("quarter")) return 101;
      if (f.startsWith("semi")) return 102;
      if (f === "final") return 1000;
      return 50;
    };
    const stages = [...new Set(ms.map((m) => m.stage ?? "unknown"))].sort((a, b) => stageOrder(a) - stageOrder(b));
    const out: { stage: string; ties: Tie[] }[] = [];
    for (let si = 0; si < stages.length; si++) {
      const stage = stages[si];
      if (!includeGroupStage && foldText(stage) === "group stage") continue;
      const later = new Set(
        ms.filter((m) => stageOrder(m.stage ?? "unknown") > stageOrder(stage)).flatMap((m) => [m.homeId, m.awayId]),
      );
      const tieMap = new Map<string, Match[]>();
      for (const m of ms.filter((x) => (x.stage ?? "unknown") === stage).sort((a, b) => a.date.localeCompare(b.date))) {
        const key = [m.homeId, m.awayId].sort().join("|");
        tieMap.set(key, [...(tieMap.get(key) ?? []), m]);
      }
      const ties: Tie[] = [];
      for (const legs of tieMap.values()) {
        const a = legs[0].homeId;
        const b = legs[0].awayId;
        let ga = 0;
        let gb = 0;
        for (const l of legs) {
          ga += l.homeId === a ? l.homeGoals : l.awayGoals;
          gb += l.homeId === a ? l.awayGoals : l.homeGoals;
        }
        const tie: Tie = {
          stage,
          teamA: this.teamName(a),
          teamB: this.teamName(b),
          teamAId: a,
          teamBId: b,
          legs,
          aggregateA: ga,
          aggregateB: gb,
        };
        if (later.has(a) !== later.has(b)) {
          tie.winnerId = later.has(a) ? a : b;
          tie.decidedBy = "progression";
        } else if (ga !== gb) {
          tie.winnerId = ga > gb ? a : b;
          tie.decidedBy = "aggregate";
        } else tie.decidedBy = "unknown";
        ties.push(tie);
      }
      out.push({ stage, ties });
    }
    return { competition: comp, season, stages: out };
  }

  /** All finals of a cup competition across seasons. */
  finals(competition: string) {
    const comp = parseCompetition(competition);
    if (LEAGUES.includes(comp)) throw new QueryError(`${COMPETITIONS[comp]} has no finals; use standings.`);
    const out: { season: number; tie: Tie }[] = [];
    for (const season of this.seasons(comp)) {
      const b = this.bracket(comp, season);
      const final = b.stages.find((s) => s.stage === "final");
      if (final) for (const tie of final.ties) out.push({ season, tie });
    }
    return { competition: comp, finals: out };
  }

  // ---------------------------------------------------------- statistics

  /** Aggregate statistics for a set of matches. */
  matchStats(f: MatchFilter = {}) {
    const r = this.resolveFilter(f);
    const ms = this.matchesFor(r);
    let goals = 0;
    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;
    const scorelines = new Map<string, number>();
    let corners = 0;
    let cornerMatches = 0;
    let shots = 0;
    let shotMatches = 0;
    for (const m of ms) {
      goals += m.homeGoals + m.awayGoals;
      if (m.homeGoals > m.awayGoals) homeWins++;
      else if (m.homeGoals < m.awayGoals) awayWins++;
      else draws++;
      const sl = `${m.homeGoals}-${m.awayGoals}`;
      scorelines.set(sl, (scorelines.get(sl) ?? 0) + 1);
      if (m.stats?.homeCorners != null && m.stats.awayCorners != null) {
        corners += m.stats.homeCorners + m.stats.awayCorners;
        cornerMatches++;
      }
      if (m.stats?.homeShots != null && m.stats.awayShots != null) {
        shots += m.stats.homeShots + m.stats.awayShots;
        shotMatches++;
      }
    }
    const n = ms.length;
    const highestScoring = [...ms].sort((a, b) => b.homeGoals + b.awayGoals - (a.homeGoals + a.awayGoals) || a.date.localeCompare(b.date))[0];
    return {
      matches: n,
      goals,
      avgGoals: n ? goals / n : 0,
      homeWins,
      awayWins,
      draws,
      homeWinRate: n ? homeWins / n : 0,
      awayWinRate: n ? awayWins / n : 0,
      drawRate: n ? draws / n : 0,
      commonScorelines: [...scorelines.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5),
      avgCorners: cornerMatches ? corners / cornerMatches : undefined,
      avgShots: shotMatches ? shots / shotMatches : undefined,
      highestScoring,
      seasons: [...new Set(ms.map((m) => m.season))].sort((a, b) => a - b),
    };
  }

  biggestWins(f: MatchFilter = {}, limit = 10) {
    const r = this.resolveFilter(f);
    let ms = this.matchesFor(r);
    if (r.teamId) {
      // Only wins by the requested team.
      ms = ms.filter((m) => (m.homeId === r.teamId ? m.homeGoals > m.awayGoals : m.awayGoals > m.homeGoals));
    }
    return ms
      .filter((m) => m.homeGoals !== m.awayGoals)
      .sort(
        (a, b) =>
          Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals) ||
          b.homeGoals + b.awayGoals - (a.homeGoals + a.awayGoals) ||
          a.date.localeCompare(b.date),
      )
      .slice(0, limit);
  }

  /** Rank teams by a metric over the filtered matches. */
  teamRankings(metric: RankingMetric, f: Omit<MatchFilter, "team" | "opponent" | "venue"> = {}, opts: { limit?: number; minMatches?: number; ascending?: boolean } = {}) {
    const r = this.resolveFilter(f);
    const ms = this.matchesFor(r);
    const overall = new Map<string, TeamRecord>();
    const home = new Map<string, TeamRecord>();
    const away = new Map<string, TeamRecord>();
    const cleanSheets = new Map<string, number>();
    const get = (map: Map<string, TeamRecord>, id: string) => {
      let rec = map.get(id);
      if (!rec) map.set(id, (rec = emptyRecord()));
      return rec;
    };
    for (const m of ms) {
      addResult(get(overall, m.homeId), m.homeGoals, m.awayGoals);
      addResult(get(overall, m.awayId), m.awayGoals, m.homeGoals);
      addResult(get(home, m.homeId), m.homeGoals, m.awayGoals);
      addResult(get(away, m.awayId), m.awayGoals, m.homeGoals);
      if (m.awayGoals === 0) cleanSheets.set(m.homeId, (cleanSheets.get(m.homeId) ?? 0) + 1);
      if (m.homeGoals === 0) cleanSheets.set(m.awayId, (cleanSheets.get(m.awayId) ?? 0) + 1);
    }
    const venueMap = metric === "home_win_rate" ? home : metric === "away_win_rate" ? away : overall;
    // Default minimum sample: a third of the busiest team's games, so tiny
    // samples (one-off cup appearances) don't top rate-based rankings.
    const maxPlayed = Math.max(0, ...[...venueMap.values()].map((x) => x.played));
    const isRate = /rate|per_game/.test(metric);
    const minMatches = opts.minMatches ?? (isRate ? Math.max(1, Math.floor(maxPlayed / 3)) : 1);
    const value = (id: string, rec: TeamRecord): number => {
      switch (metric) {
        case "points": return rec.points;
        case "points_per_game": return rec.points / rec.played;
        case "win_rate":
        case "home_win_rate":
        case "away_win_rate": return rec.wins / rec.played;
        case "goals_for": return rec.goalsFor;
        case "goals_against": return rec.goalsAgainst;
        case "goal_difference": return rec.goalsFor - rec.goalsAgainst;
        case "goals_per_game": return rec.goalsFor / rec.played;
        case "wins": return rec.wins;
        case "clean_sheets": return cleanSheets.get(id) ?? 0;
      }
    };
    const ascending = opts.ascending ?? metric === "goals_against";
    const rows = [...venueMap.entries()]
      .filter(([, rec]) => rec.played >= minMatches)
      .map(([id, rec]) => ({ teamId: id, team: this.teamName(id), value: value(id, rec), record: rec }))
      .sort((a, b) => (ascending ? a.value - b.value : b.value - a.value) || b.record.played - a.record.played || a.team.localeCompare(b.team));
    return { metric, minMatches, totalTeams: rows.length, rows: rows.slice(0, opts.limit ?? 10) };
  }

  /** Season-by-season comparison for a league (or cup). */
  compareSeasons(competition: string, seasons: number[]) {
    const comp = parseCompetition(competition);
    return seasons.map((season) => {
      const stats = this.matchStats({ competition: comp, season });
      let champion: StandingRow | undefined;
      let topScoringTeam: { team: string; goals: number } | undefined;
      if (LEAGUES.includes(comp) && stats.matches) {
        const st = this.standings(comp, season);
        champion = st.rows[0];
        const top = [...st.rows].sort((a, b) => b.goalsFor - a.goalsFor)[0];
        topScoringTeam = { team: top.team, goals: top.goalsFor };
      }
      return { season, stats, champion, topScoringTeam };
    });
  }

  derbies(f: Omit<MatchFilter, "derbiesOnly"> = {}, limit = 50) {
    const res = this.searchMatches({ ...f, derbiesOnly: true }, { limit });
    return { ...res, matches: res.matches.map((m) => ({ match: m, derby: derbyName(m.homeId, m.awayId)! })) };
  }

  /** Competitions, seasons and overall record of a team, plus linked FIFA players. */
  teamProfile(team: string) {
    const t = this.resolveTeam(team);
    const rec = this.teamRecord(t.id);
    const players = this.ds.players.filter((p) => p.teamId === t.id).sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    const rivals = [...new Set((this.matchesByTeam.get(t.id) ?? []).map((m) => (m.homeId === t.id ? m.awayId : m.homeId)))]
      .map((id) => ({ id, derby: derbyName(t.id, id) }))
      .filter((x) => x.derby)
      .map((x) => ({ team: this.teamName(x.id), derby: x.derby! }));
    const ms = this.matchesByTeam.get(t.id) ?? [];
    return {
      ...rec,
      teamInfo: t,
      firstMatch: ms[0],
      lastMatch: ms[ms.length - 1],
      players,
      rivals,
    };
  }

  // -------------------------------------------------------------- players

  private playerMatchesName(p: Player, q: string): boolean {
    if (p.searchName.includes(q)) return true;
    const tokens = q.split(" ").filter(Boolean);
    return tokens.length > 1 && tokens.every((t) => p.searchName.includes(t));
  }

  searchPlayers(f: PlayerFilter) {
    let ps = this.ds.players;
    const notes: string[] = [];
    if (f.name) {
      const q = foldText(f.name);
      ps = ps.filter((p) => this.playerMatchesName(p, q));
    }
    if (f.nationality) {
      const q = foldText(f.nationality);
      const alias: Record<string, string> = { brazilian: "brazil", brasil: "brazil", brasileiro: "brazil", argentinian: "argentina", argentine: "argentina", uruguayan: "uruguay" };
      const nat = alias[q] ?? q;
      ps = ps.filter((p) => foldText(p.nationality) === nat);
    }
    if (f.club) {
      const q = foldText(f.club);
      let teamId: string | undefined;
      try {
        const hit = this.findTeams(f.club)[0];
        if (hit?.known) teamId = hit.id;
      } catch {
        /* not a match-data team */
      }
      // Prefer an exact club / linked-team match ("Santos" should not pull in
      // "Santos Laguna"); fall back to substring matching ("Madrid").
      const exact = ps.filter((p) => foldText(p.club) === q || (teamId !== undefined && p.teamId === teamId));
      ps = exact.length ? exact : ps.filter((p) => foldText(p.club).includes(q));
      if (!ps.length && teamId) {
        notes.push(
          `${this.teamName(teamId)} is not licensed in the FIFA 19 player file. Brazilian clubs present: ${[...this.ds.brazilianClubs].sort().join(", ")}.`,
        );
      }
    }
    if (f.position) {
      const pos = positionsFor(f.position);
      ps = ps.filter((p) => pos.has(p.position));
    }
    if (f.minOverall !== undefined) ps = ps.filter((p) => (p.overall ?? 0) >= f.minOverall!);
    if (f.maxAge !== undefined) ps = ps.filter((p) => p.age !== null && p.age <= f.maxAge!);
    if (f.brazilianClubsOnly) ps = ps.filter((p) => this.ds.brazilianClubs.has(p.club));
    const sortBy = f.sortBy ?? "overall";
    const sorted = [...ps].sort((a, b) => {
      switch (sortBy) {
        case "potential": return (b.potential ?? 0) - (a.potential ?? 0) || (b.overall ?? 0) - (a.overall ?? 0);
        case "age": return (a.age ?? 99) - (b.age ?? 99);
        case "name": return a.name.localeCompare(b.name);
        default: return (b.overall ?? 0) - (a.overall ?? 0) || (b.potential ?? 0) - (a.potential ?? 0);
      }
    });
    return { total: ps.length, players: sorted.slice(0, f.limit ?? 25), notes };
  }

  /** Look up a single player (best match) plus alternatives. */
  getPlayer(name: string) {
    const q = foldText(name);
    let hits = this.ds.players.filter((p) => p.searchName === q);
    if (!hits.length) hits = this.ds.players.filter((p) => this.playerMatchesName(p, q));
    hits = [...hits].sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    let suggestions: Player[] = [];
    if (!hits.length) {
      // Partial token matches as suggestions ("Gabriel Barbosa" -> "Gabriel ...", "... Barbosa").
      const tokens = q.split(" ").filter((t) => t.length >= 3);
      suggestions = this.ds.players
        .map((p) => ({ p, score: tokens.filter((t) => p.searchName.split(/[\s.]+/).includes(t)).length }))
        .filter((x) => x.score > 0)
        .sort((a, b) => b.score - a.score || (b.p.overall ?? 0) - (a.p.overall ?? 0))
        .slice(0, 8)
        .map((x) => x.p);
    }
    return { player: hits[0], others: hits.slice(1, 10), suggestions };
  }

  /** Player counts and average rating grouped by club. */
  clubSummary(f: { nationality?: string; brazilianClubsOnly?: boolean; limit?: number; minPlayers?: number } = {}) {
    const res = this.searchPlayers({ nationality: f.nationality, brazilianClubsOnly: f.brazilianClubsOnly, limit: Infinity });
    const byClub = new Map<string, Player[]>();
    for (const p of res.players) {
      if (!p.club) continue;
      byClub.set(p.club, [...(byClub.get(p.club) ?? []), p]);
    }
    const rows = [...byClub.entries()]
      .filter(([, ps]) => ps.length >= (f.minPlayers ?? 1))
      .map(([club, ps]) => ({
        club,
        teamId: ps[0].teamId,
        players: ps.length,
        avgOverall: ps.reduce((s, p) => s + (p.overall ?? 0), 0) / ps.length,
        best: ps.reduce((a, b) => ((b.overall ?? 0) > (a.overall ?? 0) ? b : a)),
      }))
      .sort((a, b) => b.players - a.players || b.avgOverall - a.avgOverall);
    return { totalPlayers: res.total, clubs: rows.slice(0, f.limit ?? 20), totalClubs: rows.length };
  }

  nationalitySummary(limit = 15) {
    const counts = new Map<string, Player[]>();
    for (const p of this.ds.players) counts.set(p.nationality, [...(counts.get(p.nationality) ?? []), p]);
    return [...counts.entries()]
      .map(([nationality, ps]) => ({
        nationality,
        players: ps.length,
        avgOverall: ps.reduce((s, p) => s + (p.overall ?? 0), 0) / ps.length,
      }))
      .sort((a, b) => b.players - a.players)
      .slice(0, limit);
  }
}
