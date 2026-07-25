/**
 * Statistical tools: aggregate rates, record extremes and season comparisons.
 */

import { z } from 'zod';
import { COMPETITIONS } from '../domain/types.js';
import { decimal, formatAggregateStats, formatMatchList, percent } from '../format/format.js';
import { requireTeam } from '../query/filters.js';
import {
  aggregateStats,
  compareSeasons,
  extremeMatches,
  marginOf,
  totalGoalsOf,
} from '../query/statsQueries.js';
import { limitArg, matchToJson, nameArg, optionalNameArg, scopeShape, scopeToFilter } from './common.js';
import { defineTool } from './types.js';

export const matchStatistics = defineTool({
  name: 'match_statistics',
  title: 'Aggregate match statistics',
  description:
    'Goals per match, home/draw/away split, both-teams-scored rate and extremes over any slice of the ' +
    'data. Answers "what is the average goals per match in the Brasileirão" and "how strong is home ' +
    'advantage in Serie A".',
  schema: z.object({
    team: optionalNameArg('Restrict to matches involving this team.'),
    ...scopeShape,
  }),
  handler: (graph, input) => {
    const filter = scopeToFilter(input);
    if (input.team) filter.teamId = requireTeam(graph.teams, input.team).id;

    const stats = aggregateStats(graph, filter);
    const label = [
      input.team ?? undefined,
      input.competition ? COMPETITIONS[filter.competition!].name : 'All competitions',
      input.season !== undefined ? String(input.season) : undefined,
    ]
      .filter(Boolean)
      .join(' ');

    return {
      text: formatAggregateStats(stats, label),
      data: {
        scope: { ...filter },
        ...stats,
        goalsPerMatchFormatted: decimal(stats.goalsPerMatch),
        homeWinRateFormatted: percent(stats.homeWinRate),
      },
    };
  },
});

export const recordExtremes = defineTool({
  name: 'record_extremes',
  title: 'Biggest and highest-scoring matches',
  description:
    'The most lopsided or highest-scoring matches in a slice of the data. ' +
    'Answers "show me the biggest wins in the dataset".',
  schema: z.object({
    kind: z
      .enum(['biggest-margin', 'most-goals'])
      .default('biggest-margin')
      .describe('Rank by winning margin or by total goals.'),
    team: optionalNameArg('Restrict to matches involving this team.'),
    limit: limitArg(10),
    ...scopeShape,
  }),
  handler: (graph, input) => {
    const filter = scopeToFilter(input);
    if (input.team) filter.teamId = requireTeam(graph.teams, input.team).id;

    const matches = extremeMatches(graph, filter, input.kind, input.limit);

    const heading =
      input.kind === 'most-goals'
        ? 'Highest-scoring matches'
        : 'Biggest victories';

    return {
      text: [`${heading}:`, formatMatchList(graph, matches, input.limit)].join('\n'),
      data: {
        kind: input.kind,
        matches: matches.map((match) => ({
          ...matchToJson(graph, match),
          margin: marginOf(match),
          totalGoals: totalGoalsOf(match),
        })),
      },
    };
  },
});

export const seasonComparison = defineTool({
  name: 'compare_seasons',
  title: 'Compare seasons',
  description:
    'Put two or more seasons of the same competition side by side: matches, goals per match, and the ' +
    'home/draw/away split. Answers "compare the 2018 and 2019 seasons".',
  schema: z.object({
    competition: z.string().max(60).default('serie-a').describe('Competition id or name.'),
    seasons: z
      .array(z.number().int())
      .min(2)
      .max(30)
      .describe('Season years to compare, e.g. [2018, 2019].'),
    team: optionalNameArg('Restrict to matches involving this team.'),
  }),
  handler: (graph, input) => {
    const filter = scopeToFilter({ competition: input.competition });
    if (input.team) filter.teamId = requireTeam(graph.teams, input.team).id;

    const comparisons = compareSeasons(graph, filter, input.seasons);
    const name = COMPETITIONS[filter.competition!].name;

    const lines = comparisons.map(({ season, stats }) =>
      stats.matchesWithScore === 0
        ? `${season}: no matches in the data.`
        : `${season}: ${stats.matches} matches, ${stats.goals} goals (${decimal(stats.goalsPerMatch)}/match), ` +
          `home ${percent(stats.homeWinRate)} / draw ${percent(stats.drawRate)} / away ${percent(stats.awayWinRate)}`,
    );

    const withData = comparisons.filter((c) => c.stats.matchesWithScore > 0);
    const trend =
      withData.length >= 2
        ? (() => {
            const first = withData[0]!;
            const last = withData[withData.length - 1]!;
            const delta = last.stats.goalsPerMatch - first.stats.goalsPerMatch;
            const direction = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat';
            return `Goals per match moved ${direction} by ${decimal(Math.abs(delta))} between ${first.season} and ${last.season}.`;
          })()
        : undefined;

    return {
      text: [`${name}${input.team ? ` — ${input.team}` : ''}:`, ...lines, ...(trend ? ['', trend] : [])].join('\n'),
      data: {
        competition: filter.competition,
        seasons: comparisons.map(({ season, stats }) => ({ season, ...stats })),
      },
    };
  },
});
