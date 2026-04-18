import { Match, Player, TeamStats, HeadToHead } from './types.js';
import { teamMatchesQuery, normalizeTeamName } from './normalize.js';

// ─── Match Queries ────────────────────────────────────────────────────────────

export interface SearchMatchesParams {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}

export function searchMatches(matches: Match[], params: SearchMatchesParams): Match[] {
  let results = matches.filter((m) => {
    if (params.team) {
      const inHome = teamMatchesQuery(m.homeTeam, params.team);
      const inAway = teamMatchesQuery(m.awayTeam, params.team);
      if (!inHome && !inAway) return false;
    }
    if (params.homeTeam && !teamMatchesQuery(m.homeTeam, params.homeTeam)) return false;
    if (params.awayTeam && !teamMatchesQuery(m.awayTeam, params.awayTeam)) return false;
    if (params.competition) {
      const compLower = params.competition.toLowerCase();
      if (!m.competition.toLowerCase().includes(compLower)) return false;
    }
    if (params.season && m.season !== params.season) return false;
    if (params.dateFrom && m.date < params.dateFrom) return false;
    if (params.dateTo && m.date > params.dateTo) return false;
    return true;
  });

  // Sort by date descending
  results.sort((a, b) => b.date.localeCompare(a.date));

  const limit = params.limit ?? 50;
  return results.slice(0, limit);
}

// ─── Head-to-Head ─────────────────────────────────────────────────────────────

export function getHeadToHead(matches: Match[], team1: string, team2: string): HeadToHead {
  const h2h = matches.filter((m) => {
    const t1InHome = teamMatchesQuery(m.homeTeam, team1);
    const t1InAway = teamMatchesQuery(m.awayTeam, team1);
    const t2InHome = teamMatchesQuery(m.homeTeam, team2);
    const t2InAway = teamMatchesQuery(m.awayTeam, team2);
    return (t1InHome && t2InAway) || (t1InAway && t2InHome);
  });

  h2h.sort((a, b) => b.date.localeCompare(a.date));

  let team1Wins = 0;
  let team2Wins = 0;
  let draws = 0;

  const norm1 = normalizeTeamName(team1).toLowerCase();

  for (const m of h2h) {
    const homeIsTeam1 = m.homeTeam.toLowerCase().includes(norm1);
    if (m.homeGoals === m.awayGoals) {
      draws++;
    } else if (homeIsTeam1 ? m.homeGoals > m.awayGoals : m.awayGoals > m.homeGoals) {
      team1Wins++;
    } else {
      team2Wins++;
    }
  }

  return { team1, team2, matches: h2h, team1Wins, team2Wins, draws };
}

// ─── Team Stats ───────────────────────────────────────────────────────────────

export interface GetTeamStatsParams {
  team: string;
  competition?: string;
  season?: number;
  homeOnly?: boolean;
  awayOnly?: boolean;
}

export function getTeamStats(matches: Match[], params: GetTeamStatsParams): TeamStats {
  const filtered = matches.filter((m) => {
    const isHome = teamMatchesQuery(m.homeTeam, params.team);
    const isAway = teamMatchesQuery(m.awayTeam, params.team);
    if (!isHome && !isAway) return false;
    if (params.homeOnly && !isHome) return false;
    if (params.awayOnly && !isAway) return false;
    if (params.competition) {
      if (!m.competition.toLowerCase().includes(params.competition.toLowerCase())) return false;
    }
    if (params.season && m.season !== params.season) return false;
    return true;
  });

  let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;

  for (const m of filtered) {
    const isHome = teamMatchesQuery(m.homeTeam, params.team);
    const teamGoals = isHome ? m.homeGoals : m.awayGoals;
    const oppGoals = isHome ? m.awayGoals : m.homeGoals;
    goalsFor += teamGoals;
    goalsAgainst += oppGoals;
    if (teamGoals > oppGoals) wins++;
    else if (teamGoals === oppGoals) draws++;
    else losses++;
  }

  const total = filtered.length;
  const points = wins * 3 + draws;
  const winRate = total > 0 ? (wins / total) * 100 : 0;

  return {
    team: params.team,
    matches: total,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    points,
    winRate,
  };
}

// ─── Standings ────────────────────────────────────────────────────────────────

export function getStandings(matches: Match[], competition: string, season: number): TeamStats[] {
  const relevant = matches.filter(
    (m) =>
      m.competition.toLowerCase().includes(competition.toLowerCase()) && m.season === season,
  );

  const teams = new Set<string>();
  for (const m of relevant) {
    teams.add(m.homeTeam);
    teams.add(m.awayTeam);
  }

  const standings = Array.from(teams).map((team) =>
    getTeamStats(relevant, { team, competition, season }),
  );

  // Sort by points, then goal difference, then goals for
  standings.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    const gdA = a.goalsFor - a.goalsAgainst;
    const gdB = b.goalsFor - b.goalsAgainst;
    if (gdB !== gdA) return gdB - gdA;
    return b.goalsFor - a.goalsFor;
  });

  return standings;
}

// ─── Player Queries ───────────────────────────────────────────────────────────

export interface SearchPlayersParams {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

export function searchPlayers(players: Player[], params: SearchPlayersParams): Player[] {
  let results = players.filter((p) => {
    if (params.name && !p.name.toLowerCase().includes(params.name.toLowerCase())) return false;
    if (params.nationality && !p.nationality.toLowerCase().includes(params.nationality.toLowerCase())) return false;
    if (params.club && !p.club.toLowerCase().includes(params.club.toLowerCase())) return false;
    if (params.position && !p.position.toLowerCase().includes(params.position.toLowerCase())) return false;
    if (params.minOverall && p.overall < params.minOverall) return false;
    return true;
  });

  // Sort by overall rating descending
  results.sort((a, b) => b.overall - a.overall);

  const limit = params.limit ?? 50;
  return results.slice(0, limit);
}

// ─── Statistics ───────────────────────────────────────────────────────────────

export interface MatchStats {
  totalMatches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  biggestWins: Array<{ match: Match; goalDiff: number }>;
}

export function getStatistics(matches: Match[], competition?: string, season?: number): MatchStats {
  let filtered = matches;
  if (competition) {
    filtered = filtered.filter((m) => m.competition.toLowerCase().includes(competition.toLowerCase()));
  }
  if (season) {
    filtered = filtered.filter((m) => m.season === season);
  }

  const total = filtered.length;
  if (total === 0) {
    return {
      totalMatches: 0, totalGoals: 0, avgGoalsPerMatch: 0,
      homeWins: 0, awayWins: 0, draws: 0, homeWinRate: 0, biggestWins: [],
    };
  }

  let totalGoals = 0, homeWins = 0, awayWins = 0, draws = 0;
  const withDiff = filtered.map((m) => {
    const diff = Math.abs(m.homeGoals - m.awayGoals);
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.awayGoals > m.homeGoals) awayWins++;
    else draws++;
    return { match: m, goalDiff: diff };
  });

  withDiff.sort((a, b) => b.goalDiff - a.goalDiff);

  return {
    totalMatches: total,
    totalGoals,
    avgGoalsPerMatch: parseFloat((totalGoals / total).toFixed(2)),
    homeWins,
    awayWins,
    draws,
    homeWinRate: parseFloat(((homeWins / total) * 100).toFixed(1)),
    biggestWins: withDiff.slice(0, 10),
  };
}

// ─── Best Teams by Metric ─────────────────────────────────────────────────────

export function getBestTeams(
  matches: Match[],
  metric: 'home' | 'away' | 'overall',
  competition?: string,
  season?: number,
  limit = 10,
): TeamStats[] {
  let filtered = matches;
  if (competition) {
    filtered = filtered.filter((m) => m.competition.toLowerCase().includes(competition.toLowerCase()));
  }
  if (season) {
    filtered = filtered.filter((m) => m.season === season);
  }

  const teams = new Set<string>();
  for (const m of filtered) {
    teams.add(m.homeTeam);
    teams.add(m.awayTeam);
  }

  const stats = Array.from(teams).map((team) =>
    getTeamStats(filtered, {
      team,
      homeOnly: metric === 'home',
      awayOnly: metric === 'away',
    }),
  );

  stats.sort((a, b) => b.winRate - a.winRate || b.points - a.points);
  return stats.filter((s) => s.matches >= 3).slice(0, limit);
}
