/**
 * Argument fragments shared across tools.
 *
 * Keeping the competition / season / date filters in one place means every
 * tool accepts the same spellings ("brasileirao", "serie-a", "Copa do Brasil")
 * and the same date formats, which is what lets a model chain calls without
 * relearning the vocabulary each time.
 */

import { z } from 'zod';
import type { Match } from '../domain/types.js';
import type { SoccerGraph } from '../graph/graph.js';
import { optionalDate, resolveCompetition, type MatchFilter } from '../query/filters.js';

export const COMPETITION_HELP =
  'Competition id or name: serie-a (Brasileirão), serie-b, serie-c, copa-do-brasil, libertadores.';

// `.describe()` has to be re-applied after `.default()`, because Zod wraps the
// schema and the wrapper carries no description of its own.
export const competitionArg = z.string().max(60).describe(COMPETITION_HELP);

export const scopeShape = {
  competition: competitionArg.optional().describe(COMPETITION_HELP),
  season: z.number().int().optional().describe('Single season year, e.g. 2019.'),
  seasonFrom: z.number().int().optional().describe('Earliest season to include.'),
  seasonTo: z.number().int().optional().describe('Latest season to include.'),
  dateFrom: z.string().optional().describe('Earliest match date, YYYY-MM-DD or DD/MM/YYYY.'),
  dateTo: z.string().optional().describe('Latest match date, YYYY-MM-DD or DD/MM/YYYY.'),
};

export type ScopeInput = {
  competition?: string;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  dateFrom?: string;
  dateTo?: string;
};

/**
 * Turn the shared scope arguments into a `MatchFilter`.
 *
 * An inverted range is rejected rather than applied. Two independent
 * predicates would make `dateFrom > dateTo` an unsatisfiable filter that
 * quietly answers "no matches", and a caller who swapped the arguments would
 * read that as "the dataset has none" instead of retrying.
 */
export function scopeToFilter(input: ScopeInput): MatchFilter {
  const filter: MatchFilter = {};
  if (input.competition) filter.competition = resolveCompetition(input.competition);
  if (input.season !== undefined) filter.season = input.season;
  if (input.seasonFrom !== undefined) filter.seasonFrom = input.seasonFrom;
  if (input.seasonTo !== undefined) filter.seasonTo = input.seasonTo;

  if (
    filter.seasonFrom !== undefined &&
    filter.seasonTo !== undefined &&
    filter.seasonFrom > filter.seasonTo
  ) {
    throw new Error(
      `seasonFrom (${filter.seasonFrom}) is after seasonTo (${filter.seasonTo}); swap them.`,
    );
  }

  const from = optionalDate(input.dateFrom, 'dateFrom');
  const to = optionalDate(input.dateTo, 'dateTo');
  if (from && to && from > to) {
    throw new Error(`dateFrom (${from}) is after dateTo (${to}); swap them.`);
  }
  if (from) filter.dateFrom = from;
  if (to) filter.dateTo = to;
  return filter;
}

/** Compact JSON view of a match, used in every tool's structured payload. */
export function matchToJson(graph: SoccerGraph, match: Match): Record<string, unknown> {
  const json: Record<string, unknown> = {
    id: match.id,
    date: match.date,
    competition: match.competition,
    season: match.season,
    homeTeam: graph.teams.get(match.homeTeamId)?.name ?? match.homeTeamId,
    homeTeamId: match.homeTeamId,
    awayTeam: graph.teams.get(match.awayTeamId)?.name ?? match.awayTeamId,
    awayTeamId: match.awayTeamId,
    homeGoals: match.homeGoals,
    awayGoals: match.awayGoals,
    sources: match.sources,
  };
  if (match.time) json['time'] = match.time;
  if (match.round !== undefined) json['round'] = match.round;
  if (match.stage) json['stage'] = match.stage;
  if (match.venue) json['venue'] = match.venue;
  if (match.stats) json['stats'] = match.stats;
  return json;
}

/**
 * Free-text arguments are capped.
 *
 * Name resolution falls back to Levenshtein against every player (18k) or every
 * team alias (~1.1k), and Levenshtein is linear in the query length: an
 * uncapped argument costs ~1.9 s at 640 characters and ~3.7 s at 1280, which
 * blows the latency budget and blocks the server's single thread. No real club
 * or player name approaches this bound.
 */
export const NAME_MAX_LENGTH = 120;

export const nameArg = (description: string) =>
  z.string().max(NAME_MAX_LENGTH).describe(description);

/** Optional variant; `.describe()` is re-applied because `.optional()` wraps. */
export const optionalNameArg = (description: string) =>
  z.string().max(NAME_MAX_LENGTH).optional().describe(description);

/**
 * Row cap. Kept modest because every result is serialised twice -- once as
 * prose, once as `structuredContent` -- so a large page consumes a
 * disproportionate share of a model's context. Tools report the unfiltered
 * `total` separately, so counting never requires a big page.
 */
export const MAX_ROWS = 200;

export const limitArg = (fallback: number) =>
  z
    .number()
    .int()
    .min(1)
    .max(MAX_ROWS)
    .default(fallback)
    .describe('Maximum rows to return. The reported total is unaffected by this cap.');
