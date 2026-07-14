import { teamMatches } from './normalize.js';
import {
  Competition,
  DataStore,
  HeadToHead,
  Match,
  Player,
  StandingsEntry,
  TeamStats,
} from './types.js';

export interface MatchFilter {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  opponent?: string;
  season?: number;
  fromDate?: string;
  toDate?: string;
  competition?: Competition;
}

function matchHasTeam(m: Match, queryRaw: string): boolean {
  return teamMatches(m.homeTeamNorm, queryRaw) || teamMatches(m.awayTeamNorm, queryRaw);
}

export function findMatches(store: DataStore, filter: MatchFilter): Match[] {
  return store.matches
    .filter((m) => {
      if (filter.team && !matchHasTeam(m, filter.team)) return false;
      if (filter.homeTeam && !teamMatches(m.homeTeamNorm, filter.homeTeam)) return false;
      if (filter.awayTeam && !teamMatches(m.awayTeamNorm, filter.awayTeam)) return false;
      if (filter.opponent && !matchHasTeam(m, filter.opponent)) return false;
      if (filter.team && filter.opponent) {
        const ok =
          (teamMatches(m.homeTeamNorm, filter.team) &&
            teamMatches(m.awayTeamNorm, filter.opponent)) ||
          (teamMatches(m.homeTeamNorm, filter.opponent) &&
            teamMatches(m.awayTeamNorm, filter.team));
        if (!ok) return false;
      }
      if (filter.season != null && m.season !== filter.season) return false;
      if (filter.fromDate && m.date < filter.fromDate) return false;
      if (filter.toDate && m.date > filter.toDate) return false;
      if (filter.competition && m.competition !== filter.competition) return false;
      return true;
    })
    .sort((a, b) => a.date.localeCompare(b.date));
}

export function headToHead(
  store: DataStore,
  teamAInput: string,
  teamBInput: string,
  opts: { competition?: Competition; season?: number } = {}
): HeadToHead {
  const matches = store.matches.filter((m) => {
    if (opts.competition && m.competition !== opts.competition) return false;
    if (opts.season != null && m.season !== opts.season) return false;
    return (
      (teamMatches(m.homeTeamNorm, teamAInput) &&
        teamMatches(m.awayTeamNorm, teamBInput)) ||
      (teamMatches(m.homeTeamNorm, teamBInput) &&
        teamMatches(m.awayTeamNorm, teamAInput))
    );
  });

  let aWins = 0;
  let bWins = 0;
  let draws = 0;
  let aGoals = 0;
  let bGoals = 0;
  for (const m of matches) {
    const aIsHome = teamMatches(m.homeTeamNorm, teamAInput);
    const aScore = aIsHome ? m.homeGoals : m.awayGoals;
    const bScore = aIsHome ? m.awayGoals : m.homeGoals;
    aGoals += aScore;
    bGoals += bScore;
    if (aScore > bScore) aWins++;
    else if (bScore > aScore) bWins++;
    else draws++;
  }

  return {
    teamA: teamAInput,
    teamB: teamBInput,
    totalMatches: matches.length,
    teamAWins: aWins,
    teamBWins: bWins,
    draws,
    teamAGoals: aGoals,
    teamBGoals: bGoals,
    matches: matches.sort((a, b) => a.date.localeCompare(b.date)),
  };
}

export interface TeamStatsOptions {
  season?: number;
  competition?: Competition;
  venue?: 'home' | 'away' | 'all';
}

export function teamStats(
  store: DataStore,
  teamInput: string,
  opts: TeamStatsOptions = {}
): TeamStats {
  const venue = opts.venue ?? 'all';

  let played = 0;
  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsAgainst = 0;

  for (const m of store.matches) {
    if (opts.season != null && m.season !== opts.season) continue;
    if (opts.competition && m.competition !== opts.competition) continue;
    const isHome = teamMatches(m.homeTeamNorm, teamInput);
    const isAway = teamMatches(m.awayTeamNorm, teamInput);
    if (!isHome && !isAway) continue;
    if (venue === 'home' && !isHome) continue;
    if (venue === 'away' && !isAway) continue;
    const tFor = isHome ? m.homeGoals : m.awayGoals;
    const tAg = isHome ? m.awayGoals : m.homeGoals;
    played++;
    goalsFor += tFor;
    goalsAgainst += tAg;
    if (tFor > tAg) wins++;
    else if (tFor < tAg) losses++;
    else draws++;
  }

  const points = wins * 3 + draws;
  return {
    team: teamInput,
    played,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    goalDifference: goalsFor - goalsAgainst,
    points,
    winRate: played > 0 ? wins / played : 0,
  };
}

export function computeStandings(
  store: DataStore,
  competition: Competition,
  season: number
): StandingsEntry[] {
  const teamMap = new Map<string, { name: string; stats: TeamStats }>();

  const ensure = (norm: string, display: string) => {
    if (!teamMap.has(norm)) {
      teamMap.set(norm, {
        name: display,
        stats: {
          team: display,
          played: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          goalDifference: 0,
          points: 0,
          winRate: 0,
        },
      });
    }
    return teamMap.get(norm)!;
  };

  for (const m of store.matches) {
    if (m.competition !== competition || m.season !== season) continue;
    const home = ensure(m.homeTeamNorm, m.homeTeam);
    const away = ensure(m.awayTeamNorm, m.awayTeam);
    home.stats.played++;
    away.stats.played++;
    home.stats.goalsFor += m.homeGoals;
    home.stats.goalsAgainst += m.awayGoals;
    away.stats.goalsFor += m.awayGoals;
    away.stats.goalsAgainst += m.homeGoals;
    if (m.homeGoals > m.awayGoals) {
      home.stats.wins++;
      home.stats.points += 3;
      away.stats.losses++;
    } else if (m.homeGoals < m.awayGoals) {
      away.stats.wins++;
      away.stats.points += 3;
      home.stats.losses++;
    } else {
      home.stats.draws++;
      home.stats.points++;
      away.stats.draws++;
      away.stats.points++;
    }
  }

  const entries = Array.from(teamMap.values()).map((t) => ({
    ...t.stats,
    goalDifference: t.stats.goalsFor - t.stats.goalsAgainst,
    winRate: t.stats.played > 0 ? t.stats.wins / t.stats.played : 0,
  }));

  entries.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.goalDifference !== a.goalDifference)
      return b.goalDifference - a.goalDifference;
    if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
    if (b.wins !== a.wins) return b.wins - a.wins;
    return a.team.localeCompare(b.team);
  });

  return entries.map((e, i) => ({ ...e, position: i + 1 }));
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  limit?: number;
}

export function findPlayers(store: DataStore, filter: PlayerFilter): Player[] {
  const nameLc = filter.name?.toLowerCase();
  const nationLc = filter.nationality?.toLowerCase();
  const posLc = filter.position?.toLowerCase();

  let results = store.players.filter((p) => {
    if (nameLc && !p.name?.toLowerCase().includes(nameLc)) return false;
    if (nationLc && p.nationality?.toLowerCase() !== nationLc) return false;
    if (filter.club && p.clubNorm && !teamMatches(p.clubNorm, filter.club)) return false;
    if (filter.club && !p.clubNorm) return false;
    if (posLc && p.position?.toLowerCase() !== posLc) return false;
    if (filter.minOverall != null && (p.overall ?? 0) < filter.minOverall)
      return false;
    if (filter.maxOverall != null && (p.overall ?? 0) > filter.maxOverall)
      return false;
    return true;
  });

  results.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  if (filter.limit != null) results = results.slice(0, filter.limit);
  return results;
}

export function biggestWins(
  store: DataStore,
  opts: {
    competition?: Competition;
    season?: number;
    limit?: number;
  } = {}
): Match[] {
  const limit = opts.limit ?? 10;
  return store.matches
    .filter((m) => {
      if (opts.competition && m.competition !== opts.competition) return false;
      if (opts.season != null && m.season !== opts.season) return false;
      return true;
    })
    .map((m) => ({ m, diff: Math.abs(m.homeGoals - m.awayGoals) }))
    .sort((a, b) => {
      if (b.diff !== a.diff) return b.diff - a.diff;
      const bTotal = b.m.homeGoals + b.m.awayGoals;
      const aTotal = a.m.homeGoals + a.m.awayGoals;
      return bTotal - aTotal;
    })
    .slice(0, limit)
    .map((x) => x.m);
}

export interface AggregateStats {
  totalMatches: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

export function aggregateStats(
  store: DataStore,
  opts: { competition?: Competition; season?: number } = {}
): AggregateStats {
  let total = 0;
  let goals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;
  for (const m of store.matches) {
    if (opts.competition && m.competition !== opts.competition) continue;
    if (opts.season != null && m.season !== opts.season) continue;
    total++;
    goals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.awayGoals > m.homeGoals) awayWins++;
    else draws++;
  }
  return {
    totalMatches: total,
    totalGoals: goals,
    averageGoalsPerMatch: total > 0 ? goals / total : 0,
    homeWins,
    awayWins,
    draws,
    homeWinRate: total > 0 ? homeWins / total : 0,
    awayWinRate: total > 0 ? awayWins / total : 0,
    drawRate: total > 0 ? draws / total : 0,
  };
}

export function topScoringTeams(
  store: DataStore,
  opts: { competition?: Competition; season?: number; limit?: number } = {}
): Array<{ team: string; goalsFor: number; played: number }> {
  const limit = opts.limit ?? 10;
  const tally = new Map<string, { team: string; goalsFor: number; played: number }>();
  for (const m of store.matches) {
    if (opts.competition && m.competition !== opts.competition) continue;
    if (opts.season != null && m.season !== opts.season) continue;
    const h = tally.get(m.homeTeamNorm) ?? {
      team: m.homeTeam,
      goalsFor: 0,
      played: 0,
    };
    h.goalsFor += m.homeGoals;
    h.played++;
    tally.set(m.homeTeamNorm, h);
    const a = tally.get(m.awayTeamNorm) ?? {
      team: m.awayTeam,
      goalsFor: 0,
      played: 0,
    };
    a.goalsFor += m.awayGoals;
    a.played++;
    tally.set(m.awayTeamNorm, a);
  }
  return Array.from(tally.values())
    .sort((a, b) => b.goalsFor - a.goalsFor)
    .slice(0, limit);
}

export function clubRoster(
  store: DataStore,
  clubInput: string
): { club: string; players: Player[]; averageOverall: number } {
  const players = store.players
    .filter((p) => p.clubNorm && teamMatches(p.clubNorm, clubInput))
    .sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
  const avg =
    players.length > 0
      ? players.reduce((s, p) => s + (p.overall ?? 0), 0) / players.length
      : 0;
  return { club: clubInput, players, averageOverall: avg };
}
