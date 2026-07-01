import type { AllData } from './dataLoader.js';
import { findMatches, getHeadToHead, getBiggestWins, getAverageGoals, getMatchTeams, getMatchDate, getMatchSeason, getMatchGoals, type MatchFilter } from './matchQueries.js';
import { getTeamRecord, getStandings } from './teamQueries.js';
import { searchPlayers, getTopRatedPlayers } from './playerQueries.js';

function formatDate(datetime: string): string {
  if (!datetime) return 'Unknown';
  if (datetime.includes('/')) {
    const [d, m, y] = datetime.split('/');
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
  }
  return datetime.split(' ')[0];
}

export function handleFindMatches(
  data: AllData,
  params: { team?: string; opponent?: string; competition?: string; season?: number; limit?: number }
) {
  const filter: MatchFilter = {
    team: params.team,
    opponent: params.opponent,
    competition: params.competition,
    season: params.season,
  };

  const allMatches = findMatches(data, filter);
  const limit = params.limit ?? 20;
  const sliced = allMatches.slice(0, limit);

  const matches = sliced.map(match => {
    const { home, away } = getMatchTeams(match);
    const { home: homeGoals, away: awayGoals } = getMatchGoals(match);
    const date = formatDate(getMatchDate(match));
    const season = getMatchSeason(match);
    return {
      date,
      season,
      homeTeam: home,
      awayTeam: away,
      score: `${homeGoals}-${awayGoals}`,
      competition: match.competition,
      round: 'round' in match ? String((match as { round: number | string }).round) : undefined,
      stage: 'stage' in match ? String((match as { stage: string }).stage) : undefined,
    };
  });

  return { matches, total: allMatches.length, showing: sliced.length };
}

export function handleHeadToHead(
  data: AllData,
  params: { teamA: string; teamB: string; competition?: string; season?: number }
) {
  const result = getHeadToHead(data, params.teamA, params.teamB);
  const recentMatches = findMatches(data, { team: params.teamA, opponent: params.teamB })
    .slice(0, 5)
    .map(match => {
      const { home, away } = getMatchTeams(match);
      const { home: hg, away: ag } = getMatchGoals(match);
      return {
        date: formatDate(getMatchDate(match)),
        homeTeam: home,
        awayTeam: away,
        score: `${hg}-${ag}`,
        competition: match.competition,
      };
    });

  return {
    teamA: result.teamA,
    teamB: result.teamB,
    total: result.total,
    teamAWins: result.teamAWins,
    teamBWins: result.teamBWins,
    draws: result.draws,
    recentMatches,
  };
}

export function handleTeamRecord(
  data: AllData,
  params: { team: string; season?: number; competition?: string; homeOnly?: boolean; awayOnly?: boolean }
) {
  const record = getTeamRecord(data, params.team, {
    season: params.season,
    competition: params.competition,
    homeOnly: params.homeOnly,
    awayOnly: params.awayOnly,
  });

  const winRate = record.played > 0 ? ((record.wins / record.played) * 100).toFixed(1) : '0.0';

  return {
    ...record,
    winRate: `${winRate}%`,
    goalDiff: record.goalsFor - record.goalsAgainst,
  };
}

export function handleStandings(
  data: AllData,
  params: { season: number; competition: string }
) {
  const standings = getStandings(data, { season: params.season, competition: params.competition });

  return {
    season: params.season,
    competition: params.competition,
    standings: standings.map(s => ({
      rank: s.rank,
      team: s.team,
      points: s.points,
      played: s.played,
      wins: s.wins,
      draws: s.draws,
      losses: s.losses,
      goalsFor: s.goalsFor,
      goalsAgainst: s.goalsAgainst,
      goalDiff: s.goalDiff,
    })),
  };
}

export function handleSearchPlayers(
  data: AllData,
  params: { name?: string; nationality?: string; club?: string; position?: string; minOverall?: number; limit?: number }
) {
  const players = searchPlayers(data, {
    name: params.name,
    nationality: params.nationality,
    club: params.club,
    position: params.position,
    minOverall: params.minOverall,
  });

  const limit = params.limit ?? 20;
  const sliced = players.slice(0, limit);

  return {
    players: sliced.map(p => ({
      name: p.name,
      nationality: p.nationality,
      overall: p.overall,
      potential: p.potential,
      club: p.club,
      position: p.position,
      age: p.age,
    })),
    total: players.length,
    showing: sliced.length,
  };
}

export function handleTopPlayers(
  data: AllData,
  params: { nationality?: string; club?: string; position?: string; limit?: number }
) {
  const limit = params.limit ?? 10;
  const players = getTopRatedPlayers(data, {
    nationality: params.nationality,
    club: params.club,
    position: params.position,
  }, limit);

  return {
    players: players.map((p, i) => ({
      rank: i + 1,
      name: p.name,
      nationality: p.nationality,
      overall: p.overall,
      club: p.club,
      position: p.position,
    })),
  };
}

export function handleBiggestWins(
  data: AllData,
  params: { competition?: string; season?: number; team?: string; limit?: number }
) {
  const filter: MatchFilter = {
    competition: params.competition,
    season: params.season,
    team: params.team,
  };

  const limit = params.limit ?? 10;
  const wins = getBiggestWins(data, filter, limit);

  return {
    matches: wins.map(w => ({
      date: formatDate(getMatchDate(w.match)),
      homeTeam: w.home,
      awayTeam: w.away,
      score: `${w.homeGoals}-${w.awayGoals}`,
      goalDiff: w.goalDiff,
      competition: w.match.competition,
    })),
  };
}

export function handleAverageGoals(
  data: AllData,
  params: { competition?: string; season?: number }
) {
  const filter: MatchFilter = {
    competition: params.competition,
    season: params.season,
  };

  const matches = findMatches(data, filter);
  const avg = getAverageGoals(data, filter);

  return {
    average: Math.round(avg * 100) / 100,
    matchCount: matches.length,
    competition: params.competition ?? 'All',
    season: params.season ?? 'All',
  };
}
