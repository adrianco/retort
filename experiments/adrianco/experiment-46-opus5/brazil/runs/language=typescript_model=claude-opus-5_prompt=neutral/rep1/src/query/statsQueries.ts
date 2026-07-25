/**
 * Corpus-level statistics: scoring rates, home advantage, extremes and
 * season-over-season comparisons.
 *
 * Every figure here is computed over the merged fixture list, so a season that
 * three source files describe is counted once. Matches with no recorded score
 * are excluded from rates and reported separately rather than treated as 0-0.
 */

import { byDateAscending } from '../util/collections.js';
import { hasScore, outcomeOf, type Match } from '../domain/types.js';
import type { SoccerGraph } from '../graph/graph.js';
import { selectMatches, type MatchFilter } from './filters.js';

export interface AggregateStats {
  matches: number;
  matchesWithScore: number;
  goals: number;
  goalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
  homeGoals: number;
  awayGoals: number;
  /** Share of matches in which both teams scored. */
  bothTeamsScoredRate: number;
  cleanSheets: number;
  biggestMargin: number;
  highestScoring: number;
  firstDate?: string;
  lastDate?: string;
}

export function aggregateStats(graph: SoccerGraph, filter: MatchFilter): AggregateStats {
  const matches = selectMatches(graph, filter);
  return summarise(matches);
}

export function summarise(matches: readonly Match[]): AggregateStats {
  const stats: AggregateStats = {
    matches: matches.length,
    matchesWithScore: 0,
    goals: 0,
    goalsPerMatch: 0,
    homeWins: 0,
    awayWins: 0,
    draws: 0,
    homeWinRate: 0,
    awayWinRate: 0,
    drawRate: 0,
    homeGoals: 0,
    awayGoals: 0,
    bothTeamsScoredRate: 0,
    cleanSheets: 0,
    biggestMargin: 0,
    highestScoring: 0,
  };

  let bothScored = 0;
  for (const match of matches) {
    if (stats.firstDate === undefined || match.date < stats.firstDate) stats.firstDate = match.date;
    if (stats.lastDate === undefined || match.date > stats.lastDate) stats.lastDate = match.date;
    if (!hasScore(match)) continue;

    stats.matchesWithScore++;
    stats.homeGoals += match.homeGoals;
    stats.awayGoals += match.awayGoals;
    stats.goals += match.homeGoals + match.awayGoals;

    const outcome = outcomeOf(match);
    if (outcome === 'home') stats.homeWins++;
    else if (outcome === 'away') stats.awayWins++;
    else stats.draws++;

    if (match.homeGoals > 0 && match.awayGoals > 0) bothScored++;
    if (match.homeGoals === 0 || match.awayGoals === 0) stats.cleanSheets++;
    stats.biggestMargin = Math.max(stats.biggestMargin, Math.abs(match.homeGoals - match.awayGoals));
    stats.highestScoring = Math.max(stats.highestScoring, match.homeGoals + match.awayGoals);
  }

  const played = stats.matchesWithScore;
  if (played > 0) {
    stats.goalsPerMatch = stats.goals / played;
    stats.homeWinRate = stats.homeWins / played;
    stats.awayWinRate = stats.awayWins / played;
    stats.drawRate = stats.draws / played;
    stats.bothTeamsScoredRate = bothScored / played;
  }
  return stats;
}

export type ExtremeKind = 'biggest-margin' | 'most-goals';

/** Winning margin of a scored match. */
export function marginOf(match: Match): number {
  return Math.abs((match.homeGoals ?? 0) - (match.awayGoals ?? 0));
}

/** Total goals in a scored match. */
export function totalGoalsOf(match: Match): number {
  return (match.homeGoals ?? 0) + (match.awayGoals ?? 0);
}

/**
 * Most extreme matches in a selection.
 *
 * The two rankings share a comparator so they can never drift apart: whichever
 * measure is primary, the other breaks the tie, and the most recent match wins
 * a remaining tie.
 */
export function extremeMatches(
  graph: SoccerGraph,
  filter: MatchFilter,
  kind: ExtremeKind,
  limit: number,
): Match[] {
  const primary = kind === 'most-goals' ? totalGoalsOf : marginOf;
  const secondary = kind === 'most-goals' ? marginOf : totalGoalsOf;

  return selectMatches(graph, filter)
    .filter(hasScore)
    .sort(
      (a, b) =>
        primary(b) - primary(a) ||
        secondary(b) - secondary(a) ||
        -byDateAscending(a, b),
    )
    .slice(0, limit);
}

export interface SeasonComparison {
  season: number;
  stats: AggregateStats;
}

export function compareSeasons(
  graph: SoccerGraph,
  filter: Omit<MatchFilter, 'season'>,
  seasons: number[],
): SeasonComparison[] {
  return seasons.map((season) => ({
    season,
    stats: aggregateStats(graph, { ...filter, season }),
  }));
}
