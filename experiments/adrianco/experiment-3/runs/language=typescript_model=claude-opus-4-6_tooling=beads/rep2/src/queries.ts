import type { UnifiedMatch, FifaPlayer, TeamStats, HeadToHead } from "./types.js";
import { teamsMatch, normalizeTeamName } from "./normalize.js";
import { loadAllData } from "./data-loader.js";

export function searchMatches(options: {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}): UnifiedMatch[] {
  const { matches } = loadAllData();
  let results = matches;

  if (options.team) {
    results = results.filter(
      (m) => teamsMatch(m.homeTeam, options.team!) || teamsMatch(m.awayTeam, options.team!)
    );
  }

  if (options.homeTeam) {
    results = results.filter((m) => teamsMatch(m.homeTeam, options.homeTeam!));
  }

  if (options.awayTeam) {
    results = results.filter((m) => teamsMatch(m.awayTeam, options.awayTeam!));
  }

  if (options.competition) {
    const comp = options.competition.toLowerCase();
    results = results.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (options.season) {
    results = results.filter((m) => m.season === options.season);
  }

  if (options.dateFrom) {
    results = results.filter((m) => m.datetime >= options.dateFrom!);
  }

  if (options.dateTo) {
    results = results.filter((m) => m.datetime <= options.dateTo!);
  }

  results.sort((a, b) => b.datetime.localeCompare(a.datetime));

  const limit = options.limit || 50;
  return results.slice(0, limit);
}

export function getTeamStats(
  team: string,
  options: { competition?: string; season?: number; homeOnly?: boolean; awayOnly?: boolean } = {}
): TeamStats {
  const { matches } = loadAllData();
  let relevant = matches.filter(
    (m) => teamsMatch(m.homeTeam, team) || teamsMatch(m.awayTeam, team)
  );

  if (options.competition) {
    const comp = options.competition.toLowerCase();
    relevant = relevant.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (options.season) {
    relevant = relevant.filter((m) => m.season === options.season);
  }

  if (options.homeOnly) {
    relevant = relevant.filter((m) => teamsMatch(m.homeTeam, team));
  }

  if (options.awayOnly) {
    relevant = relevant.filter((m) => teamsMatch(m.awayTeam, team));
  }

  let wins = 0,
    draws = 0,
    losses = 0,
    goalsFor = 0,
    goalsAgainst = 0;

  for (const m of relevant) {
    const isHome = teamsMatch(m.homeTeam, team);
    const gf = isHome ? m.homeGoal : m.awayGoal;
    const ga = isHome ? m.awayGoal : m.homeGoal;
    goalsFor += gf;
    goalsAgainst += ga;
    if (gf > ga) wins++;
    else if (gf === ga) draws++;
    else losses++;
  }

  return {
    team: normalizeTeamName(team),
    matches: relevant.length,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    goalDifference: goalsFor - goalsAgainst,
    points: wins * 3 + draws,
    winRate: relevant.length > 0 ? Math.round((wins / relevant.length) * 1000) / 10 : 0,
  };
}

export function getHeadToHead(
  team1: string,
  team2: string,
  options: { competition?: string; season?: number } = {}
): HeadToHead {
  const { matches } = loadAllData();
  let relevant = matches.filter(
    (m) =>
      (teamsMatch(m.homeTeam, team1) && teamsMatch(m.awayTeam, team2)) ||
      (teamsMatch(m.homeTeam, team2) && teamsMatch(m.awayTeam, team1))
  );

  if (options.competition) {
    const comp = options.competition.toLowerCase();
    relevant = relevant.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (options.season) {
    relevant = relevant.filter((m) => m.season === options.season);
  }

  relevant.sort((a, b) => b.datetime.localeCompare(a.datetime));

  let team1Wins = 0,
    team2Wins = 0,
    draws = 0,
    team1Goals = 0,
    team2Goals = 0;

  for (const m of relevant) {
    const isTeam1Home = teamsMatch(m.homeTeam, team1);
    const t1g = isTeam1Home ? m.homeGoal : m.awayGoal;
    const t2g = isTeam1Home ? m.awayGoal : m.homeGoal;
    team1Goals += t1g;
    team2Goals += t2g;
    if (t1g > t2g) team1Wins++;
    else if (t1g === t2g) draws++;
    else team2Wins++;
  }

  return {
    team1: normalizeTeamName(team1),
    team2: normalizeTeamName(team2),
    team1Wins,
    team2Wins,
    draws,
    totalMatches: relevant.length,
    team1Goals,
    team2Goals,
    matches: relevant.slice(0, 20),
  };
}

export function getStandings(
  season: number,
  competition: string = "Brasileirão"
): TeamStats[] {
  const { matches } = loadAllData();
  const comp = competition.toLowerCase();
  const seasonMatches = matches.filter(
    (m) => m.season === season && m.competition.toLowerCase().includes(comp)
  );

  const teamMap = new Map<string, TeamStats>();

  for (const m of seasonMatches) {
    const home = normalizeTeamName(m.homeTeam);
    const away = normalizeTeamName(m.awayTeam);

    if (!teamMap.has(home)) {
      teamMap.set(home, {
        team: home,
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDifference: 0,
        points: 0,
        winRate: 0,
      });
    }

    if (!teamMap.has(away)) {
      teamMap.set(away, {
        team: away,
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDifference: 0,
        points: 0,
        winRate: 0,
      });
    }

    const homeStats = teamMap.get(home)!;
    const awayStats = teamMap.get(away)!;

    homeStats.matches++;
    awayStats.matches++;
    homeStats.goalsFor += m.homeGoal;
    homeStats.goalsAgainst += m.awayGoal;
    awayStats.goalsFor += m.awayGoal;
    awayStats.goalsAgainst += m.homeGoal;

    if (m.homeGoal > m.awayGoal) {
      homeStats.wins++;
      awayStats.losses++;
    } else if (m.homeGoal === m.awayGoal) {
      homeStats.draws++;
      awayStats.draws++;
    } else {
      homeStats.losses++;
      awayStats.wins++;
    }
  }

  for (const stats of teamMap.values()) {
    stats.points = stats.wins * 3 + stats.draws;
    stats.goalDifference = stats.goalsFor - stats.goalsAgainst;
    stats.winRate = stats.matches > 0 ? Math.round((stats.wins / stats.matches) * 1000) / 10 : 0;
  }

  return [...teamMap.values()].sort(
    (a, b) => b.points - a.points || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor
  );
}

export function searchPlayers(options: {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  limit?: number;
}): FifaPlayer[] {
  const { players } = loadAllData();
  let results = players;

  if (options.name) {
    const name = options.name.toLowerCase();
    results = results.filter((p) => p.name.toLowerCase().includes(name));
  }

  if (options.nationality) {
    const nat = options.nationality.toLowerCase();
    results = results.filter((p) => p.nationality.toLowerCase().includes(nat));
  }

  if (options.club) {
    const club = options.club.toLowerCase();
    results = results.filter((p) => p.club.toLowerCase().includes(club));
  }

  if (options.position) {
    const pos = options.position.toUpperCase();
    results = results.filter((p) => p.position.toUpperCase().includes(pos));
  }

  if (options.minOverall !== undefined) {
    results = results.filter((p) => p.overall >= options.minOverall!);
  }

  if (options.maxOverall !== undefined) {
    results = results.filter((p) => p.overall <= options.maxOverall!);
  }

  results.sort((a, b) => b.overall - a.overall);

  const limit = options.limit || 25;
  return results.slice(0, limit);
}

export function getBiggestWins(options: {
  competition?: string;
  season?: number;
  limit?: number;
}): (UnifiedMatch & { goalDiff: number })[] {
  const { matches } = loadAllData();
  let results = matches;

  if (options.competition) {
    const comp = options.competition.toLowerCase();
    results = results.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (options.season) {
    results = results.filter((m) => m.season === options.season);
  }

  const withDiff = results.map((m) => ({
    ...m,
    goalDiff: Math.abs(m.homeGoal - m.awayGoal),
  }));

  withDiff.sort((a, b) => b.goalDiff - a.goalDiff || b.homeGoal + b.awayGoal - (a.homeGoal + a.awayGoal));

  const limit = options.limit || 20;
  return withDiff.slice(0, limit);
}

export function getAverageGoals(options: {
  competition?: string;
  season?: number;
}): { avgGoals: number; totalGoals: number; totalMatches: number; homeWinRate: number; drawRate: number; awayWinRate: number } {
  const { matches } = loadAllData();
  let results = matches;

  if (options.competition) {
    const comp = options.competition.toLowerCase();
    results = results.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (options.season) {
    results = results.filter((m) => m.season === options.season);
  }

  const totalGoals = results.reduce((sum, m) => sum + m.homeGoal + m.awayGoal, 0);
  const homeWins = results.filter((m) => m.homeGoal > m.awayGoal).length;
  const draws = results.filter((m) => m.homeGoal === m.awayGoal).length;
  const awayWins = results.filter((m) => m.awayGoal > m.homeGoal).length;
  const total = results.length;

  return {
    avgGoals: total > 0 ? Math.round((totalGoals / total) * 100) / 100 : 0,
    totalGoals,
    totalMatches: total,
    homeWinRate: total > 0 ? Math.round((homeWins / total) * 1000) / 10 : 0,
    drawRate: total > 0 ? Math.round((draws / total) * 1000) / 10 : 0,
    awayWinRate: total > 0 ? Math.round((awayWins / total) * 1000) / 10 : 0,
  };
}

export function getTopScoringTeams(options: {
  competition?: string;
  season?: number;
  limit?: number;
}): { team: string; goalsScored: number; matches: number; avgGoals: number }[] {
  const { matches } = loadAllData();
  let results = matches;

  if (options.competition) {
    const comp = options.competition.toLowerCase();
    results = results.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (options.season) {
    results = results.filter((m) => m.season === options.season);
  }

  const teamGoals = new Map<string, { goals: number; matches: number }>();

  for (const m of results) {
    const home = normalizeTeamName(m.homeTeam);
    const away = normalizeTeamName(m.awayTeam);

    const hEntry = teamGoals.get(home) || { goals: 0, matches: 0 };
    hEntry.goals += m.homeGoal;
    hEntry.matches++;
    teamGoals.set(home, hEntry);

    const aEntry = teamGoals.get(away) || { goals: 0, matches: 0 };
    aEntry.goals += m.awayGoal;
    aEntry.matches++;
    teamGoals.set(away, aEntry);
  }

  const sorted = [...teamGoals.entries()]
    .map(([team, data]) => ({
      team,
      goalsScored: data.goals,
      matches: data.matches,
      avgGoals: data.matches > 0 ? Math.round((data.goals / data.matches) * 100) / 100 : 0,
    }))
    .sort((a, b) => b.goalsScored - a.goalsScored);

  const limit = options.limit || 20;
  return sorted.slice(0, limit);
}
