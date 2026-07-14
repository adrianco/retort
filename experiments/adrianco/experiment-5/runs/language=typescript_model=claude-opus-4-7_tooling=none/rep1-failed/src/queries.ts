import type { DataStore } from './dataLoader.js';
import type { Match, Player, TeamRecord, Competition } from './types.js';
import { normalizeTeam, teamMatches, displayTeam } from './normalize.js';

export interface MatchFilter {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  opponent?: string;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  dateFrom?: string;
  dateTo?: string;
  competition?: Competition | string;
  limit?: number;
}

export function findMatches(store: DataStore, f: MatchFilter): Match[] {
  let results = store.matches.filter((m) => {
    if (f.competition && m.competition !== f.competition) return false;
    if (f.season !== undefined && m.season !== f.season) return false;
    if (f.seasonFrom !== undefined && m.season < f.seasonFrom) return false;
    if (f.seasonTo !== undefined && m.season > f.seasonTo) return false;
    if (f.dateFrom && m.date < f.dateFrom) return false;
    if (f.dateTo && m.date > f.dateTo) return false;
    if (f.homeTeam && !teamMatches(f.homeTeam, m.homeTeam)) return false;
    if (f.awayTeam && !teamMatches(f.awayTeam, m.awayTeam)) return false;
    if (f.team && !(teamMatches(f.team, m.homeTeam) || teamMatches(f.team, m.awayTeam))) {
      return false;
    }
    if (f.opponent && !(teamMatches(f.opponent, m.homeTeam) || teamMatches(f.opponent, m.awayTeam))) {
      return false;
    }
    if (f.team && f.opponent) {
      const sameSide =
        (teamMatches(f.team, m.homeTeam) && teamMatches(f.opponent, m.homeTeam)) ||
        (teamMatches(f.team, m.awayTeam) && teamMatches(f.opponent, m.awayTeam));
      if (sameSide) return false;
    }
    return true;
  });
  results = results.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
  if (f.limit !== undefined) results = results.slice(0, f.limit);
  return results;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: Match[];
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
}

export function headToHead(store: DataStore, teamA: string, teamB: string): HeadToHead {
  const matches = findMatches(store, { team: teamA, opponent: teamB });
  let aWins = 0;
  let bWins = 0;
  let draws = 0;
  let aGoals = 0;
  let bGoals = 0;
  for (const m of matches) {
    const aIsHome = teamMatches(teamA, m.homeTeam);
    const aGoal = aIsHome ? m.homeGoals : m.awayGoals;
    const bGoal = aIsHome ? m.awayGoals : m.homeGoals;
    aGoals += aGoal;
    bGoals += bGoal;
    if (aGoal > bGoal) aWins++;
    else if (bGoal > aGoal) bWins++;
    else draws++;
  }
  return {
    teamA: displayTeam(teamA),
    teamB: displayTeam(teamB),
    matches,
    teamAWins: aWins,
    teamBWins: bWins,
    draws,
    teamAGoals: aGoals,
    teamBGoals: bGoals,
  };
}

export interface TeamStatsOptions {
  team: string;
  season?: number;
  competition?: Competition | string;
  venue?: 'home' | 'away' | 'all';
}

export function teamStats(store: DataStore, opts: TeamStatsOptions): TeamRecord {
  const venue = opts.venue ?? 'all';
  const matches = findMatches(store, {
    team: opts.team,
    season: opts.season,
    competition: opts.competition,
  });
  let wins = 0;
  let draws = 0;
  let losses = 0;
  let gf = 0;
  let ga = 0;
  let counted = 0;
  for (const m of matches) {
    const isHome = teamMatches(opts.team, m.homeTeam);
    if (venue === 'home' && !isHome) continue;
    if (venue === 'away' && isHome) continue;
    counted++;
    const teamGoals = isHome ? m.homeGoals : m.awayGoals;
    const oppGoals = isHome ? m.awayGoals : m.homeGoals;
    gf += teamGoals;
    ga += oppGoals;
    if (teamGoals > oppGoals) wins++;
    else if (teamGoals < oppGoals) losses++;
    else draws++;
  }
  return {
    team: displayTeam(opts.team),
    matches: counted,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    points: wins * 3 + draws,
  };
}

export interface StandingsOptions {
  season: number;
  competition?: Competition | string;
}

export function standings(store: DataStore, opts: StandingsOptions): TeamRecord[] {
  const competition = opts.competition ?? 'Brasileirao';
  const matches = store.matches.filter(
    (m) => m.season === opts.season && m.competition === competition
  );
  const records = new Map<string, TeamRecord>();
  const display = new Map<string, string>();
  const get = (team: string): TeamRecord => {
    const key = normalizeTeam(team);
    if (!records.has(key)) {
      records.set(key, {
        team: displayTeam(team),
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        points: 0,
      });
      display.set(key, displayTeam(team));
    }
    return records.get(key)!;
  };
  for (const m of matches) {
    const h = get(m.homeTeam);
    const a = get(m.awayTeam);
    h.matches++;
    a.matches++;
    h.goalsFor += m.homeGoals;
    h.goalsAgainst += m.awayGoals;
    a.goalsFor += m.awayGoals;
    a.goalsAgainst += m.homeGoals;
    if (m.homeGoals > m.awayGoals) {
      h.wins++;
      h.points += 3;
      a.losses++;
    } else if (m.homeGoals < m.awayGoals) {
      a.wins++;
      a.points += 3;
      h.losses++;
    } else {
      h.draws++;
      a.draws++;
      h.points += 1;
      a.points += 1;
    }
  }
  return Array.from(records.values()).sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    const gdA = a.goalsFor - a.goalsAgainst;
    const gdB = b.goalsFor - b.goalsAgainst;
    if (gdB !== gdA) return gdB - gdA;
    if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
    if (b.wins !== a.wins) return b.wins - a.wins;
    return a.team.localeCompare(b.team);
  });
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  limit?: number;
  sortBy?: 'overall' | 'potential' | 'age' | 'name';
}

export function findPlayers(store: DataStore, f: PlayerFilter): Player[] {
  const nameLower = f.name?.toLowerCase();
  const nationLower = f.nationality?.toLowerCase();
  const clubLower = f.club?.toLowerCase();
  const posUpper = f.position?.toUpperCase();
  let results = store.players.filter((p) => {
    if (nameLower && !p.name.toLowerCase().includes(nameLower)) return false;
    if (nationLower && p.nationality.toLowerCase() !== nationLower) return false;
    if (clubLower && !p.club.toLowerCase().includes(clubLower)) return false;
    if (posUpper && p.position.toUpperCase() !== posUpper) return false;
    if (f.minOverall !== undefined && p.overall < f.minOverall) return false;
    if (f.maxOverall !== undefined && p.overall > f.maxOverall) return false;
    return true;
  });
  const sortBy = f.sortBy ?? 'overall';
  results = results.sort((a, b) => {
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    if (sortBy === 'age') return a.age - b.age;
    if (sortBy === 'potential') return b.potential - a.potential;
    return b.overall - a.overall;
  });
  if (f.limit !== undefined) results = results.slice(0, f.limit);
  return results;
}

export interface AggregateStats {
  totalMatches: number;
  averageGoalsPerMatch: number;
  totalGoals: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

export function aggregateStats(store: DataStore, f: MatchFilter = {}): AggregateStats {
  const matches = findMatches(store, f);
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;
  let goals = 0;
  for (const m of matches) {
    goals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }
  const total = matches.length;
  return {
    totalMatches: total,
    totalGoals: goals,
    averageGoalsPerMatch: total ? +(goals / total).toFixed(3) : 0,
    homeWins,
    awayWins,
    draws,
    homeWinRate: total ? +(homeWins / total).toFixed(3) : 0,
    awayWinRate: total ? +(awayWins / total).toFixed(3) : 0,
    drawRate: total ? +(draws / total).toFixed(3) : 0,
  };
}

export interface BiggestMatchOptions extends MatchFilter {
  limit?: number;
}

export function biggestWins(store: DataStore, opts: BiggestMatchOptions = {}): Match[] {
  const limit = opts.limit ?? 10;
  const matches = findMatches(store, { ...opts, limit: undefined });
  return matches
    .slice()
    .sort((a, b) => {
      const da = Math.abs(a.homeGoals - a.awayGoals);
      const db = Math.abs(b.homeGoals - b.awayGoals);
      if (db !== da) return db - da;
      return b.homeGoals + b.awayGoals - (a.homeGoals + a.awayGoals);
    })
    .slice(0, limit);
}

export function listCompetitions(store: DataStore): Competition[] {
  const set = new Set<Competition>();
  for (const m of store.matches) set.add(m.competition);
  return Array.from(set);
}

export function listSeasons(store: DataStore, competition?: Competition | string): number[] {
  const set = new Set<number>();
  for (const m of store.matches) {
    if (competition && m.competition !== competition) continue;
    if (m.season > 0) set.add(m.season);
  }
  return Array.from(set).sort((a, b) => a - b);
}
