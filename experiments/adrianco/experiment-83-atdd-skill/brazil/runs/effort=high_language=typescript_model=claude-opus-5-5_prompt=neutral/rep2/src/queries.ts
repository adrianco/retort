/**
 * Query engine over the in-memory dataset. Every function returns plain
 * structured data; formatting for the MCP text responses lives in format.ts.
 *
 * All match queries operate on the de-duplicated ("canonical") match list,
 * so a fixture present in several CSV files is counted once.
 */

import {
  COMPETITION_NAMES,
  loadDataset,
  type CompetitionId,
  type Dataset,
  type Match,
  type Player,
  type Team,
} from "./data.js";
import { normalizeDateBound } from "./dates.js";
import { CLUB_BY_KEY, CLUBS, RIVALRIES, findRivalry, normalizeText, parseTeamName, type Rivalry } from "./teams.js";

// ---------------------------------------------------------------------------
// Team & competition resolution
// ---------------------------------------------------------------------------

export class TeamNotFoundError extends Error {}

export interface TeamResolution {
  query: string;
  keys: string[];
  teams: Team[];
}

export type Venue = "home" | "away" | "any";

const COMPETITION_SYNONYMS: [RegExp, CompetitionId][] = [
  [/libertadores/, "libertadores"],
  [/copa do brasil|brazilian cup|copa brasil|^cup$|^cdb$/, "copa-do-brasil"],
  [/serie b|série b|^b$/, "serie-b"],
  [/serie c|^c$/, "serie-c"],
  [/brasileir|serie a|^a$|^league$|brazilian league|campeonato brasileiro|^br$/, "brasileirao"],
];

export function resolveCompetition(input: string | undefined): CompetitionId | undefined {
  if (!input) return undefined;
  const n = normalizeText(input);
  if (n === "" || n === "all" || n === "any") return undefined;
  if ((Object.keys(COMPETITION_NAMES) as string[]).includes(input)) return input as CompetitionId;
  for (const [re, id] of COMPETITION_SYNONYMS) if (re.test(n)) return id;
  throw new Error(
    `Unknown competition "${input}". Use one of: Brasileirão (Série A), Série B, Série C, Copa do Brasil, Libertadores.`,
  );
}

export interface MatchFilter {
  team?: string;
  opponent?: string;
  venue?: Venue;
  competition?: string;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  dateFrom?: string;
  dateTo?: string;
  stage?: string;
  round?: string;
}

export function teamWins(m: Match, key: string): boolean {
  return (m.home === key && m.homeGoals > m.awayGoals) || (m.away === key && m.awayGoals > m.homeGoals);
}

export function byDateDesc(a: Match, b: Match): number {
  return (b.date ?? `${b.season}`).localeCompare(a.date ?? `${a.season}`);
}

export interface Record_ {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

export function emptyRecord(): Record_ {
  return { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0 };
}

export function addResult(r: Record_, gf: number, ga: number): void {
  r.matches++;
  r.goalsFor += gf;
  r.goalsAgainst += ga;
  if (gf > ga) {
    r.wins++;
    r.points += 3;
  } else if (gf === ga) {
    r.draws++;
    r.points += 1;
  } else r.losses++;
}

export const winRate = (r: Record_) => (r.matches ? r.wins / r.matches : 0);

export interface StandingRow extends Record_ {
  position: number;
  team: string;
  name: string;
  goalDiff: number;
  note?: string;
}

export interface Standings {
  competition: CompetitionId;
  season: number;
  source: string;
  rows: StandingRow[];
  matchesPlayed: number;
  complete: boolean;
}

export interface Tie {
  stage: string;
  teamA: string;
  teamB: string;
  nameA: string;
  nameB: string;
  legs: Match[];
  aggregateA: number;
  aggregateB: number;
  winner?: string;
  note?: string;
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

const POSITION_GROUPS: Record<string, string[]> = {
  forward: ["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"],
  midfielder: ["CAM", "CM", "CDM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"],
  defender: ["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"],
  goalkeeper: ["GK"],
};

function positionCodes(input: string): string[] {
  const n = normalizeText(input);
  const singular = n.replace(/s$/, "");
  for (const [group, codes] of Object.entries(POSITION_GROUPS)) {
    if (singular === group || (group === "forward" && /striker|attacker|winger/.test(n)) ||
        (group === "goalkeeper" && /keeper|goalie/.test(n)) || (group === "defender" && /back|defence|defense/.test(n)) ||
        (group === "midfielder" && /midfield/.test(n))) {
      return codes;
    }
  }
  return input.split(/[,\s]+/).filter(Boolean).map((s) => s.toUpperCase());
}

const NATIONALITY_SYNONYMS: Record<string, string> = {
  brazilian: "brazil", brasil: "brazil", brasileiro: "brazil", argentinian: "argentina", argentine: "argentina",
  uruguayan: "uruguay", colombian: "colombia", chilean: "chile", paraguayan: "paraguay", portuguese: "portugal",
  spanish: "spain", french: "france", german: "germany", italian: "italy", english: "england", dutch: "netherlands",
  ecuadorian: "ecuador", peruvian: "peru", venezuelan: "venezuela", bolivian: "bolivia", mexican: "mexico",
};

// ---------------------------------------------------------------------------
// The engine
// ---------------------------------------------------------------------------

export class SoccerKnowledgeBase {
  readonly data: Dataset;
  private teamSearch: { key: string; texts: string[]; weight: number }[];

  constructor(data: Dataset) {
    this.data = data;
    const appearances = new Map<string, number>();
    for (const m of data.canonical) {
      appearances.set(m.home, (appearances.get(m.home) ?? 0) + 1);
      appearances.set(m.away, (appearances.get(m.away) ?? 0) + 1);
    }
    this.teamSearch = [...data.teams.values()].map((t) => ({
      key: t.key,
      texts: [normalizeText(t.name), ...[...t.rawNames].map((r) => normalizeText(r)), ...(t.club?.aliases ?? [])],
      weight: (t.club ? 100_000 : 0) + (appearances.get(t.key) ?? 0),
    }));
  }

  static load(dataDir?: string): SoccerKnowledgeBase {
    return new SoccerKnowledgeBase(loadDataset(dataDir));
  }

  teamName(key: string): string {
    return this.data.teams.get(key)?.name ?? CLUB_BY_KEY.get(key)?.name ?? key;
  }

  /**
   * Resolve a user-supplied team name to one or more team keys.
   * Exact normalised/alias matches win; otherwise whole-word partial matches
   * are returned (most prominent club first).
   */
  resolveTeam(query: string, opts: { single?: boolean } = {}): TeamResolution {
    const q = query.trim();
    if (!q) throw new TeamNotFoundError("Empty team name.");
    const parsed = parseTeamName(q);
    if (this.data.teams.has(parsed.key)) return this.resolution(q, [parsed.key]);
    if (parsed.club) return this.resolution(q, [parsed.club.key]);

    const n = normalizeText(q);
    const re = new RegExp(`(^| )${n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}( |$)`);
    const candidates = this.teamSearch.filter((t) => t.texts.includes(n) || t.texts.some((x) => re.test(x)));
    if (candidates.length) return this.resolution(q, this.rank(candidates, opts.single));

    const loose = this.teamSearch.filter((t) => t.texts.some((x) => x.includes(n)));
    if (loose.length) return this.resolution(q, this.rank(loose, opts.single));
    throw new TeamNotFoundError(`No team matching "${query}" was found in the match data.`);
  }

  private rank(list: { key: string; weight: number }[], single?: boolean): string[] {
    const sorted = [...list].sort((a, b) => b.weight - a.weight).map((t) => t.key);
    const unique = [...new Set(sorted)];
    return single ? unique.slice(0, 1) : unique;
  }

  private resolution(query: string, keys: string[]): TeamResolution {
    return { query, keys, teams: keys.map((k) => this.data.teams.get(k)!).filter(Boolean) };
  }

  /** Resolve to exactly one team (the most prominent match). */
  team(query: string): Team {
    const r = this.resolveTeam(query, { single: true });
    return r.teams[0];
  }

  // -------------------------------------------------------------------------
  // Matches
  // -------------------------------------------------------------------------

  findMatches(f: MatchFilter): Match[] {
    const comp = resolveCompetition(f.competition);
    const teamKeys = f.team ? new Set([this.team(f.team).key]) : undefined;
    const oppKeys = f.opponent ? new Set([this.team(f.opponent).key]) : undefined;
    const venue = f.venue ?? "any";
    const from = normalizeDateBound(f.dateFrom, false);
    const to = normalizeDateBound(f.dateTo, true);
    const stage = f.stage ? normalizeText(f.stage) : undefined;

    const out = this.data.canonical.filter((m) => {
      if (comp && m.competition !== comp) return false;
      if (f.season !== undefined && m.season !== f.season) return false;
      if (f.seasonFrom !== undefined && m.season < f.seasonFrom) return false;
      if (f.seasonTo !== undefined && m.season > f.seasonTo) return false;
      if (from && (!m.date || m.date < from)) return false;
      if (to && (!m.date || m.date > to)) return false;
      if (f.round !== undefined && m.round !== String(f.round)) return false;
      if (stage) {
        if (/final/.test(stage) && !/semi|quarter|round/.test(stage) && m.competition === "copa-do-brasil") {
          if (!this.isCupFinal(m)) return false;
        } else if (!m.stage || !normalizeText(m.stage).includes(stage)) return false;
      }
      if (teamKeys) {
        const isHome = teamKeys.has(m.home), isAway = teamKeys.has(m.away);
        if (venue === "home" && !isHome) return false;
        if (venue === "away" && !isAway) return false;
        if (venue === "any" && !isHome && !isAway) return false;
        if (oppKeys) {
          const opp = isHome ? m.away : m.home;
          const oppOk = oppKeys.has(opp) || (isHome && isAway);
          if (!oppOk) return false;
        }
      } else if (oppKeys && !oppKeys.has(m.home) && !oppKeys.has(m.away)) return false;
      return true;
    });
    return out.sort(byDateDesc);
  }

  /** Copa do Brasil finals: the last round of a season when it has exactly one two-legged tie. */
  private cupFinalIds?: Set<string>;
  isCupFinal(m: Match): boolean {
    if (!this.cupFinalIds) {
      this.cupFinalIds = new Set();
      const bySeason = new Map<number, Match[]>();
      for (const x of this.data.canonical) {
        if (x.competition !== "copa-do-brasil") continue;
        const list = bySeason.get(x.season) ?? [];
        list.push(x);
        bySeason.set(x.season, list);
      }
      for (const list of bySeason.values()) {
        const rounds = list.filter((x) => x.round).map((x) => Number(x.round));
        if (rounds.length) {
          const max = Math.max(...rounds);
          const last = list.filter((x) => Number(x.round) === max);
          const pairs = new Set(last.map((x) => [x.home, x.away].sort().join("|")));
          if (last.length <= 2 && pairs.size === 1) {
            last.forEach((x) => this.cupFinalIds!.add(x.id));
            continue;
          }
        }
        // No usable round information (e.g. BR-Football rows, or a season whose
        // round data stops early): the last two matches of the season form the
        // final if they are the two legs of the same pairing.
        const sorted = list.filter((x) => x.date).sort(byDateDesc);
        if (sorted.length >= 2) {
          const [a, b] = sorted;
          if (a.home === b.away && a.away === b.home) [a, b].forEach((x) => this.cupFinalIds!.add(x.id));
        }
      }
    }
    return this.cupFinalIds.has(m.id);
  }

  cupFinals(competition: string = "copa-do-brasil"): Tie[] {
    const comp = resolveCompetition(competition)!;
    const finals =
      comp === "copa-do-brasil"
        ? this.data.canonical.filter((m) => m.competition === comp && this.isCupFinal(m))
        : this.data.canonical.filter((m) => m.competition === comp && m.stage === "final");
    const seasons = [...new Set(finals.map((m) => m.season))].sort((a, b) => b - a);
    return seasons.flatMap((s) => this.groupTies(finals.filter((m) => m.season === s), "final"));
  }

  headToHead(teamA: string, teamB: string, f: Omit<MatchFilter, "team" | "opponent"> = {}) {
    const a = this.team(teamA);
    const b = this.team(teamB);
    const matches = this.findMatches({ ...f, team: a.key, opponent: b.key });
    let aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;
    const byCompetition: Record<string, number> = {};
    for (const m of matches) {
      const ag = m.home === a.key ? m.homeGoals : m.awayGoals;
      const bg = m.home === a.key ? m.awayGoals : m.homeGoals;
      aGoals += ag;
      bGoals += bg;
      if (ag > bg) aWins++;
      else if (bg > ag) bWins++;
      else draws++;
      byCompetition[m.competition] = (byCompetition[m.competition] ?? 0) + 1;
    }
    return { teamA: a, teamB: b, rivalry: findRivalry(a.key, b.key), matches, aWins, bWins, draws, aGoals, bGoals, byCompetition };
  }

  // -------------------------------------------------------------------------
  // Teams
  // -------------------------------------------------------------------------

  teamRecord(teamQuery: string, f: Omit<MatchFilter, "team"> = {}) {
    const team = this.team(teamQuery);
    const matches = this.findMatches({ ...f, team: team.key });
    const overall = emptyRecord(), home = emptyRecord(), away = emptyRecord();
    const byCompetition: Partial<Record<CompetitionId, Record_>> = {};
    for (const m of matches) {
      const isHome = m.home === team.key;
      const gf = isHome ? m.homeGoals : m.awayGoals;
      const ga = isHome ? m.awayGoals : m.homeGoals;
      addResult(overall, gf, ga);
      addResult(isHome ? home : away, gf, ga);
      addResult((byCompetition[m.competition] ??= emptyRecord()), gf, ga);
    }
    return { team, filter: f, matches, overall, home, away, byCompetition };
  }

  /** Competitions and seasons a team appears in, across every match file. */
  teamCompetitions(teamQuery: string) {
    const team = this.team(teamQuery);
    const result = new Map<CompetitionId, { seasons: Set<number>; matches: number; sources: Set<string> }>();
    for (const m of this.data.matches) {
      if (m.home !== team.key && m.away !== team.key) continue;
      const e = result.get(m.competition) ?? { seasons: new Set(), matches: 0, sources: new Set() };
      e.seasons.add(m.season);
      e.sources.add(m.source);
      if (!m.duplicateOf) e.matches++;
      result.set(m.competition, e);
    }
    return { team, competitions: result };
  }

  /**
   * Rank teams by a metric over a set of matches (e.g. best home record,
   * most goals scored in a season).
   */
  teamRankings(opts: {
    competition?: string;
    season?: number;
    seasonFrom?: number;
    seasonTo?: number;
    venue?: Venue;
    metric?: "winRate" | "points" | "pointsPerGame" | "goalsFor" | "goalsAgainst" | "goalDiff" | "wins";
    minMatches?: number;
    limit?: number;
  }) {
    const venue = opts.venue ?? "any";
    const metric = opts.metric ?? "winRate";
    const matches = this.findMatches({
      competition: opts.competition, season: opts.season, seasonFrom: opts.seasonFrom, seasonTo: opts.seasonTo,
    });
    const records = new Map<string, Record_>();
    for (const m of matches) {
      if (venue !== "away") addResult(records.get(m.home) ?? records.set(m.home, emptyRecord()).get(m.home)!, m.homeGoals, m.awayGoals);
      if (venue !== "home") addResult(records.get(m.away) ?? records.set(m.away, emptyRecord()).get(m.away)!, m.awayGoals, m.homeGoals);
    }
    const defaultMin = opts.season !== undefined ? 1 : 19;
    const minMatches = opts.minMatches ?? defaultMin;
    const value = (r: Record_): number => {
      switch (metric) {
        case "winRate": return winRate(r);
        case "points": return r.points;
        case "pointsPerGame": return r.matches ? r.points / r.matches : 0;
        case "goalsFor": return r.goalsFor;
        case "goalsAgainst": return -r.goalsAgainst;
        case "goalDiff": return r.goalsFor - r.goalsAgainst;
        case "wins": return r.wins;
      }
    };
    const rows = [...records.entries()]
      .filter(([, r]) => r.matches >= minMatches)
      .map(([key, r]) => ({ team: key, name: this.teamName(key), ...r, winRate: winRate(r), value: value(r) }))
      .sort((a, b) => b.value - a.value || b.points - a.points || b.goalsFor - a.goalsFor);
    return { metric, venue, minMatches, matchesConsidered: matches.length, rows: rows.slice(0, opts.limit ?? 10) };
  }

  // -------------------------------------------------------------------------
  // Competitions
  // -------------------------------------------------------------------------

  /** League table for a season, computed from match results (3 pts win, 1 draw). */
  standings(season: number, competition: string = "brasileirao"): Standings {
    const comp = resolveCompetition(competition) ?? "brasileirao";
    if (comp === "copa-do-brasil" || comp === "libertadores") {
      throw new Error(`${COMPETITION_NAMES[comp]} is a knockout competition; use the bracket tool instead of standings.`);
    }
    // Start from the most complete single file, then fill gaps (e.g. rows left
    // unplayed/NA in that file) with de-duplicated fixtures from other files,
    // as long as both teams belong to this season's league and the fixture is
    // not already present. This never double-counts and ignores stray rows.
    const all = this.data.matches.filter((m) => m.competition === comp && m.season === season);
    if (all.length === 0) throw new Error(`No ${COMPETITION_NAMES[comp]} matches found for ${season}.`);
    const bySource = new Map<string, Match[]>();
    for (const m of all) bySource.set(m.source, [...(bySource.get(m.source) ?? []), m]);
    const [baseSource, base] = [...bySource.entries()].sort((a, b) => b[1].length - a[1].length)[0];
    const leagueTeams = new Set(base.flatMap((m) => [m.home, m.away]));
    const fixtures = new Set(base.map((m) => `${m.home}|${m.away}`));
    const matches = [...base];
    const sources = new Set([baseSource]);
    for (const m of all) {
      const fk = `${m.home}|${m.away}`;
      if (m.source === baseSource || m.duplicateOf || fixtures.has(fk)) continue;
      if (!leagueTeams.has(m.home) || !leagueTeams.has(m.away)) continue;
      fixtures.add(fk);
      matches.push(m);
      sources.add(m.source);
    }
    const source = [...sources].join(" + ");

    const records = new Map<string, Record_>();
    const rec = (k: string) => records.get(k) ?? records.set(k, emptyRecord()).get(k)!;
    for (const m of matches) {
      addResult(rec(m.home), m.homeGoals, m.awayGoals);
      addResult(rec(m.away), m.awayGoals, m.homeGoals);
    }
    const rows: StandingRow[] = [...records.entries()]
      .map(([team, r]) => ({ ...r, team, name: this.teamName(team), goalDiff: r.goalsFor - r.goalsAgainst, position: 0 }))
      .sort((a, b) => b.points - a.points || b.wins - a.wins || b.goalDiff - a.goalDiff || b.goalsFor - a.goalsFor || a.name.localeCompare(b.name));
    rows.forEach((r, i) => (r.position = i + 1));

    const n = rows.length;
    const expected = n * (n - 1);
    const complete = matches.length >= expected;
    if (complete && n > 0) {
      rows[0].note = "Champion";
      const relegated = comp === "brasileirao" ? relegationSlots(season) : 4;
      for (let i = n - relegated; i < n; i++) rows[i].note = "Relegated";
    }
    return { competition: comp, season, source, rows, matchesPlayed: matches.length, complete };
  }

  /** Knockout bracket (two-legged ties aggregated) for a cup season. */
  bracket(season: number, competition: string = "libertadores") {
    const comp = resolveCompetition(competition) ?? "libertadores";
    if (comp !== "libertadores" && comp !== "copa-do-brasil") {
      throw new Error("Brackets are only available for Copa Libertadores and Copa do Brasil.");
    }
    const matches = this.data.canonical.filter((m) => m.competition === comp && m.season === season);
    if (matches.length === 0) throw new Error(`No ${COMPETITION_NAMES[comp]} matches found for ${season}.`);
    const stages: { stage: string; ties: Tie[] }[] = [];
    if (comp === "libertadores") {
      for (const stage of ["round of 16", "quarterfinals", "semifinals", "final"]) {
        const ms = matches.filter((m) => m.stage === stage);
        if (ms.length) stages.push({ stage, ties: this.groupTies(ms, stage) });
      }
      const groups = matches.filter((m) => m.stage === "group stage").length;
      return { competition: comp, season, groupStageMatches: groups, stages };
    }
    const rounds = [...new Set(matches.filter((m) => m.round).map((m) => Number(m.round)))].sort((a, b) => a - b);
    for (const r of rounds) {
      const ms = matches.filter((m) => Number(m.round) === r);
      const label = ms.some((m) => this.isCupFinal(m)) ? `Round ${r} (final)` : `Round ${r}`;
      stages.push({ stage: label, ties: this.groupTies(ms, label) });
    }
    const unrounded = matches.filter((m) => !m.round);
    if (unrounded.length) stages.push({ stage: "Matches without round information", ties: this.groupTies(unrounded, "unknown") });
    return { competition: comp, season, groupStageMatches: 0, stages };
  }

  private groupTies(matches: Match[], stage: string): Tie[] {
    const ties = new Map<string, Tie>();
    for (const m of [...matches].sort((a, b) => (a.date ?? "").localeCompare(b.date ?? ""))) {
      const id = [m.home, m.away].sort().join("|");
      let t = ties.get(id);
      if (!t) {
        // Team A is the side at home in the first leg (second leg hosts the decider).
        t = { stage, teamA: m.home, teamB: m.away, nameA: this.teamName(m.home), nameB: this.teamName(m.away), legs: [], aggregateA: 0, aggregateB: 0 };
        ties.set(id, t);
      }
      t.legs.push(m);
      t.aggregateA += m.home === t.teamA ? m.homeGoals : m.awayGoals;
      t.aggregateB += m.home === t.teamA ? m.awayGoals : m.homeGoals;
    }
    for (const t of ties.values()) {
      if (t.aggregateA > t.aggregateB) t.winner = t.teamA;
      else if (t.aggregateB > t.aggregateA) t.winner = t.teamB;
      else t.note = "level on aggregate (decided by away goals or penalties - not in dataset)";
    }
    return [...ties.values()];
  }

  // -------------------------------------------------------------------------
  // Statistics
  // -------------------------------------------------------------------------

  biggestWins(f: MatchFilter & { limit?: number } = {}): Match[] {
    const matches = this.findMatches(f);
    return [...matches]
      .sort((a, b) =>
        Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals) ||
        b.homeGoals + b.awayGoals - (a.homeGoals + a.awayGoals) ||
        byDateDesc(a, b))
      .slice(0, f.limit ?? 10);
  }

  highestScoring(f: MatchFilter & { limit?: number } = {}): Match[] {
    return [...this.findMatches(f)]
      .sort((a, b) => b.homeGoals + b.awayGoals - (a.homeGoals + a.awayGoals) || byDateDesc(a, b))
      .slice(0, f.limit ?? 10);
  }

  summarize(matches: Match[]) {
    let goals = 0, homeWins = 0, awayWins = 0, draws = 0, homeGoals = 0, awayGoals = 0;
    for (const m of matches) {
      goals += m.homeGoals + m.awayGoals;
      homeGoals += m.homeGoals;
      awayGoals += m.awayGoals;
      if (m.homeGoals > m.awayGoals) homeWins++;
      else if (m.awayGoals > m.homeGoals) awayWins++;
      else draws++;
    }
    const n = matches.length || 1;
    return {
      matches: matches.length,
      goals,
      avgGoals: goals / n,
      avgHomeGoals: homeGoals / n,
      avgAwayGoals: awayGoals / n,
      homeWinRate: homeWins / n,
      awayWinRate: awayWins / n,
      drawRate: draws / n,
      homeWins,
      awayWins,
      draws,
    };
  }

  /** Aggregate statistics, optionally broken down per season. */
  competitionStats(f: MatchFilter = {}) {
    const matches = this.findMatches(f);
    const seasons = [...new Set(matches.map((m) => m.season))].sort((a, b) => a - b);
    const perSeason = seasons.map((s) => ({ season: s, ...this.summarize(matches.filter((m) => m.season === s)) }));
    const withStats = matches.filter((m) => m.stats?.homeCorners !== undefined);
    const extra = withStats.length
      ? {
          matchesWithStats: withStats.length,
          avgCorners: withStats.reduce((s, m) => s + (m.stats!.homeCorners ?? 0) + (m.stats!.awayCorners ?? 0), 0) / withStats.length,
          avgShots: withStats.reduce((s, m) => s + (m.stats!.homeShots ?? 0) + (m.stats!.awayShots ?? 0), 0) / withStats.length,
        }
      : undefined;
    return { overall: this.summarize(matches), perSeason, extra };
  }

  /** Compare league seasons side by side (stats + champion). */
  compareSeasons(seasons: number[], competition: string = "brasileirao") {
    const comp = resolveCompetition(competition) ?? "brasileirao";
    return seasons.map((season) => {
      const stats = this.summarize(this.findMatches({ competition: comp, season }));
      let champion: StandingRow | undefined;
      let topScorer: StandingRow | undefined;
      let bestDefence: StandingRow | undefined;
      if (comp !== "copa-do-brasil" && comp !== "libertadores" && stats.matches > 0) {
        const table = this.standings(season, comp);
        champion = table.rows[0];
        topScorer = [...table.rows].sort((a, b) => b.goalsFor - a.goalsFor)[0];
        bestDefence = [...table.rows].sort((a, b) => a.goalsAgainst - b.goalsAgainst)[0];
      }
      return { season, competition: comp, ...stats, champion, topScoringTeam: topScorer, bestDefence };
    });
  }

  derbies(opts: { season?: number; rivalry?: string; team?: string; competition?: string } = {}) {
    let rivalries: Rivalry[] = RIVALRIES;
    if (opts.rivalry) {
      const n = normalizeText(opts.rivalry);
      rivalries = RIVALRIES.filter((r) => normalizeText(r.name).includes(n));
      if (!rivalries.length) throw new Error(`Unknown rivalry "${opts.rivalry}". Known: ${RIVALRIES.map((r) => r.name).join(", ")}`);
    }
    if (opts.team) {
      const key = this.team(opts.team).key;
      rivalries = rivalries.filter((r) => r.teams.includes(key));
    }
    const comp = resolveCompetition(opts.competition);
    const out: { rivalry: Rivalry; matches: Match[] }[] = [];
    for (const r of rivalries) {
      const matches = this.data.canonical
        .filter((m) => (opts.season === undefined || m.season === opts.season) && (!comp || m.competition === comp))
        .filter((m) => (m.home === r.teams[0] && m.away === r.teams[1]) || (m.home === r.teams[1] && m.away === r.teams[0]))
        .sort(byDateDesc);
      if (matches.length) out.push({ rivalry: r, matches });
    }
    return out;
  }

  // -------------------------------------------------------------------------
  // Players
  // -------------------------------------------------------------------------

  searchPlayers(f: PlayerFilter): { players: Player[]; total: number; clubKeys?: string[]; fuzzy: boolean } {
    let fuzzy = false;
    let list = this.data.players;
    let clubKeys: string[] | undefined;

    if (f.nationality) {
      const n = normalizeText(f.nationality);
      const target = NATIONALITY_SYNONYMS[n] ?? n;
      list = list.filter((p) => normalizeText(p.nationality) === target);
    }
    if (f.club) {
      const n = normalizeText(f.club);
      const parsed = parseTeamName(f.club);
      const curated = parsed.club?.key ?? CLUBS.find((c) => c.aliases.includes(n))?.key;
      if (curated) {
        clubKeys = [curated];
        list = list.filter((p) => p.clubKey === curated);
      } else {
        const re = new RegExp(`(^| )${n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}( |$)`);
        list = list.filter((p) => re.test(normalizeText(p.club)));
      }
    }
    if (f.brazilianClubsOnly) list = list.filter((p) => p.clubKey);
    if (f.position) {
      const codes = new Set(positionCodes(f.position));
      list = list.filter((p) => codes.has(p.position));
    }
    if (f.minOverall !== undefined) list = list.filter((p) => (p.overall ?? 0) >= f.minOverall!);
    if (f.maxAge !== undefined) list = list.filter((p) => (p.age ?? 99) <= f.maxAge!);
    if (f.name) {
      const tokens = normalizeText(f.name).split(" ").filter(Boolean);
      const full = normalizeText(f.name);
      const exact = list.filter((p) => normalizeText(p.name) === full);
      const all = list.filter((p) => {
        const words = normalizeText(p.name).split(" ");
        return tokens.every((t) => words.some((w) => w.startsWith(t)));
      });
      if (exact.length) list = [...exact, ...all.filter((p) => !exact.includes(p))];
      else if (all.length) list = all;
      else {
        // Fall back to players matching any of the name tokens, best overlap first.
        fuzzy = true;
        const scored = list
          .map((p) => {
            const words = normalizeText(p.name).split(" ");
            return { p, score: tokens.filter((t) => t.length > 2 && words.some((w) => w.startsWith(t))).length };
          })
          .filter((x) => x.score > 0)
          .sort((a, b) => b.score - a.score || (b.p.overall ?? 0) - (a.p.overall ?? 0));
        list = scored.map((x) => x.p);
      }
    }
    const sortBy = f.sortBy ?? (f.name && !fuzzy ? undefined : "overall");
    if (sortBy) {
      const cmp: Record<string, (a: Player, b: Player) => number> = {
        overall: (a, b) => (b.overall ?? 0) - (a.overall ?? 0) || (b.potential ?? 0) - (a.potential ?? 0),
        potential: (a, b) => (b.potential ?? 0) - (a.potential ?? 0),
        age: (a, b) => (a.age ?? 0) - (b.age ?? 0),
        name: (a, b) => a.name.localeCompare(b.name),
      };
      list = [...list].sort(cmp[sortBy]);
    }
    return { players: list.slice(0, f.limit ?? 20), total: list.length, clubKeys, fuzzy };
  }

  getPlayer(nameOrId: string | number): Player[] {
    if (typeof nameOrId === "number" || /^\d+$/.test(String(nameOrId))) {
      const id = Number(nameOrId);
      return this.data.players.filter((p) => p.id === id);
    }
    return this.searchPlayers({ name: String(nameOrId), limit: 5 }).players;
  }

  /** Players grouped by club, e.g. Brazilian players at Brazilian clubs. */
  playersByClub(opts: { nationality?: string; brazilianClubsOnly?: boolean; limit?: number } = {}) {
    const { players } = this.searchPlayers({ nationality: opts.nationality, brazilianClubsOnly: opts.brazilianClubsOnly, limit: Infinity });
    const groups = new Map<string, Player[]>();
    for (const p of players) {
      const club = p.club || "(no club)";
      groups.set(club, [...(groups.get(club) ?? []), p]);
    }
    return [...groups.entries()]
      .map(([club, ps]) => ({
        club,
        clubKey: ps[0].clubKey,
        count: ps.length,
        avgOverall: ps.reduce((s, p) => s + (p.overall ?? 0), 0) / ps.length,
        best: ps.reduce((a, b) => ((b.overall ?? 0) > (a.overall ?? 0) ? b : a)),
      }))
      .sort((a, b) => b.count - a.count || b.avgOverall - a.avgOverall)
      .slice(0, opts.limit ?? 20);
  }

  /** Cross-file profile: match record per competition + FIFA squad for the club. */
  teamProfile(teamQuery: string) {
    const team = this.team(teamQuery);
    const comps = this.teamCompetitions(team.key);
    const record = this.teamRecord(team.key);
    const squad = this.data.players.filter((p) => p.clubKey === team.key).sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    const lastMatch = record.matches[0];
    const titles = this.leagueTitles(team.key);
    return { team, competitions: comps.competitions, record, squad, lastMatch, titles };
  }

  /** Brasileirão seasons the team won (calculated from complete seasons in the data). */
  leagueTitles(key: string): number[] {
    const seasons = [...new Set(this.data.matches.filter((m) => m.competition === "brasileirao").map((m) => m.season))];
    return seasons
      .filter((s) => {
        const t = this.standingsCached(s);
        return t?.complete && t.rows[0]?.team === key;
      })
      .sort((a, b) => a - b);
  }

  private standingsCache = new Map<number, Standings | null>();
  private standingsCached(season: number): Standings | null {
    if (!this.standingsCache.has(season)) {
      try {
        this.standingsCache.set(season, this.standings(season, "brasileirao"));
      } catch {
        this.standingsCache.set(season, null);
      }
    }
    return this.standingsCache.get(season)!;
  }

  listCompetitions() {
    const out = new Map<CompetitionId, { seasons: Set<number>; matches: number; sources: Set<string> }>();
    for (const m of this.data.matches) {
      const e = out.get(m.competition) ?? { seasons: new Set(), matches: 0, sources: new Set() };
      e.seasons.add(m.season);
      e.sources.add(m.source);
      if (!m.duplicateOf) e.matches++;
      out.set(m.competition, e);
    }
    return out;
  }
}

/** Série A relegation places: 2 in 2003 (24 clubs), 4 from 2004 onwards. */
function relegationSlots(season: number): number {
  return season === 2003 ? 2 : 4;
}
