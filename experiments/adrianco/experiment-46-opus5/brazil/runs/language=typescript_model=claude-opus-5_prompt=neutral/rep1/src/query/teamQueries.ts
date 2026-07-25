/**
 * Team-centric aggregations: records, head-to-head and profiles.
 *
 * All of them reduce a selected match list into the same `TeamRecord` shape, so
 * "Corinthians at home in 2022", "Palmeiras in the Libertadores" and "every
 * match Santos has ever played here" are the same computation with different
 * filters.
 */

import type { Team } from '../domain/teams.js';
import { hasScore, type CompetitionId, type Match } from '../domain/types.js';
import type { SoccerGraph } from '../graph/graph.js';
import { selectMatches, type MatchFilter, type Venue } from './filters.js';
import { squadOf } from './playerQueries.js';

export interface TeamRecord {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  /** Three points for a win, one for a draw. */
  points: number;
  /** Wins / played, as a fraction. `0` when nothing was played. */
  winRate: number;
  /** Matches in the selection with no recorded score, excluded from the rest. */
  withoutScore: number;
}

export function emptyRecord(): TeamRecord {
  return {
    played: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    goalDifference: 0,
    points: 0,
    winRate: 0,
    withoutScore: 0,
  };
}

/** Reduce matches into a win/draw/loss record from `teamId`'s point of view. */
export function buildRecord(matches: readonly Match[], teamId: string): TeamRecord {
  const record = emptyRecord();
  for (const match of matches) {
    if (!hasScore(match)) {
      record.withoutScore++;
      continue;
    }
    const isHome = match.homeTeamId === teamId;
    const goalsFor = isHome ? match.homeGoals : match.awayGoals;
    const goalsAgainst = isHome ? match.awayGoals : match.homeGoals;

    record.played++;
    record.goalsFor += goalsFor;
    record.goalsAgainst += goalsAgainst;
    if (goalsFor > goalsAgainst) record.wins++;
    else if (goalsFor === goalsAgainst) record.draws++;
    else record.losses++;
  }
  record.goalDifference = record.goalsFor - record.goalsAgainst;
  record.points = record.wins * 3 + record.draws;
  record.winRate = record.played === 0 ? 0 : record.wins / record.played;
  return record;
}

export interface TeamStatsResult {
  team: Team;
  filter: MatchFilter;
  record: TeamRecord;
  matches: Match[];
  /** Same record split by where the matches were played. */
  home: TeamRecord;
  away: TeamRecord;
  byCompetition: Array<{ competition: CompetitionId; record: TeamRecord }>;
  bySeason: Array<{ season: number; record: TeamRecord }>;
}

export function teamStats(
  graph: SoccerGraph,
  team: Team,
  filter: Omit<MatchFilter, 'teamId'> = {},
): TeamStatsResult {
  const full: MatchFilter = { ...filter, teamId: team.id };
  const matches = selectMatches(graph, full);

  const home = matches.filter((m) => m.homeTeamId === team.id);
  const away = matches.filter((m) => m.awayTeamId === team.id);

  const competitions = new Map<CompetitionId, Match[]>();
  const seasons = new Map<number, Match[]>();
  for (const match of matches) {
    pushInto(competitions, match.competition, match);
    pushInto(seasons, match.season, match);
  }

  return {
    team,
    filter: full,
    record: buildRecord(matches, team.id),
    matches,
    home: buildRecord(home, team.id),
    away: buildRecord(away, team.id),
    byCompetition: [...competitions.entries()]
      .map(([competition, list]) => ({ competition, record: buildRecord(list, team.id) }))
      .sort((a, b) => b.record.played - a.record.played),
    bySeason: [...seasons.entries()]
      .map(([season, list]) => ({ season, record: buildRecord(list, team.id) }))
      .sort((a, b) => a.season - b.season),
  };
}

export interface HeadToHeadResult {
  teamA: Team;
  teamB: Team;
  /** Named derby, when the pair has one. */
  rivalry?: string;
  matches: Match[];
  aWins: number;
  bWins: number;
  draws: number;
  aGoals: number;
  bGoals: number;
  withoutScore: number;
  /** Record of A when hosting B, and of A when visiting B. */
  aAtHome: TeamRecord;
  aAway: TeamRecord;
}

export function headToHead(
  graph: SoccerGraph,
  teamA: Team,
  teamB: Team,
  filter: Omit<MatchFilter, 'teamId' | 'opponentId'> = {},
): HeadToHeadResult {
  const matches = selectMatches(graph, { ...filter, teamId: teamA.id, opponentId: teamB.id });

  let aWins = 0;
  let bWins = 0;
  let draws = 0;
  let aGoals = 0;
  let bGoals = 0;
  let withoutScore = 0;

  for (const match of matches) {
    if (!hasScore(match)) {
      withoutScore++;
      continue;
    }
    const aIsHome = match.homeTeamId === teamA.id;
    const forA = aIsHome ? match.homeGoals : match.awayGoals;
    const forB = aIsHome ? match.awayGoals : match.homeGoals;
    aGoals += forA;
    bGoals += forB;
    if (forA > forB) aWins++;
    else if (forA < forB) bWins++;
    else draws++;
  }

  const result: HeadToHeadResult = {
    teamA,
    teamB,
    matches,
    aWins,
    bWins,
    draws,
    aGoals,
    bGoals,
    withoutScore,
    aAtHome: buildRecord(matches.filter((m) => m.homeTeamId === teamA.id), teamA.id),
    aAway: buildRecord(matches.filter((m) => m.awayTeamId === teamA.id), teamA.id),
  };

  const rivalry = graph.teams.rivalryFor(teamA.id, teamB.id);
  if (rivalry) result.rivalry = rivalry.name;
  return result;
}

export interface TeamProfile {
  team: Team;
  record: TeamRecord;
  firstMatch?: Match;
  lastMatch?: Match;
  competitions: Array<{ competition: CompetitionId; matches: number; seasons: number[] }>;
  topOpponents: Array<{ team: Team; meetings: number }>;
  venues: Array<{ venue: string; matches: number }>;
  squad: Array<{ name: string; overall: number | null; position: string }>;
  /** Every raw spelling of the club found in the source files. */
  knownAs: string[];
}

export function teamProfile(graph: SoccerGraph, team: Team): TeamProfile {
  const matches = graph.matchesFor(team.id);
  const squad = squadOf(graph, team.id).map((p) => ({
    name: p.name,
    overall: p.overall,
    position: p.position,
  }));

  const profile: TeamProfile = {
    team,
    record: buildRecord(matches, team.id),
    competitions: graph.competitionsOf(team.id),
    topOpponents: graph.opponentsOf(team.id).slice(0, 10),
    venues: graph.venuesOf(team.id).slice(0, 5),
    squad,
    knownAs: [...team.aliases].sort(),
  };
  if (matches.length > 0) {
    profile.firstMatch = matches[0]!;
    profile.lastMatch = matches[matches.length - 1]!;
  }
  return profile;
}

/** Rank every team in a selection by a record-derived metric. */
export function teamLeaderboard(
  graph: SoccerGraph,
  filter: MatchFilter,
  venue: Venue,
  minimumPlayed: number,
): Array<{ team: Team; record: TeamRecord }> {
  const matches = selectMatches(graph, filter);
  const byTeam = new Map<string, Match[]>();
  for (const match of matches) {
    if (venue !== 'away') pushInto(byTeam, match.homeTeamId, match);
    if (venue !== 'home') pushInto(byTeam, match.awayTeamId, match);
  }

  const rows: Array<{ team: Team; record: TeamRecord }> = [];
  for (const [teamId, list] of byTeam) {
    const team = graph.teams.get(teamId);
    if (!team) continue;
    const relevant =
      venue === 'home'
        ? list.filter((m) => m.homeTeamId === teamId)
        : venue === 'away'
          ? list.filter((m) => m.awayTeamId === teamId)
          : list;
    const record = buildRecord(relevant, teamId);
    if (record.played >= minimumPlayed) rows.push({ team, record });
  }
  return rows;
}


function pushInto<K, V>(map: Map<K, V[]>, key: K, value: V): void {
  const bucket = map.get(key);
  if (bucket) bucket.push(value);
  else map.set(key, [value]);
}
