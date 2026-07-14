import type { Match, Player, DataStore, TeamRecord, Competition } from './types.js';
import { teamKey, teamMatches, normalizeTeamName, stripAccents } from './normalize.js';

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

export function findMatches(store: DataStore, filter: MatchFilter): Match[] {
  let results = store.matches;

  if (filter.competition) {
    const target = String(filter.competition).toLowerCase();
    results = results.filter((m) => m.competition.toLowerCase().includes(target));
  }
  if (filter.season !== undefined) {
    results = results.filter((m) => m.season === filter.season);
  }
  if (filter.seasonFrom !== undefined) {
    results = results.filter((m) => m.season >= filter.seasonFrom!);
  }
  if (filter.seasonTo !== undefined) {
    results = results.filter((m) => m.season <= filter.seasonTo!);
  }
  if (filter.dateFrom) {
    results = results.filter((m) => m.date >= filter.dateFrom!);
  }
  if (filter.dateTo) {
    results = results.filter((m) => m.date <= filter.dateTo!);
  }
  if (filter.homeTeam) {
    results = results.filter((m) => teamMatches(filter.homeTeam!, m.homeTeam));
  }
  if (filter.awayTeam) {
    results = results.filter((m) => teamMatches(filter.awayTeam!, m.awayTeam));
  }
  if (filter.team) {
    results = results.filter(
      (m) => teamMatches(filter.team!, m.homeTeam) || teamMatches(filter.team!, m.awayTeam),
    );
  }
  if (filter.opponent) {
    results = results.filter(
      (m) => teamMatches(filter.opponent!, m.homeTeam) || teamMatches(filter.opponent!, m.awayTeam),
    );
  }

  results = results.slice().sort((a, b) => b.date.localeCompare(a.date));

  if (filter.limit && filter.limit > 0) {
    results = results.slice(0, filter.limit);
  }
  return results;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  totalMatches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  matches: Match[];
}

export function headToHead(store: DataStore, teamA: string, teamB: string, limit = 50): HeadToHead {
  const matches = store.matches.filter(
    (m) =>
      (teamMatches(teamA, m.homeTeam) && teamMatches(teamB, m.awayTeam)) ||
      (teamMatches(teamB, m.homeTeam) && teamMatches(teamA, m.awayTeam)),
  );

  let teamAWins = 0;
  let teamBWins = 0;
  let draws = 0;
  let teamAGoals = 0;
  let teamBGoals = 0;

  for (const m of matches) {
    const aIsHome = teamMatches(teamA, m.homeTeam);
    const aGoals = aIsHome ? m.homeGoals : m.awayGoals;
    const bGoals = aIsHome ? m.awayGoals : m.homeGoals;
    teamAGoals += aGoals;
    teamBGoals += bGoals;
    if (aGoals > bGoals) teamAWins++;
    else if (bGoals > aGoals) teamBWins++;
    else draws++;
  }

  const sorted = matches.slice().sort((a, b) => b.date.localeCompare(a.date));

  return {
    teamA: normalizeTeamName(teamA),
    teamB: normalizeTeamName(teamB),
    totalMatches: matches.length,
    teamAWins,
    teamBWins,
    draws,
    teamAGoals,
    teamBGoals,
    matches: sorted.slice(0, limit),
  };
}

export interface TeamStatsOptions {
  team: string;
  season?: number;
  competition?: string;
  venue?: 'home' | 'away' | 'all';
}

export interface TeamStats extends TeamRecord {
  homeMatches: number;
  awayMatches: number;
  homeWins: number;
  awayWins: number;
  winRate: number;
}

export function teamStats(store: DataStore, options: TeamStatsOptions): TeamStats {
  const venue = options.venue ?? 'all';
  let matches = store.matches.filter(
    (m) => teamMatches(options.team, m.homeTeam) || teamMatches(options.team, m.awayTeam),
  );
  if (options.season !== undefined) {
    matches = matches.filter((m) => m.season === options.season);
  }
  if (options.competition) {
    const c = options.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(c));
  }
  if (venue === 'home') {
    matches = matches.filter((m) => teamMatches(options.team, m.homeTeam));
  } else if (venue === 'away') {
    matches = matches.filter((m) => teamMatches(options.team, m.awayTeam));
  }

  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsAgainst = 0;
  let homeMatches = 0;
  let awayMatches = 0;
  let homeWins = 0;
  let awayWins = 0;

  for (const m of matches) {
    const isHome = teamMatches(options.team, m.homeTeam);
    const teamGoals = isHome ? m.homeGoals : m.awayGoals;
    const oppGoals = isHome ? m.awayGoals : m.homeGoals;
    goalsFor += teamGoals;
    goalsAgainst += oppGoals;
    if (isHome) homeMatches++;
    else awayMatches++;

    if (teamGoals > oppGoals) {
      wins++;
      if (isHome) homeWins++;
      else awayWins++;
    } else if (teamGoals < oppGoals) {
      losses++;
    } else {
      draws++;
    }
  }

  const total = matches.length;
  return {
    team: normalizeTeamName(options.team),
    matches: total,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    goalDifference: goalsFor - goalsAgainst,
    points: wins * 3 + draws,
    homeMatches,
    awayMatches,
    homeWins,
    awayWins,
    winRate: total === 0 ? 0 : wins / total,
  };
}

export interface StandingsOptions {
  season: number;
  competition?: string;
}

export function standings(store: DataStore, options: StandingsOptions): TeamRecord[] {
  let matches = store.matches.filter((m) => m.season === options.season);
  if (options.competition) {
    const c = options.competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(c));
  } else {
    matches = matches.filter(
      (m) =>
        m.competition === 'Brasileirão Serie A' ||
        m.competition === 'Brasileirão (Historical 2003-2019)',
    );
  }

  const table = new Map<string, TeamRecord>();
  const teamLabel = new Map<string, string>();

  const apply = (rawTeam: string, gf: number, ga: number) => {
    const key = teamKey(rawTeam);
    if (!key) return;
    if (!teamLabel.has(key)) teamLabel.set(key, normalizeTeamName(rawTeam));
    const record = table.get(key) ?? {
      team: teamLabel.get(key)!,
      matches: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goalsFor: 0,
      goalsAgainst: 0,
      goalDifference: 0,
      points: 0,
    };
    record.matches++;
    record.goalsFor += gf;
    record.goalsAgainst += ga;
    if (gf > ga) {
      record.wins++;
      record.points += 3;
    } else if (gf < ga) {
      record.losses++;
    } else {
      record.draws++;
      record.points += 1;
    }
    record.goalDifference = record.goalsFor - record.goalsAgainst;
    table.set(key, record);
  };

  for (const m of matches) {
    apply(m.homeTeam, m.homeGoals, m.awayGoals);
    apply(m.awayTeam, m.awayGoals, m.homeGoals);
  }

  return Array.from(table.values()).sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.wins !== a.wins) return b.wins - a.wins;
    if (b.goalDifference !== a.goalDifference) return b.goalDifference - a.goalDifference;
    if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
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
}

function fuzzy(haystack: string | undefined, needle: string): boolean {
  if (!haystack) return false;
  return stripAccents(haystack).toLowerCase().includes(stripAccents(needle).toLowerCase());
}

export function findPlayers(store: DataStore, filter: PlayerFilter): Player[] {
  let results = store.players;

  if (filter.name) {
    results = results.filter((p) => fuzzy(p.name, filter.name!));
  }
  if (filter.nationality) {
    results = results.filter((p) => fuzzy(p.nationality, filter.nationality!));
  }
  if (filter.club) {
    results = results.filter((p) => fuzzy(p.club, filter.club!));
  }
  if (filter.position) {
    results = results.filter(
      (p) => (p.position ?? '').toUpperCase() === filter.position!.toUpperCase(),
    );
  }
  if (filter.minOverall !== undefined) {
    results = results.filter((p) => (p.overall ?? 0) >= filter.minOverall!);
  }
  if (filter.maxOverall !== undefined) {
    results = results.filter((p) => (p.overall ?? 0) <= filter.maxOverall!);
  }

  results = results
    .slice()
    .sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0) || a.name.localeCompare(b.name));

  if (filter.limit && filter.limit > 0) {
    results = results.slice(0, filter.limit);
  }
  return results;
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

export function aggregateStats(store: DataStore, filter: MatchFilter = {}): AggregateStats {
  const matches = findMatches(store, { ...filter, limit: undefined });
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;
  let totalGoals = 0;
  for (const m of matches) {
    totalGoals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) homeWins++;
    else if (m.homeGoals < m.awayGoals) awayWins++;
    else draws++;
  }
  const total = matches.length;
  return {
    totalMatches: total,
    totalGoals,
    averageGoalsPerMatch: total === 0 ? 0 : totalGoals / total,
    homeWins,
    awayWins,
    draws,
    homeWinRate: total === 0 ? 0 : homeWins / total,
    awayWinRate: total === 0 ? 0 : awayWins / total,
    drawRate: total === 0 ? 0 : draws / total,
  };
}

export function biggestWins(store: DataStore, filter: MatchFilter = {}, limit = 10): Match[] {
  const matches = findMatches(store, { ...filter, limit: undefined });
  return matches
    .slice()
    .sort((a, b) => {
      const diffA = Math.abs(a.homeGoals - a.awayGoals);
      const diffB = Math.abs(b.homeGoals - b.awayGoals);
      if (diffB !== diffA) return diffB - diffA;
      const totalA = a.homeGoals + a.awayGoals;
      const totalB = b.homeGoals + b.awayGoals;
      return totalB - totalA;
    })
    .slice(0, limit);
}

export interface TopScoringTeam {
  team: string;
  goals: number;
  matches: number;
  goalsPerMatch: number;
}

export function topScoringTeams(
  store: DataStore,
  filter: MatchFilter = {},
  limit = 10,
): TopScoringTeam[] {
  const matches = findMatches(store, { ...filter, limit: undefined });
  const totals = new Map<string, { team: string; goals: number; matches: number }>();
  const bump = (rawTeam: string, goals: number) => {
    const key = teamKey(rawTeam);
    if (!key) return;
    const cur = totals.get(key) ?? { team: normalizeTeamName(rawTeam), goals: 0, matches: 0 };
    cur.goals += goals;
    cur.matches++;
    totals.set(key, cur);
  };
  for (const m of matches) {
    bump(m.homeTeam, m.homeGoals);
    bump(m.awayTeam, m.awayGoals);
  }
  return Array.from(totals.values())
    .map((t) => ({
      team: t.team,
      goals: t.goals,
      matches: t.matches,
      goalsPerMatch: t.matches === 0 ? 0 : t.goals / t.matches,
    }))
    .sort((a, b) => b.goals - a.goals)
    .slice(0, limit);
}

export function listCompetitions(store: DataStore): string[] {
  return Array.from(new Set(store.matches.map((m) => m.competition))).sort();
}

export function listSeasons(store: DataStore, competition?: string): number[] {
  let matches = store.matches;
  if (competition) {
    const c = competition.toLowerCase();
    matches = matches.filter((m) => m.competition.toLowerCase().includes(c));
  }
  return Array.from(new Set(matches.map((m) => m.season).filter((s) => s > 0))).sort(
    (a, b) => a - b,
  );
}
