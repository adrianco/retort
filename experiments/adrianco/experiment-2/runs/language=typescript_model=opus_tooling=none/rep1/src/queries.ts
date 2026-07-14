import { Dataset, Match, Player, normalizeTeam } from "./data.js";

export type MatchFilter = {
  team?: string;
  teamA?: string;
  teamB?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  homeOnly?: boolean;
  awayOnly?: boolean;
  limit?: number;
};

export function findMatches(ds: Dataset, f: MatchFilter): Match[] {
  const team = f.team ? normalizeTeam(f.team) : undefined;
  const a = f.teamA ? normalizeTeam(f.teamA) : undefined;
  const b = f.teamB ? normalizeTeam(f.teamB) : undefined;
  const comp = f.competition?.toLowerCase();

  const out: Match[] = [];
  for (const m of ds.matches) {
    const h = normalizeTeam(m.homeTeam);
    const aw = normalizeTeam(m.awayTeam);
    if (team) {
      if (f.homeOnly && h !== team) continue;
      else if (f.awayOnly && aw !== team) continue;
      else if (!f.homeOnly && !f.awayOnly && h !== team && aw !== team) continue;
    }
    if (a && b) {
      const pair = (h === a && aw === b) || (h === b && aw === a);
      if (!pair) continue;
    }
    if (comp && !m.competition.toLowerCase().includes(comp)) continue;
    if (f.season !== undefined && m.season !== f.season) continue;
    if (f.dateFrom && (!m.date || m.date < f.dateFrom)) continue;
    if (f.dateTo && (!m.date || m.date > f.dateTo)) continue;
    out.push(m);
  }
  out.sort((x, y) => (y.date ?? "").localeCompare(x.date ?? ""));
  if (f.limit && out.length > f.limit) return out.slice(0, f.limit);
  return out;
}

export type TeamStats = {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  homeWins: number;
  homeDraws: number;
  homeLosses: number;
  awayWins: number;
  awayDraws: number;
  awayLosses: number;
  winRate: number;
};

export function teamStats(
  ds: Dataset,
  team: string,
  opts: { season?: number; competition?: string; homeOnly?: boolean; awayOnly?: boolean } = {},
): TeamStats {
  const nt = normalizeTeam(team);
  const s: TeamStats = {
    team,
    matches: 0, wins: 0, draws: 0, losses: 0,
    goalsFor: 0, goalsAgainst: 0,
    homeWins: 0, homeDraws: 0, homeLosses: 0,
    awayWins: 0, awayDraws: 0, awayLosses: 0,
    winRate: 0,
  };
  const comp = opts.competition?.toLowerCase();
  for (const m of ds.matches) {
    if (opts.season !== undefined && m.season !== opts.season) continue;
    if (comp && !m.competition.toLowerCase().includes(comp)) continue;
    const isHome = normalizeTeam(m.homeTeam) === nt;
    const isAway = normalizeTeam(m.awayTeam) === nt;
    if (!isHome && !isAway) continue;
    if (opts.homeOnly && !isHome) continue;
    if (opts.awayOnly && !isAway) continue;
    s.matches++;
    const gf = isHome ? m.homeGoal : m.awayGoal;
    const ga = isHome ? m.awayGoal : m.homeGoal;
    s.goalsFor += gf;
    s.goalsAgainst += ga;
    if (gf > ga) {
      s.wins++;
      if (isHome) s.homeWins++; else s.awayWins++;
    } else if (gf < ga) {
      s.losses++;
      if (isHome) s.homeLosses++; else s.awayLosses++;
    } else {
      s.draws++;
      if (isHome) s.homeDraws++; else s.awayDraws++;
    }
  }
  s.winRate = s.matches ? s.wins / s.matches : 0;
  return s;
}

export type HeadToHead = {
  teamA: string;
  teamB: string;
  matches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
};

export function headToHead(ds: Dataset, teamA: string, teamB: string): HeadToHead {
  const a = normalizeTeam(teamA);
  const b = normalizeTeam(teamB);
  const r: HeadToHead = {
    teamA, teamB, matches: 0,
    teamAWins: 0, teamBWins: 0, draws: 0,
    teamAGoals: 0, teamBGoals: 0,
  };
  for (const m of ds.matches) {
    const h = normalizeTeam(m.homeTeam);
    const aw = normalizeTeam(m.awayTeam);
    let aHome: boolean | null = null;
    if (h === a && aw === b) aHome = true;
    else if (h === b && aw === a) aHome = false;
    else continue;
    r.matches++;
    const aGoals = aHome ? m.homeGoal : m.awayGoal;
    const bGoals = aHome ? m.awayGoal : m.homeGoal;
    r.teamAGoals += aGoals;
    r.teamBGoals += bGoals;
    if (aGoals > bGoals) r.teamAWins++;
    else if (aGoals < bGoals) r.teamBWins++;
    else r.draws++;
  }
  return r;
}

export type StandingRow = {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDiff: number;
  points: number;
};

export function standings(ds: Dataset, season: number, competition = "Brasileirão"): StandingRow[] {
  const comp = competition.toLowerCase();
  const table = new Map<string, StandingRow>();
  const key = (t: string) => normalizeTeam(t);
  const get = (display: string) => {
    const k = key(display);
    let r = table.get(k);
    if (!r) {
      r = { team: display, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, goalDiff: 0, points: 0 };
      table.set(k, r);
    }
    return r;
  };
  for (const m of ds.matches) {
    if (m.season !== season) continue;
    if (!m.competition.toLowerCase().includes(comp)) continue;
    const hr = get(m.homeTeam);
    const ar = get(m.awayTeam);
    hr.matches++; ar.matches++;
    hr.goalsFor += m.homeGoal; hr.goalsAgainst += m.awayGoal;
    ar.goalsFor += m.awayGoal; ar.goalsAgainst += m.homeGoal;
    if (m.homeGoal > m.awayGoal) { hr.wins++; hr.points += 3; ar.losses++; }
    else if (m.homeGoal < m.awayGoal) { ar.wins++; ar.points += 3; hr.losses++; }
    else { hr.draws++; ar.draws++; hr.points += 1; ar.points += 1; }
  }
  const rows = [...table.values()];
  for (const r of rows) r.goalDiff = r.goalsFor - r.goalsAgainst;
  rows.sort((a, b) =>
    b.points - a.points ||
    b.goalDiff - a.goalDiff ||
    b.goalsFor - a.goalsFor ||
    a.team.localeCompare(b.team)
  );
  return rows;
}

export type PlayerFilter = {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
};

export function findPlayers(ds: Dataset, f: PlayerFilter): Player[] {
  const name = f.name?.toLowerCase();
  const nat = f.nationality?.toLowerCase();
  const club = f.club?.toLowerCase();
  const pos = f.position?.toLowerCase();
  const out: Player[] = [];
  for (const p of ds.players) {
    if (name && !p.name.toLowerCase().includes(name)) continue;
    if (nat && p.nationality.toLowerCase() !== nat) continue;
    if (club && !p.club.toLowerCase().includes(club)) continue;
    if (pos && p.position.toLowerCase() !== pos) continue;
    if (f.minOverall !== undefined && (p.overall ?? 0) < f.minOverall) continue;
    out.push(p);
  }
  out.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  return f.limit ? out.slice(0, f.limit) : out;
}

export type GlobalStats = {
  totalMatches: number;
  avgGoalsPerMatch: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
};

export function globalStats(ds: Dataset, filter: { competition?: string; season?: number } = {}): GlobalStats {
  const comp = filter.competition?.toLowerCase();
  let total = 0, goals = 0, home = 0, away = 0, draws = 0;
  for (const m of ds.matches) {
    if (filter.season !== undefined && m.season !== filter.season) continue;
    if (comp && !m.competition.toLowerCase().includes(comp)) continue;
    total++;
    goals += m.homeGoal + m.awayGoal;
    if (m.homeGoal > m.awayGoal) home++;
    else if (m.homeGoal < m.awayGoal) away++;
    else draws++;
  }
  return {
    totalMatches: total,
    avgGoalsPerMatch: total ? goals / total : 0,
    homeWinRate: total ? home / total : 0,
    awayWinRate: total ? away / total : 0,
    drawRate: total ? draws / total : 0,
  };
}

export function biggestWins(ds: Dataset, opts: { competition?: string; limit?: number } = {}): Match[] {
  const comp = opts.competition?.toLowerCase();
  const arr = ds.matches.filter((m) => (comp ? m.competition.toLowerCase().includes(comp) : true));
  arr.sort((a, b) => Math.abs(b.homeGoal - b.awayGoal) - Math.abs(a.homeGoal - a.awayGoal));
  return arr.slice(0, opts.limit ?? 10);
}
