import { SoccerData, Match, Player, teamMatches, normalizeTeam, teamKey } from "./data.js";

export type MatchFilter = {
  team?: string;
  team2?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
};

export function findMatches(data: SoccerData, f: MatchFilter): Match[] {
  let results = data.matches.filter((m) => {
    if (f.homeTeam && !teamMatches(f.homeTeam, m.homeTeam)) return false;
    if (f.awayTeam && !teamMatches(f.awayTeam, m.awayTeam)) return false;
    if (f.team && !(teamMatches(f.team, m.homeTeam) || teamMatches(f.team, m.awayTeam))) return false;
    if (f.team2 && !(teamMatches(f.team2, m.homeTeam) || teamMatches(f.team2, m.awayTeam))) return false;
    if (f.competition && !m.competition.toLowerCase().includes(f.competition.toLowerCase())) return false;
    if (f.season !== undefined && m.season !== f.season) return false;
    if (f.dateFrom && m.date < f.dateFrom) return false;
    if (f.dateTo && m.date > f.dateTo) return false;
    return true;
  });
  results = results.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  if (f.limit) results = results.slice(0, f.limit);
  return results;
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
  points: number;
};

export function teamStats(
  data: SoccerData,
  team: string,
  opts: { season?: number; competition?: string; homeOnly?: boolean; awayOnly?: boolean } = {}
): TeamStats {
  const stats: TeamStats = {
    team: normalizeTeam(team),
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    homeWins: 0,
    homeDraws: 0,
    homeLosses: 0,
    awayWins: 0,
    awayDraws: 0,
    awayLosses: 0,
    points: 0,
  };
  for (const m of data.matches) {
    if (opts.season !== undefined && m.season !== opts.season) continue;
    if (opts.competition && !m.competition.toLowerCase().includes(opts.competition.toLowerCase())) continue;
    const isHome = teamMatches(team, m.homeTeam);
    const isAway = teamMatches(team, m.awayTeam);
    if (!isHome && !isAway) continue;
    if (opts.homeOnly && !isHome) continue;
    if (opts.awayOnly && !isAway) continue;
    if (m.homeGoal === null || m.awayGoal === null) continue;
    const gf = isHome ? m.homeGoal : m.awayGoal;
    const ga = isHome ? m.awayGoal : m.homeGoal;
    stats.matches++;
    stats.goalsFor += gf;
    stats.goalsAgainst += ga;
    if (gf > ga) {
      stats.wins++;
      stats.points += 3;
      if (isHome) stats.homeWins++;
      else stats.awayWins++;
    } else if (gf === ga) {
      stats.draws++;
      stats.points += 1;
      if (isHome) stats.homeDraws++;
      else stats.awayDraws++;
    } else {
      stats.losses++;
      if (isHome) stats.homeLosses++;
      else stats.awayLosses++;
    }
  }
  return stats;
}

export type HeadToHead = {
  team1: string;
  team2: string;
  matches: number;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  team1Goals: number;
  team2Goals: number;
  recentMatches: Match[];
};

export function headToHead(data: SoccerData, team1: string, team2: string, limit = 10): HeadToHead {
  const result: HeadToHead = {
    team1: normalizeTeam(team1),
    team2: normalizeTeam(team2),
    matches: 0,
    team1Wins: 0,
    team2Wins: 0,
    draws: 0,
    team1Goals: 0,
    team2Goals: 0,
    recentMatches: [],
  };
  const matches = findMatches(data, { team: team1, team2 });
  for (const m of matches) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    const t1Home = teamMatches(team1, m.homeTeam);
    const t1Goal = t1Home ? m.homeGoal : m.awayGoal;
    const t2Goal = t1Home ? m.awayGoal : m.homeGoal;
    result.matches++;
    result.team1Goals += t1Goal;
    result.team2Goals += t2Goal;
    if (t1Goal > t2Goal) result.team1Wins++;
    else if (t1Goal < t2Goal) result.team2Wins++;
    else result.draws++;
  }
  result.recentMatches = matches.slice(0, limit);
  return result;
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

export function standings(data: SoccerData, season: number, competition = "Brasileirão"): StandingRow[] {
  const teams = new Map<string, StandingRow>();
  const ensure = (t: string): StandingRow => {
    const key = teamKey(t);
    let row = teams.get(key);
    if (!row) {
      row = {
        team: t,
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDiff: 0,
        points: 0,
      };
      teams.set(key, row);
    }
    return row;
  };
  for (const m of data.matches) {
    if (m.season !== season) continue;
    if (!m.competition.toLowerCase().includes(competition.toLowerCase())) continue;
    if (m.homeGoal === null || m.awayGoal === null) continue;
    const h = ensure(m.homeTeam);
    const a = ensure(m.awayTeam);
    h.matches++;
    a.matches++;
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
  const rows = [...teams.values()];
  rows.forEach((r) => (r.goalDiff = r.goalsFor - r.goalsAgainst));
  rows.sort((x, y) => y.points - x.points || y.goalDiff - x.goalDiff || y.goalsFor - x.goalsFor);
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

export function findPlayers(data: SoccerData, f: PlayerFilter): Player[] {
  const nameLower = f.name?.toLowerCase();
  const natLower = f.nationality?.toLowerCase();
  const clubLower = f.club?.toLowerCase();
  const posLower = f.position?.toLowerCase();
  let results = data.players.filter((p) => {
    if (nameLower && !p.name.toLowerCase().includes(nameLower)) return false;
    if (natLower && p.nationality.toLowerCase() !== natLower && !p.nationality.toLowerCase().includes(natLower)) return false;
    if (clubLower && !p.club.toLowerCase().includes(clubLower)) return false;
    if (posLower && p.position.toLowerCase() !== posLower) return false;
    if (f.minOverall !== undefined && (p.overall === null || p.overall < f.minOverall)) return false;
    return true;
  });
  results.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  if (f.limit) results = results.slice(0, f.limit);
  return results;
}

export type OverallStats = {
  totalMatches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
};

export function overallStats(data: SoccerData, opts: { competition?: string; season?: number } = {}): OverallStats {
  let matches = 0;
  let goals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;
  for (const m of data.matches) {
    if (opts.season !== undefined && m.season !== opts.season) continue;
    if (opts.competition && !m.competition.toLowerCase().includes(opts.competition.toLowerCase())) continue;
    if (m.homeGoal === null || m.awayGoal === null) continue;
    matches++;
    goals += m.homeGoal + m.awayGoal;
    if (m.homeGoal > m.awayGoal) homeWins++;
    else if (m.homeGoal < m.awayGoal) awayWins++;
    else draws++;
  }
  return {
    totalMatches: matches,
    totalGoals: goals,
    avgGoalsPerMatch: matches ? goals / matches : 0,
    homeWinRate: matches ? homeWins / matches : 0,
    awayWinRate: matches ? awayWins / matches : 0,
    drawRate: matches ? draws / matches : 0,
  };
}

export function biggestWins(data: SoccerData, opts: { competition?: string; limit?: number } = {}): Match[] {
  const matches = data.matches.filter((m) => {
    if (m.homeGoal === null || m.awayGoal === null) return false;
    if (opts.competition && !m.competition.toLowerCase().includes(opts.competition.toLowerCase())) return false;
    return true;
  });
  matches.sort((a, b) => Math.abs((b.homeGoal ?? 0) - (b.awayGoal ?? 0)) - Math.abs((a.homeGoal ?? 0) - (a.awayGoal ?? 0)));
  return matches.slice(0, opts.limit ?? 10);
}
