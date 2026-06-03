import type { Match, Player, Competition, TeamRecord, HeadToHead } from './types.js';
import { normalizeTeamName } from './normalize.js';

export interface MatchFilter {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  opponent?: string;
  competition?: Competition | 'all';
  season?: number;
  fromDate?: string;
  toDate?: string;
  stage?: string;
  round?: string | number;
  limit?: number;
}

function matchTeam(matchTeam: string, target: string): boolean {
  if (!target) return false;
  const a = normalizeTeamName(target);
  const b = matchTeam;
  if (!a || !b) return false;
  if (a === b) return true;
  return a.length >= 3 && (b.includes(a) || a.includes(b));
}

export function filterMatches(matches: Match[], filter: MatchFilter): Match[] {
  const competitionFilter =
    filter.competition && filter.competition !== 'all' ? filter.competition : undefined;

  const results = matches.filter(m => {
    if (competitionFilter && m.competition !== competitionFilter) return false;
    if (filter.season && m.season !== filter.season) return false;
    if (filter.fromDate && m.date < filter.fromDate) return false;
    if (filter.toDate && m.date > filter.toDate) return false;
    if (filter.stage && (m.stage || '').toLowerCase() !== filter.stage.toLowerCase()) return false;
    if (filter.round !== undefined && String(m.round ?? '') !== String(filter.round)) return false;
    if (filter.homeTeam && !matchTeam(m.homeTeam, filter.homeTeam)) return false;
    if (filter.awayTeam && !matchTeam(m.awayTeam, filter.awayTeam)) return false;

    if (filter.team) {
      const hits = matchTeam(m.homeTeam, filter.team) || matchTeam(m.awayTeam, filter.team);
      if (!hits) return false;
    }
    if (filter.opponent) {
      // Used with `team` — find matches where team played against opponent
      const teamRef = filter.team;
      if (teamRef) {
        const teamHome = matchTeam(m.homeTeam, teamRef);
        const oppAway = matchTeam(m.awayTeam, filter.opponent);
        const teamAway = matchTeam(m.awayTeam, teamRef);
        const oppHome = matchTeam(m.homeTeam, filter.opponent);
        if (!((teamHome && oppAway) || (teamAway && oppHome))) return false;
      } else {
        if (!matchTeam(m.homeTeam, filter.opponent) && !matchTeam(m.awayTeam, filter.opponent)) {
          return false;
        }
      }
    }
    return true;
  });

  results.sort((a, b) => b.date.localeCompare(a.date));

  if (filter.limit && filter.limit > 0) return results.slice(0, filter.limit);
  return results;
}

export function teamRecord(
  matches: Match[],
  team: string,
  opts: { season?: number; competition?: Competition | 'all'; venue?: 'home' | 'away' | 'all' } = {},
): TeamRecord {
  const venue = opts.venue ?? 'all';
  const relevant = filterMatches(matches, {
    team,
    season: opts.season,
    competition: opts.competition,
  });
  let wins = 0, draws = 0, losses = 0, gf = 0, ga = 0, count = 0;
  for (const m of relevant) {
    const home = matchTeam(m.homeTeam, team);
    if (venue === 'home' && !home) continue;
    if (venue === 'away' && home) continue;
    count++;
    const ourGoals = home ? m.homeGoals : m.awayGoals;
    const theirGoals = home ? m.awayGoals : m.homeGoals;
    gf += ourGoals;
    ga += theirGoals;
    if (ourGoals > theirGoals) wins++;
    else if (ourGoals < theirGoals) losses++;
    else draws++;
  }
  return {
    team: normalizeTeamName(team) || team,
    matches: count,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    goalDifference: gf - ga,
    points: wins * 3 + draws,
  };
}

export function headToHead(matches: Match[], teamA: string, teamB: string, opts: { competition?: Competition | 'all'; season?: number } = {}): HeadToHead {
  const history = filterMatches(matches, {
    team: teamA,
    opponent: teamB,
    competition: opts.competition,
    season: opts.season,
  });

  let aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;
  for (const m of history) {
    const aHome = matchTeam(m.homeTeam, teamA);
    const ourGoals = aHome ? m.homeGoals : m.awayGoals;
    const theirGoals = aHome ? m.awayGoals : m.homeGoals;
    aGoals += ourGoals;
    bGoals += theirGoals;
    if (ourGoals > theirGoals) aWins++;
    else if (ourGoals < theirGoals) bWins++;
    else draws++;
  }
  return {
    teamA: normalizeTeamName(teamA) || teamA,
    teamB: normalizeTeamName(teamB) || teamB,
    matches: history.length,
    teamAWins: aWins,
    teamBWins: bWins,
    draws,
    teamAGoals: aGoals,
    teamBGoals: bGoals,
    history,
  };
}

export interface StandingRow extends TeamRecord {
  rank: number;
}

export function competitionStandings(
  matches: Match[],
  competition: Competition,
  season: number,
): StandingRow[] {
  const seasonMatches = matches.filter(m => m.competition === competition && m.season === season);
  const records = new Map<string, TeamRecord>();

  for (const m of seasonMatches) {
    for (const team of [m.homeTeam, m.awayTeam]) {
      if (!team) continue;
      if (!records.has(team)) {
        records.set(team, {
          team,
          matches: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          goalDifference: 0,
          points: 0,
        });
      }
    }
    const home = records.get(m.homeTeam);
    const away = records.get(m.awayTeam);
    if (!home || !away) continue;
    home.matches++;
    away.matches++;
    home.goalsFor += m.homeGoals;
    home.goalsAgainst += m.awayGoals;
    away.goalsFor += m.awayGoals;
    away.goalsAgainst += m.homeGoals;
    if (m.homeGoals > m.awayGoals) {
      home.wins++;
      away.losses++;
      home.points += 3;
    } else if (m.homeGoals < m.awayGoals) {
      away.wins++;
      home.losses++;
      away.points += 3;
    } else {
      home.draws++;
      away.draws++;
      home.points++;
      away.points++;
    }
  }

  const list = Array.from(records.values()).map(r => ({
    ...r,
    goalDifference: r.goalsFor - r.goalsAgainst,
  }));
  list.sort((a, b) =>
    b.points - a.points ||
    b.goalDifference - a.goalDifference ||
    b.goalsFor - a.goalsFor ||
    a.team.localeCompare(b.team),
  );
  return list.map((r, i) => ({ ...r, rank: i + 1 }));
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxOverall?: number;
  sortBy?: 'overall' | 'potential' | 'age' | 'name';
  order?: 'asc' | 'desc';
  limit?: number;
}

export function filterPlayers(players: Player[], filter: PlayerFilter): Player[] {
  const target = filter.name ? filter.name.toLowerCase() : undefined;
  const targetClub = filter.club ? normalizeTeamName(filter.club) : undefined;
  const nat = filter.nationality ? filter.nationality.toLowerCase() : undefined;
  const pos = filter.position ? filter.position.toUpperCase() : undefined;

  const results = players.filter(p => {
    if (target && !(p.name || '').toLowerCase().includes(target)) return false;
    if (nat && (p.nationality || '').toLowerCase() !== nat) return false;
    if (targetClub) {
      const pc = p.clubNormalized || normalizeTeamName(p.club || '');
      if (!pc) return false;
      if (pc !== targetClub && !pc.includes(targetClub) && !targetClub.includes(pc)) return false;
    }
    if (pos && (p.position || '').toUpperCase() !== pos) return false;
    if (filter.minOverall !== undefined && (p.overall ?? -1) < filter.minOverall) return false;
    if (filter.maxOverall !== undefined && (p.overall ?? 999) > filter.maxOverall) return false;
    return true;
  });

  const sortBy = filter.sortBy ?? 'overall';
  const order = filter.order ?? 'desc';
  results.sort((a, b) => {
    let av: number | string;
    let bv: number | string;
    switch (sortBy) {
      case 'overall': av = a.overall ?? 0; bv = b.overall ?? 0; break;
      case 'potential': av = a.potential ?? 0; bv = b.potential ?? 0; break;
      case 'age': av = a.age ?? 0; bv = b.age ?? 0; break;
      default: av = a.name; bv = b.name; break;
    }
    if (av < bv) return order === 'asc' ? -1 : 1;
    if (av > bv) return order === 'asc' ? 1 : -1;
    return 0;
  });

  if (filter.limit && filter.limit > 0) return results.slice(0, filter.limit);
  return results;
}

export interface GoalsStat {
  team: string;
  goals: number;
  matches: number;
}

export function topScoringTeams(
  matches: Match[],
  opts: { competition?: Competition | 'all'; season?: number; venue?: 'home' | 'away' | 'all'; limit?: number } = {},
): GoalsStat[] {
  const venue = opts.venue ?? 'all';
  const subset = matches.filter(m => {
    if (opts.competition && opts.competition !== 'all' && m.competition !== opts.competition) return false;
    if (opts.season && m.season !== opts.season) return false;
    return true;
  });
  const tally = new Map<string, GoalsStat>();
  for (const m of subset) {
    if (venue !== 'away') {
      const row = tally.get(m.homeTeam) ?? { team: m.homeTeam, goals: 0, matches: 0 };
      row.goals += m.homeGoals;
      row.matches += 1;
      tally.set(m.homeTeam, row);
    }
    if (venue !== 'home') {
      const row = tally.get(m.awayTeam) ?? { team: m.awayTeam, goals: 0, matches: 0 };
      row.goals += m.awayGoals;
      row.matches += 1;
      tally.set(m.awayTeam, row);
    }
  }
  const list = Array.from(tally.values()).sort((a, b) => b.goals - a.goals);
  return opts.limit ? list.slice(0, opts.limit) : list;
}

export function biggestWins(
  matches: Match[],
  opts: { competition?: Competition | 'all'; season?: number; limit?: number } = {},
): Match[] {
  const subset = matches.filter(m => {
    if (opts.competition && opts.competition !== 'all' && m.competition !== opts.competition) return false;
    if (opts.season && m.season !== opts.season) return false;
    return true;
  });
  const sorted = [...subset].sort((a, b) => {
    const diffA = Math.abs(a.homeGoals - a.awayGoals);
    const diffB = Math.abs(b.homeGoals - b.awayGoals);
    if (diffB !== diffA) return diffB - diffA;
    return b.homeGoals + b.awayGoals - (a.homeGoals + a.awayGoals);
  });
  return sorted.slice(0, opts.limit ?? 10);
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
  matches: Match[],
  opts: { competition?: Competition | 'all'; season?: number } = {},
): AggregateStats {
  const subset = matches.filter(m => {
    if (opts.competition && opts.competition !== 'all' && m.competition !== opts.competition) return false;
    if (opts.season && m.season !== opts.season) return false;
    return true;
  });
  let goals = 0, hw = 0, aw = 0, dr = 0;
  for (const m of subset) {
    goals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) hw++;
    else if (m.homeGoals < m.awayGoals) aw++;
    else dr++;
  }
  const n = subset.length || 1;
  return {
    totalMatches: subset.length,
    totalGoals: goals,
    averageGoalsPerMatch: subset.length ? +(goals / n).toFixed(3) : 0,
    homeWins: hw,
    awayWins: aw,
    draws: dr,
    homeWinRate: subset.length ? +(hw / n).toFixed(4) : 0,
    awayWinRate: subset.length ? +(aw / n).toFixed(4) : 0,
    drawRate: subset.length ? +(dr / n).toFixed(4) : 0,
  };
}

export interface PlayerClubSummary {
  club: string;
  count: number;
  averageOverall: number;
}

export function brazilianPlayersByClub(players: Player[]): PlayerClubSummary[] {
  const brazilian = players.filter(p => (p.nationality || '').toLowerCase() === 'brazil');
  const groups = new Map<string, Player[]>();
  for (const p of brazilian) {
    const club = p.club || 'Unknown';
    if (!groups.has(club)) groups.set(club, []);
    groups.get(club)!.push(p);
  }
  return Array.from(groups.entries())
    .map(([club, group]) => ({
      club,
      count: group.length,
      averageOverall: +(group.reduce((s, p) => s + (p.overall ?? 0), 0) / group.length).toFixed(2),
    }))
    .sort((a, b) => b.count - a.count);
}

export function competitionsForTeam(matches: Match[], team: string): Competition[] {
  const set = new Set<Competition>();
  for (const m of matches) {
    if (matchTeam(m.homeTeam, team) || matchTeam(m.awayTeam, team)) {
      set.add(m.competition);
    }
  }
  return Array.from(set);
}
