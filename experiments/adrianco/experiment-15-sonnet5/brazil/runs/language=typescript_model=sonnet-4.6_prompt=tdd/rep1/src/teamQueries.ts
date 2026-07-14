import { teamsMatch, normalizeTeamName } from './teamNormalizer.js';
import { findMatches, getMatchTeams, getMatchSeason, getMatchGoals, type MatchFilter } from './matchQueries.js';
import type { AllData } from './dataLoader.js';

export interface TeamRecordOptions {
  season?: number;
  competition?: string;
  homeOnly?: boolean;
  awayOnly?: boolean;
}

export interface TeamRecord {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

export function getTeamRecord(data: AllData, team: string, options: TeamRecordOptions): TeamRecord {
  const filter: MatchFilter = {
    team,
    season: options.season,
    competition: options.competition,
  };

  const matches = findMatches(data, filter);
  let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;

  for (const match of matches) {
    const { home, away } = getMatchTeams(match);
    const { home: homeGoals, away: awayGoals } = getMatchGoals(match);
    const isHome = teamsMatch(home, team);
    const isAway = teamsMatch(away, team);

    if (options.homeOnly && !isHome) continue;
    if (options.awayOnly && !isAway) continue;

    const myGoals = isHome ? homeGoals : awayGoals;
    const theirGoals = isHome ? awayGoals : homeGoals;

    goalsFor += myGoals;
    goalsAgainst += theirGoals;

    if (myGoals > theirGoals) wins++;
    else if (myGoals === theirGoals) draws++;
    else losses++;
  }

  const played = wins + draws + losses;
  return { team, played, wins, draws, losses, goalsFor, goalsAgainst, points: wins * 3 + draws };
}

export interface StandingEntry extends TeamRecord {
  goalDiff: number;
  rank: number;
}

export interface StandingsOptions {
  season?: number;
  competition?: string;
}

export function getStandings(data: AllData, options: StandingsOptions): StandingEntry[] {
  const filter: MatchFilter = {
    season: options.season,
    competition: options.competition,
  };

  const matches = findMatches(data, filter);
  const teamSet = new Set<string>();

  for (const match of matches) {
    const { home, away } = getMatchTeams(match);
    if (home) teamSet.add(home);
    if (away) teamSet.add(away);
  }

  const entries = Array.from(teamSet).map((teamKey, i) => {
    // getTeamRecord uses teamKey (state-qualified) so Atletico-MG ≠ Atletico-PR
    const record = getTeamRecord(data, teamKey, options);
    // Display the normalized name (without state suffix) for readability
    const displayName = normalizeTeamName(teamKey);
    return { ...record, team: displayName, goalDiff: record.goalsFor - record.goalsAgainst, rank: i + 1 };
  });

  entries.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.wins !== a.wins) return b.wins - a.wins;
    return b.goalDiff - a.goalDiff;
  });

  entries.forEach((e, i) => { e.rank = i + 1; });
  return entries;
}

export interface TopScorerEntry {
  team: string;
  goals: number;
}

export function getTopScoringTeams(data: AllData, options: StandingsOptions, limit = 10): TopScorerEntry[] {
  const standings = getStandings(data, options);
  return standings
    .sort((a, b) => b.goalsFor - a.goalsFor)
    .slice(0, limit)
    .map(s => ({ team: s.team, goals: s.goalsFor }));
}
