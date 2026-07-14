import { Match, Player, TeamStats, DataStore } from "./types.js";
import { teamsMatch } from "./normalize.js";

export function searchMatches(
  data: DataStore,
  opts: {
    team?: string;
    homeTeam?: string;
    awayTeam?: string;
    opponent?: string;
    competition?: string;
    season?: number;
    dateFrom?: string;
    dateTo?: string;
    limit?: number;
  }
): Match[] {
  let results = data.matches;

  if (opts.team) {
    results = results.filter(
      (m) => teamsMatch(opts.team!, m.homeTeam) || teamsMatch(opts.team!, m.awayTeam)
    );
  }

  if (opts.homeTeam) {
    results = results.filter((m) => teamsMatch(opts.homeTeam!, m.homeTeam));
  }

  if (opts.awayTeam) {
    results = results.filter((m) => teamsMatch(opts.awayTeam!, m.awayTeam));
  }

  if (opts.opponent) {
    results = results.filter(
      (m) => teamsMatch(opts.opponent!, m.homeTeam) || teamsMatch(opts.opponent!, m.awayTeam)
    );
    if (opts.team) {
      results = results.filter(
        (m) =>
          (teamsMatch(opts.team!, m.homeTeam) && teamsMatch(opts.opponent!, m.awayTeam)) ||
          (teamsMatch(opts.team!, m.awayTeam) && teamsMatch(opts.opponent!, m.homeTeam))
      );
    }
  }

  if (opts.competition) {
    const compLower = opts.competition.toLowerCase();
    results = results.filter((m) => m.competition.toLowerCase().includes(compLower));
  }

  if (opts.season) {
    results = results.filter((m) => m.season === opts.season);
  }

  if (opts.dateFrom) {
    results = results.filter((m) => m.date >= opts.dateFrom!);
  }

  if (opts.dateTo) {
    results = results.filter((m) => m.date <= opts.dateTo!);
  }

  results.sort((a, b) => b.date.localeCompare(a.date));

  const limit = opts.limit ?? 50;
  return results.slice(0, limit);
}

export function getTeamStats(
  data: DataStore,
  team: string,
  opts: { competition?: string; season?: number; homeOnly?: boolean; awayOnly?: boolean } = {}
): TeamStats {
  let matches = data.matches.filter(
    (m) => teamsMatch(team, m.homeTeam) || teamsMatch(team, m.awayTeam)
  );

  if (opts.competition) {
    const compLower = opts.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(compLower));
  }

  if (opts.season) {
    matches = matches.filter((m) => m.season === opts.season);
  }

  if (opts.homeOnly) {
    matches = matches.filter((m) => teamsMatch(team, m.homeTeam));
  }

  if (opts.awayOnly) {
    matches = matches.filter((m) => teamsMatch(team, m.awayTeam));
  }

  let wins = 0,
    draws = 0,
    losses = 0,
    goalsFor = 0,
    goalsAgainst = 0;

  for (const m of matches) {
    const isHome = teamsMatch(team, m.homeTeam);
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    goalsFor += gf;
    goalsAgainst += ga;

    if (gf > ga) wins++;
    else if (gf === ga) draws++;
    else losses++;
  }

  return {
    team,
    matches: matches.length,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    points: wins * 3 + draws,
  };
}

export function getHeadToHead(
  data: DataStore,
  team1: string,
  team2: string,
  opts: { competition?: string; season?: number } = {}
): { team1Stats: TeamStats; team2Stats: TeamStats; matches: Match[] } {
  let matches = data.matches.filter(
    (m) =>
      (teamsMatch(team1, m.homeTeam) && teamsMatch(team2, m.awayTeam)) ||
      (teamsMatch(team2, m.homeTeam) && teamsMatch(team1, m.awayTeam))
  );

  if (opts.competition) {
    const compLower = opts.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(compLower));
  }

  if (opts.season) {
    matches = matches.filter((m) => m.season === opts.season);
  }

  matches.sort((a, b) => b.date.localeCompare(a.date));

  let t1Wins = 0,
    t2Wins = 0,
    drs = 0,
    t1gf = 0,
    t1ga = 0;

  for (const m of matches) {
    const t1Home = teamsMatch(team1, m.homeTeam);
    const gf = t1Home ? m.homeGoals : m.awayGoals;
    const ga = t1Home ? m.awayGoals : m.homeGoals;
    t1gf += gf;
    t1ga += ga;
    if (gf > ga) t1Wins++;
    else if (gf === ga) drs++;
    else t2Wins++;
  }

  return {
    team1Stats: {
      team: team1,
      matches: matches.length,
      wins: t1Wins,
      draws: drs,
      losses: t2Wins,
      goalsFor: t1gf,
      goalsAgainst: t1ga,
      points: t1Wins * 3 + drs,
    },
    team2Stats: {
      team: team2,
      matches: matches.length,
      wins: t2Wins,
      draws: drs,
      losses: t1Wins,
      goalsFor: t1ga,
      goalsAgainst: t1gf,
      points: t2Wins * 3 + drs,
    },
    matches: matches.slice(0, 50),
  };
}

export function searchPlayers(
  data: DataStore,
  opts: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    minOverall?: number;
    maxOverall?: number;
    sortBy?: string;
    limit?: number;
  }
): Player[] {
  let results = data.players;

  if (opts.name) {
    const nameLower = opts.name.toLowerCase();
    results = results.filter((p) => p.name.toLowerCase().includes(nameLower));
  }

  if (opts.nationality) {
    const natLower = opts.nationality.toLowerCase();
    results = results.filter((p) => p.nationality.toLowerCase().includes(natLower));
  }

  if (opts.club) {
    const clubLower = opts.club.toLowerCase();
    results = results.filter((p) => p.club.toLowerCase().includes(clubLower));
  }

  if (opts.position) {
    const posLower = opts.position.toLowerCase();
    results = results.filter((p) => p.position.toLowerCase().includes(posLower));
  }

  if (opts.minOverall !== undefined) {
    results = results.filter((p) => p.overall >= opts.minOverall!);
  }

  if (opts.maxOverall !== undefined) {
    results = results.filter((p) => p.overall <= opts.maxOverall!);
  }

  const sortField = opts.sortBy ?? "overall";
  results.sort((a, b) => {
    const aVal = (a as unknown as Record<string, unknown>)[sortField];
    const bVal = (b as unknown as Record<string, unknown>)[sortField];
    if (typeof aVal === "number" && typeof bVal === "number") return bVal - aVal;
    return String(bVal).localeCompare(String(aVal));
  });

  const limit = opts.limit ?? 25;
  return results.slice(0, limit);
}

export function getStandings(
  data: DataStore,
  season: number,
  competition?: string
): TeamStats[] {
  const comp = competition ?? "brasileirão";
  const compLower = comp.toLowerCase();

  const seasonMatches = data.matches.filter(
    (m) => m.season === season && m.competition.toLowerCase().includes(compLower)
  );

  const teamsMap = new Map<string, TeamStats>();

  for (const m of seasonMatches) {
    for (const side of ["home", "away"] as const) {
      const team = side === "home" ? m.homeTeam : m.awayTeam;
      if (!teamsMap.has(team)) {
        teamsMap.set(team, {
          team,
          matches: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          points: 0,
        });
      }
      const stats = teamsMap.get(team)!;
      stats.matches++;
      const gf = side === "home" ? m.homeGoals : m.awayGoals;
      const ga = side === "home" ? m.awayGoals : m.homeGoals;
      stats.goalsFor += gf;
      stats.goalsAgainst += ga;
      if (gf > ga) {
        stats.wins++;
        stats.points += 3;
      } else if (gf === ga) {
        stats.draws++;
        stats.points += 1;
      } else {
        stats.losses++;
      }
    }
  }

  return Array.from(teamsMap.values()).sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.wins !== a.wins) return b.wins - a.wins;
    const aGD = a.goalsFor - a.goalsAgainst;
    const bGD = b.goalsFor - b.goalsAgainst;
    if (bGD !== aGD) return bGD - aGD;
    return b.goalsFor - a.goalsFor;
  });
}

export function getStatistics(
  data: DataStore,
  opts: { competition?: string; season?: number; team?: string } = {}
): {
  totalMatches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
  biggestWins: Match[];
} {
  let matches = data.matches;

  if (opts.competition) {
    const compLower = opts.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(compLower));
  }

  if (opts.season) {
    matches = matches.filter((m) => m.season === opts.season);
  }

  if (opts.team) {
    matches = matches.filter(
      (m) => teamsMatch(opts.team!, m.homeTeam) || teamsMatch(opts.team!, m.awayTeam)
    );
  }

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

  const total = matches.length || 1;

  const sorted = [...matches].sort(
    (a, b) => Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals)
  );

  return {
    totalMatches: matches.length,
    totalGoals,
    avgGoalsPerMatch: Math.round((totalGoals / total) * 100) / 100,
    homeWins,
    awayWins,
    draws,
    homeWinRate: Math.round((homeWins / total) * 1000) / 10,
    awayWinRate: Math.round((awayWins / total) * 1000) / 10,
    drawRate: Math.round((draws / total) * 1000) / 10,
    biggestWins: sorted.slice(0, 10),
  };
}
