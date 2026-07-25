/**
 * Shared match selection.
 *
 * Every match-oriented tool funnels through `selectMatches` so that filter
 * semantics (especially "home / away / either") are defined once. Selection
 * starts from the narrowest available index -- a team's own match list, or a
 * competition-season bucket -- rather than scanning all 16k fixtures.
 */

import { parseDateBound } from '../domain/dates.js';
import type { Team, TeamRegistry } from '../domain/teams.js';
import { COMPETITIONS, type CompetitionId, type Match } from '../domain/types.js';
import type { SoccerGraph } from '../graph/graph.js';

export type Venue = 'home' | 'away' | 'any';

export interface MatchFilter {
  /** Canonical team id; matches must involve this team. */
  teamId?: string;
  /** Canonical id of a second team; matches must involve both. */
  opponentId?: string;
  /** Where `teamId` played. Ignored when `teamId` is absent. */
  venue?: Venue;
  competition?: CompetitionId;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  /** Inclusive `YYYY-MM-DD` bounds. */
  dateFrom?: string;
  dateTo?: string;
  /** Case-insensitive substring of the cup stage label. */
  stage?: string;
  round?: number;
  /** Keep only matches whose winning margin is at least this many goals. */
  minGoalDifference?: number;
  /** Keep only matches with at least this many goals in total. */
  minTotalGoals?: number;
}

/**
 * Match a stage label against a user's phrase on word boundaries.
 *
 * Plain substring matching would make "final" select the quarter-finals and
 * semi-finals too, which quietly ruins "find all Copa do Brasil finals".
 */
export function stageMatches(stage: string | undefined, query: string): boolean {
  if (!stage) return false;
  const escaped = query.trim().toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  if (escaped === '') return true;
  return new RegExp(`\\b${escaped}\\b`).test(stage.toLowerCase());
}

export function selectMatches(graph: SoccerGraph, filter: MatchFilter): Match[] {
  const base = pickIndex(graph, filter);
  const stage = filter.stage;

  return base.filter((match) => {
    if (filter.teamId) {
      const isHome = match.homeTeamId === filter.teamId;
      const isAway = match.awayTeamId === filter.teamId;
      if (!isHome && !isAway) return false;
      if (filter.venue === 'home' && !isHome) return false;
      if (filter.venue === 'away' && !isAway) return false;
    }
    if (filter.opponentId) {
      const involved = match.homeTeamId === filter.opponentId || match.awayTeamId === filter.opponentId;
      if (!involved) return false;
    }
    if (filter.competition && match.competition !== filter.competition) return false;
    if (filter.season !== undefined && match.season !== filter.season) return false;
    if (filter.seasonFrom !== undefined && match.season < filter.seasonFrom) return false;
    if (filter.seasonTo !== undefined && match.season > filter.seasonTo) return false;
    if (filter.dateFrom && match.date < filter.dateFrom) return false;
    if (filter.dateTo && match.date > filter.dateTo) return false;
    if (filter.round !== undefined && match.round !== filter.round) return false;
    if (stage && !stageMatches(match.stage, stage)) return false;

    if (filter.minGoalDifference !== undefined || filter.minTotalGoals !== undefined) {
      if (match.homeGoals === null || match.awayGoals === null) return false;
      const difference = Math.abs(match.homeGoals - match.awayGoals);
      const total = match.homeGoals + match.awayGoals;
      if (filter.minGoalDifference !== undefined && difference < filter.minGoalDifference) return false;
      if (filter.minTotalGoals !== undefined && total < filter.minTotalGoals) return false;
    }
    return true;
  });
}

/** Cheapest starting set for a filter, so the scan stays proportional to the answer. */
function pickIndex(graph: SoccerGraph, filter: MatchFilter): readonly Match[] {
  if (filter.teamId) return graph.matchesFor(filter.teamId);
  if (filter.opponentId) return graph.matchesFor(filter.opponentId);
  if (filter.competition && filter.season !== undefined) {
    return graph.matchesIn(filter.competition, filter.season);
  }
  return graph.matches;
}

/** Most recent first. Matches are stored oldest-first. */
export function newestFirst(matches: Match[]): Match[] {
  return [...matches].reverse();
}

export class TeamNotFoundError extends Error {
  constructor(
    readonly query: string,
    readonly candidates: Team[],
  ) {
    const suggestions = candidates.map((t) => `${t.name} (${t.id})`).join(', ');
    super(
      suggestions
        ? `No team matched "${query}". Closest names: ${suggestions}.`
        : `No team matched "${query}".`,
    );
    this.name = 'TeamNotFoundError';
  }
}

/** Resolve a user-supplied team name or throw with suggestions. */
export function requireTeam(teams: TeamRegistry, query: string): Team {
  const { team, candidates } = teams.resolveQuery(query);
  if (!team) throw new TeamNotFoundError(query, candidates);
  return team;
}

/**
 * Resolve two team names that must denote different clubs.
 *
 * Without this, "Atletico Mineiro" versus "Atletico-MG" both resolve to the
 * same club and the opponent predicate is satisfied by the team itself: every
 * home match counts as a win for one side and a loss for the other, producing
 * a head-to-head record of a club against itself.
 */
export function requireDistinctTeams(
  teams: TeamRegistry,
  first: string,
  second: string,
): [Team, Team] {
  const a = requireTeam(teams, first);
  const b = requireTeam(teams, second);
  if (a.id === b.id) {
    throw new Error(
      `"${first}" and "${second}" both resolve to ${a.name} (${a.id}); a team cannot play itself.`,
    );
  }
  return [a, b];
}

const COMPETITION_ALIASES: Record<string, CompetitionId> = {
  'serie a': 'serie-a',
  'série a': 'serie-a',
  brasileirao: 'serie-a',
  brasileirão: 'serie-a',
  'campeonato brasileiro': 'serie-a',
  'serie b': 'serie-b',
  'série b': 'serie-b',
  'serie c': 'serie-c',
  'série c': 'serie-c',
  'copa do brasil': 'copa-do-brasil',
  'brazilian cup': 'copa-do-brasil',
  cup: 'copa-do-brasil',
  libertadores: 'libertadores',
  'copa libertadores': 'libertadores',
};

/** Accept an id or a common human name for a competition. */
export function resolveCompetition(input: string): CompetitionId {
  const key = input.trim().toLowerCase();
  // `in` would walk the prototype chain and accept "constructor" or "toString".
  if (Object.hasOwn(COMPETITIONS, key)) return key as CompetitionId;
  const alias = COMPETITION_ALIASES[key] ?? COMPETITION_ALIASES[key.replace(/-/g, ' ')];
  if (alias) return alias;
  throw new Error(
    `Unknown competition "${input}". Use one of: ${Object.keys(COMPETITIONS).join(', ')}.`,
  );
}

/** Parse an optional user-supplied date bound. */
export function optionalDate(value: string | undefined, label: string): string | undefined {
  return value === undefined || value === '' ? undefined : parseDateBound(value, label);
}
