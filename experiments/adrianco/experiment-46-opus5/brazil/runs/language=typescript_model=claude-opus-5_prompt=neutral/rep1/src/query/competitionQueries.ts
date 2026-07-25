/**
 * Competition views: league tables computed from results, and cup brackets.
 *
 * No standings are stored in any source file, so a table is derived by
 * replaying every match of a season. That makes the champion, the European /
 * Libertadores places and the relegation zone *inferences*, which is why the
 * result carries a `complete` flag and an explicit note when the season's match
 * count does not look like a finished campaign.
 */

import { byDateAscending, pushInto } from '../util/collections.js';
import type { Team } from '../domain/teams.js';
import { COMPETITIONS, hasScore, type CompetitionId, type Match } from '../domain/types.js';
import type { SoccerGraph } from '../graph/graph.js';
import { buildRecord, type TeamRecord } from './teamQueries.js';

export interface StandingRow {
  position: number;
  team: Team;
  record: TeamRecord;
}

export interface Standings {
  competition: CompetitionId;
  competitionName: string;
  season: number;
  rows: StandingRow[];
  /** Matches counted, and how many were expected for a full double round-robin. */
  matchesPlayed: number;
  expectedMatches: number;
  complete: boolean;
  /** Bottom placings, by the four-down rule the Brasileirão has used since 2006. */
  relegated: StandingRow[];
  champion?: StandingRow;
  notes: string[];
}

/** Since 2006 the bottom four of Série A and Série B go down. */
const RELEGATION_SLOTS = 4;

/**
 * A table smaller than this is a data artefact, not a division, so no
 * relegation zone is inferred for it -- otherwise a two-team "season" would
 * report both teams as relegated.
 */
const MIN_TEAMS_FOR_RELEGATION = 12;

/**
 * Rank by points, then wins, then goal difference, then goals scored.
 *
 * The CBF's official tiebreakers continue past this into head-to-head record
 * and disciplinary points, neither of which the data contains; ties that reach
 * that far are broken by name so the ordering is at least deterministic.
 */
function compareRows(a: StandingRow, b: StandingRow): number {
  return (
    b.record.points - a.record.points ||
    b.record.wins - a.record.wins ||
    b.record.goalDifference - a.record.goalDifference ||
    b.record.goalsFor - a.record.goalsFor ||
    a.team.name.localeCompare(b.team.name)
  );
}

export function standings(
  graph: SoccerGraph,
  competition: CompetitionId,
  season: number,
): Standings {
  const matches = graph.matchesIn(competition, season).filter(hasScore);
  const byTeam = new Map<string, Match[]>();
  for (const match of matches) {
    pushInto(byTeam, match.homeTeamId, match);
    pushInto(byTeam, match.awayTeamId, match);
  }

  const rows: StandingRow[] = [];
  for (const [teamId, list] of byTeam) {
    const team = graph.teams.get(teamId);
    if (!team) continue;
    rows.push({ position: 0, team, record: buildRecord(list, teamId) });
  }
  rows.sort(compareRows);
  rows.forEach((row, index) => {
    row.position = index + 1;
  });

  const teamCount = rows.length;
  const expectedMatches = teamCount * (teamCount - 1);
  const complete = teamCount > 1 && matches.length === expectedMatches;

  const notes: string[] = [];
  if (COMPETITIONS[competition].format !== 'league') {
    notes.push(
      `${COMPETITIONS[competition].name} is a knockout competition; this table just aggregates its results and is not an official standing.`,
    );
  }
  if (!complete && teamCount > 1) {
    notes.push(
      `The data holds ${matches.length} of the ${expectedMatches} matches a ${teamCount}-team double round-robin needs, so this table is partial.`,
    );
  }
  notes.push(
    'Standings are computed from match results in the provided datasets, not taken from an official table. Points are 3 for a win, 1 for a draw.',
  );

  const isLeague = COMPETITIONS[competition].format === 'league';
  const relegated =
    isLeague && complete && teamCount >= MIN_TEAMS_FOR_RELEGATION
      ? rows.slice(-RELEGATION_SLOTS)
      : [];

  const result: Standings = {
    competition,
    competitionName: COMPETITIONS[competition].name,
    season,
    rows,
    matchesPlayed: matches.length,
    expectedMatches,
    complete,
    relegated,
    notes,
  };
  if (isLeague && complete && rows[0]) result.champion = rows[0];
  return result;
}

export interface StageGroup {
  stage: string;
  matches: Match[];
}

export interface CupSummary {
  competition: CompetitionId;
  competitionName: string;
  season: number;
  stages: StageGroup[];
  /** Winner of the final, when the final is present and decided. */
  winner?: Team;
  notes: string[];
}

/** Rough progression order, so stages read from group phase to final. */
const STAGE_ORDER = [
  'group stage',
  'round 1',
  'round 2',
  'round 3',
  'round 4',
  'round 5',
  'round of 16',
  'quarterfinals',
  'semifinals',
  'final',
];

function stageRank(stage: string): number {
  const index = STAGE_ORDER.indexOf(stage.toLowerCase());
  return index === -1 ? STAGE_ORDER.length : index;
}

export function cupSummary(
  graph: SoccerGraph,
  competition: CompetitionId,
  season: number,
): CupSummary {
  const matches = graph.matchesIn(competition, season);
  const byStage = new Map<string, Match[]>();
  for (const match of matches) pushInto(byStage, match.stage ?? 'unknown stage', match);

  const stages: StageGroup[] = [...byStage.entries()]
    .map(([stage, list]) => ({
      stage,
      matches: [...list].sort(byDateAscending),
    }))
    .sort((a, b) => stageRank(a.stage) - stageRank(b.stage) || a.stage.localeCompare(b.stage));

  const notes: string[] = [];
  const summary: CupSummary = {
    competition,
    competitionName: COMPETITIONS[competition].name,
    season,
    stages,
    notes,
  };

  const finals = byStage.get('final') ?? [];
  const winner = decideTie(graph, finals);
  if (winner) {
    summary.winner = winner;
  } else if (finals.length > 0) {
    notes.push('The final is in the data but the tie is level on aggregate; no winner can be inferred without extra-time or penalty detail.');
  }
  if (finals.length === 0) notes.push('No match in this season is labelled as the final.');

  return summary;
}

/**
 * Winner of a one- or two-legged tie on aggregate.
 *
 * Away goals and penalty shoot-outs are not in the data, so a level aggregate
 * yields no winner rather than a guess.
 */
export function decideTie(graph: SoccerGraph, legs: readonly Match[]): Team | undefined {
  const scored = legs.filter(hasScore);
  if (scored.length === 0) return undefined;

  const aggregate = new Map<string, number>();
  for (const match of scored) {
    aggregate.set(match.homeTeamId, (aggregate.get(match.homeTeamId) ?? 0) + match.homeGoals);
    aggregate.set(match.awayTeamId, (aggregate.get(match.awayTeamId) ?? 0) + match.awayGoals);
  }

  // Aggregating only makes sense within a single tie. Given two unrelated
  // one-leg ties this would otherwise crown whoever won by most, so anything
  // that is not exactly two teams yields no winner.
  if (aggregate.size !== 2) return undefined;

  const ranked = [...aggregate.entries()].sort((a, b) => b[1] - a[1]);
  const [best, second] = ranked;
  if (!best || !second || best[1] === second[1]) return undefined;
  return graph.teams.get(best[0]);
}

