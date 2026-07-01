import { teamsMatch } from './teamNormalizer.js';
import type { AllData, BrazileiraoMatch, CupMatch, LibertadoresMatch, BRFootballMatch, HistoricalMatch } from './dataLoader.js';

export type AnyMatch = (BrazileiraoMatch | CupMatch | LibertadoresMatch | BRFootballMatch | HistoricalMatch) & {
  competition: string;
};

export interface MatchFilter {
  team?: string;
  opponent?: string;
  season?: number;
  competition?: string;
  dateFrom?: string;
  dateTo?: string;
}

function getMatchTeams(match: AnyMatch): { home: string; away: string } {
  if (match.competition === 'Brasileirao' && 'home_team' in match) {
    const m = match as BrazileiraoMatch;
    // Use original names with state suffix to distinguish e.g. Atletico-MG vs Atletico-PR
    return { home: m.home_team, away: m.away_team };
  }
  if (match.competition === 'Copa do Brasil' && 'home_team' in match) {
    const m = match as CupMatch;
    return { home: m.home_team_normalized, away: m.away_team_normalized };
  }
  if (match.competition === 'Libertadores' && 'home_team' in match) {
    const m = match as LibertadoresMatch;
    return { home: m.home_team_normalized, away: m.away_team_normalized };
  }
  if ('home' in match) {
    const m = match as BRFootballMatch;
    return { home: m.home_normalized, away: m.away_normalized };
  }
  if ('equipe_mandante' in match) {
    const m = match as HistoricalMatch;
    return {
      home: m.equipe_mandante + (m.mandante_uf ? `-${m.mandante_uf}` : ''),
      away: m.equipe_visitante + (m.visitante_uf ? `-${m.visitante_uf}` : ''),
    };
  }
  return { home: '', away: '' };
}

function getMatchDate(match: AnyMatch): string {
  if ('datetime' in match && match.datetime) return (match as BrazileiraoMatch).datetime;
  if ('date' in match && (match as BRFootballMatch).date) return (match as BRFootballMatch).date;
  if ('data' in match && (match as HistoricalMatch).data) return (match as HistoricalMatch).data;
  return '';
}

function getMatchSeason(match: AnyMatch): number {
  if ('season' in match) return (match as BrazileiraoMatch).season;
  if ('ano' in match) return (match as HistoricalMatch).ano;
  return 0;
}

function getMatchGoals(match: AnyMatch): { home: number; away: number } {
  if ('home_goal' in match) return { home: (match as BrazileiraoMatch).home_goal, away: (match as BrazileiraoMatch).away_goal };
  if ('gols_mandante' in match) return { home: (match as HistoricalMatch).gols_mandante, away: (match as HistoricalMatch).gols_visitante };
  return { home: 0, away: 0 };
}

function getAllMatches(data: AllData): AnyMatch[] {
  return [
    ...(data.brasileirao as AnyMatch[]),
    ...(data.copaBrasil as AnyMatch[]),
    ...(data.libertadores as AnyMatch[]),
    ...(data.brFootball as AnyMatch[]),
    ...(data.historical as AnyMatch[]),
  ];
}

export function findMatches(data: AllData, filter: MatchFilter): AnyMatch[] {
  const all = getAllMatches(data);

  return all.filter(match => {
    const { home, away } = getMatchTeams(match);
    const season = getMatchSeason(match);

    if (filter.competition && match.competition !== filter.competition) return false;
    if (filter.season && season !== filter.season) return false;

    if (filter.team) {
      const teamInMatch = teamsMatch(home, filter.team) || teamsMatch(away, filter.team);
      if (!teamInMatch) return false;

      if (filter.opponent) {
        const opponentInMatch = teamsMatch(home, filter.opponent) || teamsMatch(away, filter.opponent);
        if (!opponentInMatch) return false;
        if (home === away) return false;
      }
    }

    return true;
  });
}

export interface HeadToHeadResult {
  total: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamA: string;
  teamB: string;
}

export function getHeadToHead(data: AllData, teamA: string, teamB: string): HeadToHeadResult {
  const matches = findMatches(data, { team: teamA, opponent: teamB });

  let teamAWins = 0;
  let teamBWins = 0;
  let draws = 0;

  for (const match of matches) {
    const { home, away } = getMatchTeams(match);
    const { home: homeGoals, away: awayGoals } = getMatchGoals(match);
    const homeIsA = teamsMatch(home, teamA);

    if (homeGoals === awayGoals) {
      draws++;
    } else if ((homeGoals > awayGoals && homeIsA) || (awayGoals > homeGoals && !homeIsA)) {
      teamAWins++;
    } else {
      teamBWins++;
    }
  }

  return { total: matches.length, teamAWins, teamBWins, draws, teamA, teamB };
}

export interface WinResult {
  match: AnyMatch;
  goalDiff: number;
  home: string;
  away: string;
  homeGoals: number;
  awayGoals: number;
}

export function getBiggestWins(data: AllData, filter: MatchFilter, limit = 10): WinResult[] {
  const matches = findMatches(data, filter);

  return matches
    .map(match => {
      const { home, away } = getMatchTeams(match);
      const { home: homeGoals, away: awayGoals } = getMatchGoals(match);
      return { match, goalDiff: Math.abs(homeGoals - awayGoals), home, away, homeGoals, awayGoals };
    })
    .sort((a, b) => b.goalDiff - a.goalDiff)
    .slice(0, limit);
}

export function getAverageGoals(data: AllData, filter: MatchFilter): number {
  const matches = findMatches(data, filter);
  if (matches.length === 0) return 0;

  const total = matches.reduce((sum, match) => {
    const { home, away } = getMatchGoals(match);
    return sum + home + away;
  }, 0);

  return total / matches.length;
}

export { getMatchTeams, getMatchDate, getMatchSeason, getMatchGoals, getAllMatches };
