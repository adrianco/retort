import {
  DataStore,
  BrasileiraoMatch,
  CupMatch,
  LibertadoresMatch,
  HistoricalMatch,
  ExtendedMatch,
  FifaPlayer,
  normalizeTeamName,
} from './data-loader';

function teamMatches(team: string, name: string): boolean {
  const t = team.toLowerCase();
  const n = name.toLowerCase();
  return t.includes(n) || n.includes(t);
}

function parseDate(dt: string): Date | null {
  if (!dt) return null;
  // Try ISO: 2023-09-24 or 2023-09-24 20:00:00
  if (/^\d{4}-\d{2}-\d{2}/.test(dt)) {
    const d = new Date(dt.substring(0, 10));
    return isNaN(d.getTime()) ? null : d;
  }
  // Try Brazilian: 29/03/2003
  if (/^\d{2}\/\d{2}\/\d{4}/.test(dt)) {
    const [day, month, year] = dt.split('/');
    const d = new Date(`${year}-${month}-${day}`);
    return isNaN(d.getTime()) ? null : d;
  }
  return null;
}

export interface UnifiedMatch {
  competition: string;
  date: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  extra: string;
}

function brasileiraoToUnified(m: BrasileiraoMatch): UnifiedMatch {
  return {
    competition: 'Brasileirão Serie A',
    date: m.datetime.substring(0, 10),
    home_team: m.home_team,
    away_team: m.away_team,
    home_goal: m.home_goal,
    away_goal: m.away_goal,
    season: m.season,
    extra: `Round ${m.round}`,
  };
}

function cupToUnified(m: CupMatch): UnifiedMatch {
  return {
    competition: 'Copa do Brasil',
    date: m.datetime.substring(0, 10),
    home_team: m.home_team,
    away_team: m.away_team,
    home_goal: m.home_goal,
    away_goal: m.away_goal,
    season: m.season,
    extra: `Round: ${m.round}`,
  };
}

function libertadoresToUnified(m: LibertadoresMatch): UnifiedMatch {
  return {
    competition: 'Copa Libertadores',
    date: m.datetime.substring(0, 10),
    home_team: m.home_team,
    away_team: m.away_team,
    home_goal: m.home_goal,
    away_goal: m.away_goal,
    season: m.season,
    extra: m.stage,
  };
}

function historicalToUnified(m: HistoricalMatch): UnifiedMatch {
  let dateStr = m.date;
  if (/^\d{2}\/\d{2}\/\d{4}/.test(m.date)) {
    const [day, month, year] = m.date.split('/');
    dateStr = `${year}-${month}-${day}`;
  }
  return {
    competition: 'Brasileirão (Historical)',
    date: dateStr,
    home_team: m.home_team,
    away_team: m.away_team,
    home_goal: m.home_goal,
    away_goal: m.away_goal,
    season: m.year,
    extra: `Round ${m.round}, Arena: ${m.arena}`,
  };
}

function extendedToUnified(m: ExtendedMatch): UnifiedMatch {
  return {
    competition: m.tournament,
    date: m.date,
    home_team: m.home,
    away_team: m.away,
    home_goal: m.home_goal,
    away_goal: m.away_goal,
    season: m.date ? parseInt(m.date.substring(0, 4), 10) : 0,
    extra: `Shots: ${m.home_shots}-${m.away_shots}, Corners: ${m.total_corners}`,
  };
}

export interface MatchQueryParams {
  team?: string;
  home_team?: string;
  away_team?: string;
  season?: number;
  date_from?: string;
  date_to?: string;
  competition?: string;
  limit?: number;
}

export function queryMatches(store: DataStore, params: MatchQueryParams): UnifiedMatch[] {
  const limit = params.limit ?? 50;
  const results: UnifiedMatch[] = [];

  const compFilter = params.competition?.toLowerCase();

  function matchesComp(comp: string): boolean {
    if (!compFilter) return true;
    return comp.toLowerCase().includes(compFilter);
  }

  function matchesTeamFilter(home: string, away: string): boolean {
    if (params.home_team && params.away_team) {
      return (teamMatches(home, params.home_team) && teamMatches(away, params.away_team)) ||
             (teamMatches(home, params.away_team) && teamMatches(away, params.home_team));
    }
    if (params.home_team) return teamMatches(home, params.home_team) || teamMatches(away, params.home_team);
    if (params.away_team) return teamMatches(home, params.away_team) || teamMatches(away, params.away_team);
    if (params.team) return teamMatches(home, params.team) || teamMatches(away, params.team);
    return true;
  }

  function matchesDate(dateStr: string): boolean {
    if (!params.date_from && !params.date_to) return true;
    const d = parseDate(dateStr);
    if (!d) return false; // invalid/missing date excluded when filter is active
    if (params.date_from) {
      const from = parseDate(params.date_from);
      if (from && d < from) return false;
    }
    if (params.date_to) {
      const to = parseDate(params.date_to);
      if (to && d > to) return false;
    }
    return true;
  }

  function matchesSeason(season: number): boolean {
    if (!params.season) return true;
    return season === params.season;
  }

  // Brasileirão
  if (matchesComp('brasileirão') || matchesComp('brasileirao') || matchesComp('serie a') || !compFilter) {
    for (const m of store.brasileirao) {
      if (matchesTeamFilter(m.home_team, m.away_team) &&
          matchesSeason(m.season) &&
          matchesDate(m.datetime)) {
        results.push(brasileiraoToUnified(m));
      }
    }
  }

  // Copa do Brasil
  if (matchesComp('copa do brasil') || matchesComp('copa brasil') || matchesComp('cup') || !compFilter) {
    for (const m of store.copa) {
      if (matchesTeamFilter(m.home_team, m.away_team) &&
          matchesSeason(m.season) &&
          matchesDate(m.datetime)) {
        results.push(cupToUnified(m));
      }
    }
  }

  // Libertadores
  if (matchesComp('libertadores') || !compFilter) {
    for (const m of store.libertadores) {
      if (matchesTeamFilter(m.home_team, m.away_team) &&
          matchesSeason(m.season) &&
          matchesDate(m.datetime)) {
        results.push(libertadoresToUnified(m));
      }
    }
  }

  // Historical (only if not duplicating brasileirao)
  if (matchesComp('histórico') || matchesComp('historico') || matchesComp('historical') ||
      matchesComp('brasileirão') || matchesComp('brasileirao') || !compFilter) {
    for (const m of store.historical) {
      if (matchesTeamFilter(m.home_team, m.away_team) &&
          matchesSeason(m.year) &&
          matchesDate(m.date)) {
        results.push(historicalToUnified(m));
      }
    }
  }

  // Extended
  if (!compFilter) {
    for (const m of store.extended) {
      const extSeason = m.date ? parseInt(m.date.substring(0, 4), 10) : 0;
      if (matchesTeamFilter(m.home, m.away) &&
          matchesSeason(isNaN(extSeason) ? 0 : extSeason) &&
          matchesDate(m.date)) {
        results.push(extendedToUnified(m));
      }
    }
  }

  // Sort by date descending, deduplicate by competition+date+teams
  results.sort((a, b) => b.date.localeCompare(a.date));

  const seen = new Set<string>();
  const deduped: UnifiedMatch[] = [];
  for (const r of results) {
    const key = `${r.competition}|${r.date}|${r.home_team}|${r.away_team}`;
    if (!seen.has(key)) {
      seen.add(key);
      deduped.push(r);
    }
  }

  return deduped.slice(0, limit);
}

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  points: number;
  win_rate: number;
  home_wins: number;
  home_matches: number;
  away_wins: number;
  away_matches: number;
}

export function getTeamStats(store: DataStore, teamName: string, season?: number, competition?: string): TeamStats {
  const stats: TeamStats = {
    team: teamName,
    matches: 0, wins: 0, draws: 0, losses: 0,
    goals_for: 0, goals_against: 0, points: 0, win_rate: 0,
    home_wins: 0, home_matches: 0, away_wins: 0, away_matches: 0,
  };

  const matches = queryMatches(store, { team: teamName, season, competition, limit: 10000 });

  for (const m of matches) {
    const isHome = teamMatches(m.home_team, teamName);
    const gf = isHome ? m.home_goal : m.away_goal;
    const ga = isHome ? m.away_goal : m.home_goal;

    stats.matches++;
    stats.goals_for += gf;
    stats.goals_against += ga;

    if (isHome) stats.home_matches++;
    else stats.away_matches++;

    if (gf > ga) {
      stats.wins++;
      stats.points += 3;
      if (isHome) stats.home_wins++;
      else stats.away_wins++;
    } else if (gf === ga) {
      stats.draws++;
      stats.points += 1;
    } else {
      stats.losses++;
    }
  }

  stats.win_rate = stats.matches > 0 ? Math.round((stats.wins / stats.matches) * 1000) / 10 : 0;
  return stats;
}

export interface HeadToHeadResult {
  team1: string;
  team2: string;
  matches: UnifiedMatch[];
  team1_wins: number;
  team2_wins: number;
  draws: number;
  team1_goals: number;
  team2_goals: number;
}

export function getHeadToHead(store: DataStore, team1: string, team2: string, limit = 20): HeadToHeadResult {
  const matches = queryMatches(store, { home_team: team1, away_team: team2, limit: 10000 });

  let t1wins = 0, t2wins = 0, draws = 0, t1goals = 0, t2goals = 0;

  for (const m of matches) {
    const t1home = teamMatches(m.home_team, team1);
    const gf1 = t1home ? m.home_goal : m.away_goal;
    const gf2 = t1home ? m.away_goal : m.home_goal;
    t1goals += gf1;
    t2goals += gf2;
    if (gf1 > gf2) t1wins++;
    else if (gf2 > gf1) t2wins++;
    else draws++;
  }

  return {
    team1, team2,
    matches: matches.slice(0, limit),
    team1_wins: t1wins,
    team2_wins: t2wins,
    draws,
    team1_goals: t1goals,
    team2_goals: t2goals,
  };
}

export interface StandingsEntry {
  position: number;
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  points: number;
}

export function getStandings(store: DataStore, season: number, competition = 'brasileirao'): StandingsEntry[] {
  const teamMap = new Map<string, Omit<StandingsEntry, 'position'>>();

  function ensure(team: string) {
    if (!teamMap.has(team)) {
      teamMap.set(team, {
        team, matches: 0, wins: 0, draws: 0, losses: 0,
        goals_for: 0, goals_against: 0, goal_diff: 0, points: 0,
      });
    }
    return teamMap.get(team)!;
  }

  function processMatch(home: string, away: string, hg: number, ag: number) {
    const h = ensure(home);
    const a = ensure(away);
    h.matches++; a.matches++;
    h.goals_for += hg; h.goals_against += ag;
    a.goals_for += ag; a.goals_against += hg;
    if (hg > ag) {
      h.wins++; h.points += 3; a.losses++;
    } else if (hg === ag) {
      h.draws++; h.points += 1; a.draws++; a.points += 1;
    } else {
      a.wins++; a.points += 3; h.losses++;
    }
    h.goal_diff = h.goals_for - h.goals_against;
    a.goal_diff = a.goals_for - a.goals_against;
  }

  const compLower = competition.toLowerCase();
  if (compLower.includes('brasileirao') || compLower.includes('serie a') || compLower.includes('brasileirão')) {
    for (const m of store.brasileirao) {
      if (m.season === season) processMatch(m.home_team, m.away_team, m.home_goal, m.away_goal);
    }
    for (const m of store.historical) {
      if (m.year === season) processMatch(m.home_team, m.away_team, m.home_goal, m.away_goal);
    }
  } else if (compLower.includes('copa') && compLower.includes('brasil')) {
    for (const m of store.copa) {
      if (m.season === season) processMatch(m.home_team, m.away_team, m.home_goal, m.away_goal);
    }
  } else if (compLower.includes('libertadores')) {
    for (const m of store.libertadores) {
      if (m.season === season) processMatch(m.home_team, m.away_team, m.home_goal, m.away_goal);
    }
  }

  const sorted = Array.from(teamMap.values()).sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.goal_diff !== a.goal_diff) return b.goal_diff - a.goal_diff;
    return b.goals_for - a.goals_for;
  });

  return sorted.map((t, i) => ({ position: i + 1, ...t }));
}

export interface PlayerQueryParams {
  name?: string;
  nationality?: string;
  club?: string;
  min_overall?: number;
  position?: string;
  limit?: number;
}

export function queryPlayers(store: DataStore, params: PlayerQueryParams): FifaPlayer[] {
  let players = store.players;

  if (params.name) {
    const n = params.name.toLowerCase();
    players = players.filter(p => p.name.toLowerCase().includes(n));
  }
  if (params.nationality) {
    const nat = params.nationality.toLowerCase();
    players = players.filter(p => p.nationality.toLowerCase().includes(nat));
  }
  if (params.club) {
    const club = params.club.toLowerCase();
    players = players.filter(p => p.club.toLowerCase().includes(club));
  }
  if (params.min_overall) {
    players = players.filter(p => p.overall >= (params.min_overall ?? 0));
  }
  if (params.position) {
    const pos = params.position.toUpperCase();
    players = players.filter(p => p.position.toUpperCase().includes(pos));
  }

  players.sort((a, b) => b.overall - a.overall);
  return players.slice(0, params.limit ?? 20);
}

export interface BiggestWin {
  competition: string;
  date: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  goal_diff: number;
  season: number;
}

export function getBiggestWins(store: DataStore, limit = 10): BiggestWin[] {
  const all = queryMatches(store, { limit: 100000 });
  return all
    .map(m => ({ ...m, goal_diff: Math.abs(m.home_goal - m.away_goal) }))
    .filter(m => m.goal_diff > 0)
    .sort((a, b) => b.goal_diff - a.goal_diff)
    .slice(0, limit);
}

export interface LeagueStats {
  competition: string;
  total_matches: number;
  total_goals: number;
  avg_goals_per_match: number;
  home_wins: number;
  away_wins: number;
  draws: number;
  home_win_rate: number;
}

export function getLeagueStats(store: DataStore, competition?: string): LeagueStats {
  const matches = queryMatches(store, { competition, limit: 100000 });

  let goals = 0, homeWins = 0, awayWins = 0, draws = 0;
  for (const m of matches) {
    goals += m.home_goal + m.away_goal;
    if (m.home_goal > m.away_goal) homeWins++;
    else if (m.away_goal > m.home_goal) awayWins++;
    else draws++;
  }

  const total = matches.length;
  return {
    competition: competition || 'All Competitions',
    total_matches: total,
    total_goals: goals,
    avg_goals_per_match: total > 0 ? Math.round((goals / total) * 100) / 100 : 0,
    home_wins: homeWins,
    away_wins: awayWins,
    draws,
    home_win_rate: total > 0 ? Math.round((homeWins / total) * 1000) / 10 : 0,
  };
}

export function getTopScoringTeams(store: DataStore, season?: number, competition?: string, limit = 10): Array<{team: string; goals: number; matches: number; avg: number}> {
  const matches = queryMatches(store, { season, competition, limit: 100000 });
  const teamGoals = new Map<string, { goals: number; matches: number }>();

  for (const m of matches) {
    const h = teamGoals.get(m.home_team) ?? { goals: 0, matches: 0 };
    h.goals += m.home_goal; h.matches++;
    teamGoals.set(m.home_team, h);

    const a = teamGoals.get(m.away_team) ?? { goals: 0, matches: 0 };
    a.goals += m.away_goal; a.matches++;
    teamGoals.set(m.away_team, a);
  }

  return Array.from(teamGoals.entries())
    .map(([team, { goals, matches }]) => ({
      team, goals, matches,
      avg: matches > 0 ? Math.round((goals / matches) * 100) / 100 : 0,
    }))
    .sort((a, b) => b.goals - a.goals)
    .slice(0, limit);
}
