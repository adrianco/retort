import {
  NormalizedMatch,
  FifaPlayer,
  TeamStats,
  BRFootballMatch,
} from './types';
import {
  getAllMatches,
  loadBrasileiraoMatches,
  loadCupMatches,
  loadLibertadoresMatches,
  loadHistoricalMatches,
  loadBRFootballMatches,
  loadFifaPlayers,
  teamMatches,
} from './dataLoader';

// ─── Match Queries ────────────────────────────────────────────────────────────

export interface SearchMatchesParams {
  team?: string;
  team1?: string;
  team2?: string;
  competition?: string;
  season?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
}

export function searchMatches(params: SearchMatchesParams): NormalizedMatch[] {
  let matches = getAllMatches();

  if (params.team) {
    matches = matches.filter(
      (m) => teamMatches(params.team!, m.home_team) || teamMatches(params.team!, m.away_team)
    );
  }

  if (params.team1 && params.team2) {
    matches = matches.filter(
      (m) =>
        (teamMatches(params.team1!, m.home_team) && teamMatches(params.team2!, m.away_team)) ||
        (teamMatches(params.team2!, m.home_team) && teamMatches(params.team1!, m.away_team))
    );
  } else if (params.team1) {
    matches = matches.filter(
      (m) => teamMatches(params.team1!, m.home_team) || teamMatches(params.team1!, m.away_team)
    );
  }

  if (params.competition) {
    const comp = params.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (params.season) {
    matches = matches.filter((m) => m.season === params.season);
  }

  if (params.date_from) {
    matches = matches.filter((m) => m.date >= params.date_from!);
  }

  if (params.date_to) {
    matches = matches.filter((m) => m.date <= params.date_to!);
  }

  // Sort by date descending
  matches.sort((a, b) => b.date.localeCompare(a.date));

  const limit = params.limit ?? 50;
  return matches.slice(0, limit);
}

// ─── Team Statistics ──────────────────────────────────────────────────────────

export interface TeamStatsParams {
  team: string;
  competition?: string;
  season?: number;
  home_only?: boolean;
  away_only?: boolean;
}

export function getTeamStats(params: TeamStatsParams): TeamStats {
  let matches = getAllMatches();

  if (params.competition) {
    const comp = params.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (params.season) {
    matches = matches.filter((m) => m.season === params.season);
  }

  const stats: TeamStats = {
    team: params.team,
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goals_for: 0,
    goals_against: 0,
    points: 0,
  };

  for (const m of matches) {
    const isHome = teamMatches(params.team, m.home_team);
    const isAway = teamMatches(params.team, m.away_team);

    if (!isHome && !isAway) continue;
    if (params.home_only && !isHome) continue;
    if (params.away_only && !isAway) continue;

    stats.matches++;

    if (isHome) {
      stats.goals_for += m.home_goal;
      stats.goals_against += m.away_goal;
      if (m.home_goal > m.away_goal) {
        stats.wins++;
        stats.points += 3;
      } else if (m.home_goal === m.away_goal) {
        stats.draws++;
        stats.points += 1;
      } else {
        stats.losses++;
      }
    } else {
      stats.goals_for += m.away_goal;
      stats.goals_against += m.home_goal;
      if (m.away_goal > m.home_goal) {
        stats.wins++;
        stats.points += 3;
      } else if (m.away_goal === m.home_goal) {
        stats.draws++;
        stats.points += 1;
      } else {
        stats.losses++;
      }
    }
  }

  return stats;
}

// ─── Head-to-Head ─────────────────────────────────────────────────────────────

export interface HeadToHeadResult {
  team1: string;
  team2: string;
  total_matches: number;
  team1_wins: number;
  team2_wins: number;
  draws: number;
  team1_goals: number;
  team2_goals: number;
  matches: NormalizedMatch[];
}

export function getHeadToHead(
  team1: string,
  team2: string,
  limit = 20
): HeadToHeadResult {
  const matches = getAllMatches().filter(
    (m) =>
      (teamMatches(team1, m.home_team) && teamMatches(team2, m.away_team)) ||
      (teamMatches(team2, m.home_team) && teamMatches(team1, m.away_team))
  );

  matches.sort((a, b) => b.date.localeCompare(a.date));

  let team1Wins = 0;
  let team2Wins = 0;
  let draws = 0;
  let team1Goals = 0;
  let team2Goals = 0;

  for (const m of matches) {
    const t1IsHome = teamMatches(team1, m.home_team);
    const t1Goals = t1IsHome ? m.home_goal : m.away_goal;
    const t2Goals = t1IsHome ? m.away_goal : m.home_goal;
    team1Goals += t1Goals;
    team2Goals += t2Goals;
    if (t1Goals > t2Goals) team1Wins++;
    else if (t2Goals > t1Goals) team2Wins++;
    else draws++;
  }

  return {
    team1,
    team2,
    total_matches: matches.length,
    team1_wins: team1Wins,
    team2_wins: team2Wins,
    draws,
    team1_goals: team1Goals,
    team2_goals: team2Goals,
    matches: matches.slice(0, limit),
  };
}

// ─── Standings ────────────────────────────────────────────────────────────────

export function getStandings(
  season: number,
  competition = 'Brasileirao'
): TeamStats[] {
  const comp = competition.toLowerCase();
  const matches = getAllMatches().filter(
    (m) => m.season === season && m.competition.toLowerCase().includes(comp)
  );

  const table = new Map<string, TeamStats>();

  function getOrCreate(team: string): TeamStats {
    if (!table.has(team)) {
      table.set(team, {
        team,
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0,
        points: 0,
      });
    }
    return table.get(team)!;
  }

  for (const m of matches) {
    const home = getOrCreate(m.home_team);
    const away = getOrCreate(m.away_team);

    home.matches++;
    away.matches++;
    home.goals_for += m.home_goal;
    home.goals_against += m.away_goal;
    away.goals_for += m.away_goal;
    away.goals_against += m.home_goal;

    if (m.home_goal > m.away_goal) {
      home.wins++;
      home.points += 3;
      away.losses++;
    } else if (m.home_goal === m.away_goal) {
      home.draws++;
      home.points += 1;
      away.draws++;
      away.points += 1;
    } else {
      away.wins++;
      away.points += 3;
      home.losses++;
    }
  }

  return Array.from(table.values()).sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    const gdA = a.goals_for - a.goals_against;
    const gdB = b.goals_for - b.goals_against;
    if (gdB !== gdA) return gdB - gdA;
    return b.goals_for - a.goals_for;
  });
}

// ─── Biggest Wins ─────────────────────────────────────────────────────────────

export function getBiggestWins(
  competition?: string,
  season?: number,
  limit = 10
): NormalizedMatch[] {
  let matches = getAllMatches();

  if (competition) {
    const comp = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  return matches
    .map((m) => ({ ...m, margin: Math.abs(m.home_goal - m.away_goal) }))
    .sort((a: any, b: any) => b.margin - a.margin || (b.home_goal + b.away_goal) - (a.home_goal + a.away_goal))
    .slice(0, limit);
}

// ─── Competition Stats ────────────────────────────────────────────────────────

export interface CompetitionStats {
  competition: string;
  season?: number;
  total_matches: number;
  total_goals: number;
  avg_goals_per_match: number;
  home_wins: number;
  away_wins: number;
  draws: number;
  home_win_rate: number;
}

export function getCompetitionStats(
  competition?: string,
  season?: number
): CompetitionStats {
  let matches = getAllMatches();

  if (competition) {
    const comp = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  let totalGoals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;

  for (const m of matches) {
    totalGoals += m.home_goal + m.away_goal;
    if (m.home_goal > m.away_goal) homeWins++;
    else if (m.away_goal > m.home_goal) awayWins++;
    else draws++;
  }

  const total = matches.length;

  return {
    competition: competition ?? 'All',
    season,
    total_matches: total,
    total_goals: totalGoals,
    avg_goals_per_match: total > 0 ? Math.round((totalGoals / total) * 100) / 100 : 0,
    home_wins: homeWins,
    away_wins: awayWins,
    draws,
    home_win_rate: total > 0 ? Math.round((homeWins / total) * 1000) / 10 : 0,
  };
}

// ─── Player Queries ───────────────────────────────────────────────────────────

export interface SearchPlayersParams {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  min_overall?: number;
  limit?: number;
}

export function searchPlayers(params: SearchPlayersParams): FifaPlayer[] {
  let players = loadFifaPlayers();

  if (params.name) {
    const n = params.name.toLowerCase();
    players = players.filter((p) => p.Name.toLowerCase().includes(n));
  }

  if (params.nationality) {
    const nat = params.nationality.toLowerCase();
    players = players.filter((p) => p.Nationality.toLowerCase().includes(nat));
  }

  if (params.club) {
    const club = params.club.toLowerCase();
    players = players.filter((p) => p.Club.toLowerCase().includes(club));
  }

  if (params.position) {
    const pos = params.position.toLowerCase();
    players = players.filter((p) => p.Position.toLowerCase().includes(pos));
  }

  if (params.min_overall) {
    players = players.filter((p) => p.Overall >= params.min_overall!);
  }

  players.sort((a, b) => b.Overall - a.Overall);

  return players.slice(0, params.limit ?? 20);
}

// ─── Best Home/Away Teams ─────────────────────────────────────────────────────

export function getBestTeams(
  mode: 'home' | 'away' | 'overall',
  competition?: string,
  season?: number,
  limit = 10
): TeamStats[] {
  let matches = getAllMatches();

  if (competition) {
    const comp = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(comp));
  }

  if (season) {
    matches = matches.filter((m) => m.season === season);
  }

  const table = new Map<string, TeamStats>();

  function getOrCreate(team: string): TeamStats {
    if (!table.has(team)) {
      table.set(team, {
        team,
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0,
        points: 0,
      });
    }
    return table.get(team)!;
  }

  for (const m of matches) {
    if (mode === 'home' || mode === 'overall') {
      const home = getOrCreate(m.home_team);
      home.matches++;
      home.goals_for += m.home_goal;
      home.goals_against += m.away_goal;
      if (m.home_goal > m.away_goal) { home.wins++; home.points += 3; }
      else if (m.home_goal === m.away_goal) { home.draws++; home.points += 1; }
      else { home.losses++; }
    }

    if (mode === 'away' || mode === 'overall') {
      const away = getOrCreate(m.away_team);
      away.matches++;
      away.goals_for += m.away_goal;
      away.goals_against += m.home_goal;
      if (m.away_goal > m.home_goal) { away.wins++; away.points += 3; }
      else if (m.away_goal === m.home_goal) { away.draws++; away.points += 1; }
      else { away.losses++; }
    }
  }

  return Array.from(table.values())
    .filter((t) => t.matches >= 5)
    .sort((a, b) => {
      const wrA = a.matches > 0 ? a.wins / a.matches : 0;
      const wrB = b.matches > 0 ? b.wins / b.matches : 0;
      return wrB - wrA;
    })
    .slice(0, limit);
}

// ─── BR Football Extended Stats ───────────────────────────────────────────────

export interface ExtendedMatchStatsResult {
  matches: BRFootballMatch[];
  avg_corners: number;
  avg_shots: number;
  avg_attacks: number;
}

export function getExtendedStats(
  team?: string,
  competition?: string,
  limit = 20
): ExtendedMatchStatsResult {
  let matches = loadBRFootballMatches();

  if (team) {
    matches = matches.filter(
      (m) => teamMatches(team, m.home) || teamMatches(team, m.away)
    );
  }

  if (competition) {
    const comp = competition.toLowerCase();
    matches = matches.filter((m) => m.tournament.toLowerCase().includes(comp));
  }

  const subset = matches.slice(0, limit);
  const n = subset.length || 1;

  const avg_corners = subset.reduce((s, m) => s + m.total_corners, 0) / n;
  const avg_shots = subset.reduce((s, m) => s + m.home_shots + m.away_shots, 0) / n;
  const avg_attacks = subset.reduce((s, m) => s + m.home_attack + m.away_attack, 0) / n;

  return {
    matches: subset,
    avg_corners: Math.round(avg_corners * 10) / 10,
    avg_shots: Math.round(avg_shots * 10) / 10,
    avg_attacks: Math.round(avg_attacks * 10) / 10,
  };
}
