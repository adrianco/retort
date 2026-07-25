/**
 * Query engine over the loaded Dataset: match search, head-to-head,
 * team statistics, standings, player search and aggregate analytics.
 */

import { normalizeTeamName, stripDiacritics, teamMatches, type TeamName } from "./teams.js";
import type { Competition, Dataset, Match, Player } from "./types.js";

// ---------------------------------------------------------------- helpers

const COMPETITIONS: Competition[] = [
  "Brasileirão Série A",
  "Brasileirão Série B",
  "Brasileirão Série C",
  "Copa do Brasil",
  "Copa Libertadores",
];

/** Fuzzy-resolve a user-supplied competition name. */
export function resolveCompetition(input?: string): Competition | undefined {
  if (!input) return undefined;
  const s = stripDiacritics(input).toLowerCase();
  if (s.includes("libertadores")) return "Copa Libertadores";
  if (s.includes("copa do brasil") || s.includes("brazilian cup") || s === "cup" || s.includes("cup"))
    return "Copa do Brasil";
  if (s.includes("serie b") || s.includes("série b")) return "Brasileirão Série B";
  if (s.includes("serie c")) return "Brasileirão Série C";
  if (s.includes("brasileir") || s.includes("serie a") || s.includes("liga")) {
    return "Brasileirão Série A";
  }
  return undefined;
}

export interface MatchFilter {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
}

function matchInvolves(m: Match, q: TeamName): "home" | "away" | null {
  if (teamMatches(m.home, q)) return "home";
  if (teamMatches(m.away, q)) return "away";
  return null;
}

export function filterMatches(ds: Dataset, f: MatchFilter): Match[] {
  const comp = resolveCompetition(f.competition);
  const teamQ = f.team ? normalizeTeamName(f.team) : null;
  const oppQ = f.opponent ? normalizeTeamName(f.opponent) : null;

  return ds.matches.filter((m) => {
    if (comp && m.competition !== comp) return false;
    if (f.season !== undefined && m.season !== f.season) return false;
    if (f.dateFrom && (!m.date || m.date < f.dateFrom)) return false;
    if (f.dateTo && (!m.date || m.date > f.dateTo)) return false;
    if (teamQ) {
      const side = matchInvolves(m, teamQ);
      if (!side) return false;
      if (oppQ) {
        const otherSide = side === "home" ? m.away : m.home;
        if (!teamMatches(otherSide, oppQ)) return false;
      }
    } else if (oppQ) {
      if (!matchInvolves(m, oppQ)) return false;
    }
    return true;
  });
}

export function formatScoreline(m: Match): string {
  return `${m.home.display} ${m.homeGoals}-${m.awayGoals} ${m.away.display}`;
}

export function formatMatchLine(m: Match): string {
  const bits = [m.date ?? "unknown date", `${formatScoreline(m)}`, m.competition];
  const extra: string[] = [];
  if (m.round) extra.push(`Round ${m.round}`);
  if (m.stage && m.stage !== m.round) extra.push(m.stage);
  if (m.stadium) extra.push(m.stadium);
  const tail = extra.length ? ` (${extra.join(", ")})` : "";
  return `${bits[0]}: ${bits[1]} [${bits[2]}]${tail}`;
}

// ---------------------------------------------------------------- head-to-head

export interface HeadToHead {
  team1: string;
  team2: string;
  matches: Match[];
  team1Wins: number;
  team2Wins: number;
  draws: number;
  team1Goals: number;
  team2Goals: number;
}

export function headToHead(ds: Dataset, team1: string, team2: string): HeadToHead {
  const q1 = normalizeTeamName(team1);
  const matches = filterMatches(ds, { team: team1, opponent: team2 });
  let w1 = 0,
    w2 = 0,
    d = 0,
    g1 = 0,
    g2 = 0;
  for (const m of matches) {
    const t1Home = matchInvolves(m, q1) === "home";
    const t1Goals = t1Home ? m.homeGoals : m.awayGoals;
    const t2Goals = t1Home ? m.awayGoals : m.homeGoals;
    g1 += t1Goals;
    g2 += t2Goals;
    if (t1Goals > t2Goals) w1++;
    else if (t2Goals > t1Goals) w2++;
    else d++;
  }
  return {
    team1,
    team2,
    matches,
    team1Wins: w1,
    team2Wins: w2,
    draws: d,
    team1Goals: g1,
    team2Goals: g2,
  };
}

// ---------------------------------------------------------------- team stats

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number; // 0..1
  competitions: Record<string, number>;
  seasons: number[];
}

export function teamStats(
  ds: Dataset,
  team: string,
  opts: { season?: number; competition?: string; venue?: "home" | "away" | "all" } = {},
): TeamStats {
  const venue = opts.venue ?? "all";
  const q = normalizeTeamName(team);
  const all = filterMatches(ds, {
    team,
    season: opts.season,
    competition: opts.competition,
  });
  let wins = 0,
    draws = 0,
    losses = 0,
    gf = 0,
    ga = 0,
    count = 0;
  const competitions: Record<string, number> = {};
  const seasons = new Set<number>();
  for (const m of all) {
    const side = matchInvolves(m, q);
    if (!side) continue;
    if (venue !== "all" && side !== venue) continue;
    count++;
    const f = side === "home" ? m.homeGoals : m.awayGoals;
    const a = side === "home" ? m.awayGoals : m.homeGoals;
    gf += f;
    ga += a;
    if (f > a) wins++;
    else if (f < a) losses++;
    else draws++;
    competitions[m.competition] = (competitions[m.competition] ?? 0) + 1;
    if (m.season !== null) seasons.add(m.season);
  }
  return {
    team,
    matches: count,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    winRate: count ? wins / count : 0,
    competitions,
    seasons: [...seasons].sort((a, b) => a - b),
  };
}

// ---------------------------------------------------------------- standings

export interface StandingRow {
  position: number;
  team: string;
  key: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}

/**
 * Files considered authoritative for league standings. The extended-stats
 * file (BR-Football-Dataset.csv) occasionally misses fixtures or records a
 * shifted date, so when an authoritative file covers the requested season
 * only its matches are used; otherwise (e.g. Série B/C) all matches count.
 */
const AUTHORITATIVE_SOURCES: Partial<Record<Competition, string[]>> = {
  "Brasileirão Série A": ["Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv"],
  "Copa do Brasil": ["Brazilian_Cup_Matches.csv"],
  "Copa Libertadores": ["Libertadores_Matches.csv"],
};

export function standings(
  ds: Dataset,
  season: number,
  competition?: string,
): StandingRow[] {
  const comp = resolveCompetition(competition) ?? "Brasileirão Série A";
  const rows = new Map<string, StandingRow>();
  const displayFor = new Map<string, string>();

  let pool = ds.matches.filter((m) => m.competition === comp && m.season === season);
  const preferred = AUTHORITATIVE_SOURCES[comp];
  if (preferred) {
    const authoritative = pool.filter((m) => m.sources.some((s) => preferred.includes(s)));
    if (authoritative.length > 0) pool = authoritative;
  }

  const bump = (t: TeamName, gf: number, ga: number) => {
    let row = rows.get(t.key);
    if (!row) {
      row = {
        position: 0,
        team: t.display,
        key: t.key,
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDifference: 0,
        points: 0,
      };
      rows.set(t.key, row);
      displayFor.set(t.key, t.display);
    }
    row.played++;
    row.goalsFor += gf;
    row.goalsAgainst += ga;
    row.goalDifference = row.goalsFor - row.goalsAgainst;
    if (gf > ga) {
      row.wins++;
      row.points += 3;
    } else if (gf < ga) {
      row.losses++;
    } else {
      row.draws++;
      row.points += 1;
    }
  };

  for (const m of pool) {
    bump(m.home, m.homeGoals, m.awayGoals);
    bump(m.away, m.awayGoals, m.homeGoals);
  }

  const table = [...rows.values()].sort(
    (a, b) =>
      b.points - a.points ||
      b.wins - a.wins ||
      b.goalDifference - a.goalDifference ||
      b.goalsFor - a.goalsFor ||
      a.team.localeCompare(b.team),
  );
  table.forEach((r, i) => (r.position = i + 1));
  return table;
}

// ---------------------------------------------------------------- players

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  sortBy?: "overall" | "potential" | "age" | "name";
  limit?: number;
}

function fold(s: string): string {
  return stripDiacritics(s).toLowerCase();
}

export function searchPlayers(ds: Dataset, f: PlayerFilter): Player[] {
  const name = f.name ? fold(f.name) : null;
  const nat = f.nationality ? fold(f.nationality) : null;
  const club = f.club ? fold(f.club) : null;
  const pos = f.position ? f.position.toUpperCase() : null;

  let out = ds.players.filter((p) => {
    if (name && !fold(p.name).includes(name)) return false;
    if (nat && !fold(p.nationality).includes(nat)) return false;
    if (club && !fold(p.club).includes(club)) return false;
    if (pos && p.position.toUpperCase() !== pos) return false;
    if (f.minOverall !== undefined && p.overall < f.minOverall) return false;
    return true;
  });

  const sortBy = f.sortBy ?? "overall";
  out = out.sort((a, b) => {
    switch (sortBy) {
      case "name":
        return a.name.localeCompare(b.name);
      case "age":
        return (a.age ?? 99) - (b.age ?? 99);
      case "potential":
        return (b.potential ?? 0) - (a.potential ?? 0);
      default:
        return b.overall - a.overall;
    }
  });
  return out.slice(0, f.limit ?? 25);
}

// ---------------------------------------------------------------- analytics

export interface CompetitionStats {
  competition: string;
  season?: number;
  matches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
}

export function competitionStats(
  ds: Dataset,
  opts: { competition?: string; season?: number } = {},
): CompetitionStats {
  const comp = resolveCompetition(opts.competition);
  let matches = 0,
    goals = 0,
    hw = 0,
    aw = 0,
    d = 0;
  for (const m of ds.matches) {
    if (comp && m.competition !== comp) continue;
    if (opts.season !== undefined && m.season !== opts.season) continue;
    matches++;
    goals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) hw++;
    else if (m.homeGoals < m.awayGoals) aw++;
    else d++;
  }
  return {
    competition: comp ?? "All competitions",
    season: opts.season,
    matches,
    totalGoals: goals,
    avgGoalsPerMatch: matches ? goals / matches : 0,
    homeWins: hw,
    awayWins: aw,
    draws: d,
    homeWinRate: matches ? hw / matches : 0,
  };
}

export function biggestWins(
  ds: Dataset,
  opts: { competition?: string; season?: number; limit?: number } = {},
): Match[] {
  const comp = resolveCompetition(opts.competition);
  return ds.matches
    .filter(
      (m) =>
        (!comp || m.competition === comp) &&
        (opts.season === undefined || m.season === opts.season),
    )
    .sort(
      (a, b) =>
        Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals) ||
        b.homeGoals + b.awayGoals - (a.homeGoals + a.awayGoals),
    )
    .slice(0, opts.limit ?? 10);
}

/** Best home/away records across teams (minimum number of matches applies). */
export function bestRecords(
  ds: Dataset,
  opts: { venue: "home" | "away"; competition?: string; season?: number; minMatches?: number; limit?: number },
): { team: string; matches: number; wins: number; draws: number; losses: number; winRate: number }[] {
  const comp = resolveCompetition(opts.competition);
  const minMatches = opts.minMatches ?? 10;
  const acc = new Map<string, { team: string; matches: number; wins: number; draws: number; losses: number }>();
  for (const m of ds.matches) {
    if (comp && m.competition !== comp) continue;
    if (opts.season !== undefined && m.season !== opts.season) continue;
    const t = opts.venue === "home" ? m.home : m.away;
    const gf = opts.venue === "home" ? m.homeGoals : m.awayGoals;
    const ga = opts.venue === "home" ? m.awayGoals : m.homeGoals;
    let row = acc.get(t.key);
    if (!row) {
      row = { team: t.display, matches: 0, wins: 0, draws: 0, losses: 0 };
      acc.set(t.key, row);
    }
    row.matches++;
    if (gf > ga) row.wins++;
    else if (gf < ga) row.losses++;
    else row.draws++;
  }
  return [...acc.values()]
    .filter((r) => r.matches >= minMatches)
    .map((r) => ({ ...r, winRate: r.wins / r.matches }))
    .sort((a, b) => b.winRate - a.winRate)
    .slice(0, opts.limit ?? 10);
}

/** Every competition (and seasons) a team appears in. */
export function teamCompetitions(
  ds: Dataset,
  team: string,
): { competition: string; matches: number; seasons: number[] }[] {
  const q = normalizeTeamName(team);
  const acc = new Map<string, { competition: string; matches: number; seasons: Set<number> }>();
  for (const m of ds.matches) {
    if (!matchInvolves(m, q)) continue;
    let row = acc.get(m.competition);
    if (!row) {
      row = { competition: m.competition, matches: 0, seasons: new Set() };
      acc.set(m.competition, row);
    }
    row.matches++;
    if (m.season !== null) row.seasons.add(m.season);
  }
  return [...acc.values()]
    .map((r) => ({
      competition: r.competition,
      matches: r.matches,
      seasons: [...r.seasons].sort((a, b) => a - b),
    }))
    .sort((a, b) => b.matches - a.matches);
}

export { COMPETITIONS };
