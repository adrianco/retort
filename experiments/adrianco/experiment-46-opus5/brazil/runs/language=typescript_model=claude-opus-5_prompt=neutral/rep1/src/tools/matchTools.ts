/**
 * Match-oriented tools: fixture search, head-to-head, and derby lookup.
 */

import { z } from 'zod';
import { RIVALRIES } from '../domain/teams.js';
import { formatHeadToHead, formatMatchLine, formatMatchList } from '../format/format.js';
import { newestFirst, requireDistinctTeams, requireTeam, selectMatches } from '../query/filters.js';
import { headToHead } from '../query/teamQueries.js';
import { limitArg, matchToJson, nameArg, optionalNameArg, scopeShape, scopeToFilter } from './common.js';
import { defineTool } from './types.js';

export const searchMatches = defineTool({
  name: 'search_matches',
  title: 'Search matches',
  description:
    'Find matches by team, opponent, competition, season, date range, round or stage. ' +
    'Use it for questions like "what matches did Palmeiras play in 2023" or "find all Copa do Brasil finals". ' +
    'Team names may be written with or without a state suffix and with or without accents.',
  schema: z.object({
    team: optionalNameArg('Team name, e.g. "Flamengo" or "Sao Paulo-SP".'),
    opponent: optionalNameArg('Restrict to matches against this second team.'),
    venue: z
      .enum(['home', 'away', 'any'])
      .default('any')
      .describe('Where `team` played. Ignored when no team is given.'),
    stage: optionalNameArg('Cup stage, matched on word boundaries: "final" excludes the semi-finals.'),
    round: z.number().int().optional().describe('League round number.'),
    minGoalDifference: z.number().int().min(0).optional().describe('Keep only wins by this margin or more.'),
    minTotalGoals: z.number().int().min(0).optional().describe('Keep only matches with at least this many goals.'),
    order: z.enum(['newest', 'oldest']).default('newest').describe('Sort direction by date.'),
    limit: limitArg(20),
    ...scopeShape,
  }),
  handler: (graph, input) => {
    const filter = scopeToFilter(input);
    if (input.team && input.opponent) {
      const [team, opponent] = requireDistinctTeams(graph.teams, input.team, input.opponent);
      filter.teamId = team.id;
      filter.opponentId = opponent.id;
    } else if (input.team) {
      filter.teamId = requireTeam(graph.teams, input.team).id;
    } else if (input.opponent) {
      filter.opponentId = requireTeam(graph.teams, input.opponent).id;
    }
    if (input.team) filter.venue = input.venue;
    if (input.stage) filter.stage = input.stage;
    if (input.round !== undefined) filter.round = input.round;
    if (input.minGoalDifference !== undefined) filter.minGoalDifference = input.minGoalDifference;
    if (input.minTotalGoals !== undefined) filter.minTotalGoals = input.minTotalGoals;

    const found = selectMatches(graph, filter);
    const ordered = input.order === 'newest' ? newestFirst(found) : found;
    const shown = ordered.slice(0, input.limit);

    const header = describeQuery(input);
    const text = [`${header} — ${found.length} match(es) found.`, formatMatchList(graph, ordered, input.limit)].join('\n');

    return {
      text,
      data: {
        total: found.length,
        returned: shown.length,
        matches: shown.map((match) => matchToJson(graph, match)),
      },
    };
  },
});

function describeQuery(input: {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
}): string {
  const parts: string[] = [];
  if (input.team && input.opponent) parts.push(`${input.team} vs ${input.opponent}`);
  else if (input.team) parts.push(input.team);
  if (input.competition) parts.push(input.competition);
  if (input.season !== undefined) parts.push(String(input.season));
  return parts.length > 0 ? parts.join(' / ') : 'All matches';
}

export const headToHeadTool = defineTool({
  name: 'head_to_head',
  title: 'Head-to-head record',
  description:
    'Compare two teams: every meeting in the data plus the win/draw/loss and goal totals. ' +
    'Answers "compare Palmeiras and Santos head-to-head" or "when did Flamengo last play Corinthians".',
  schema: z.object({
    teamA: nameArg('First team name.'),
    teamB: nameArg('Second team name.'),
    limit: limitArg(15),
    ...scopeShape,
  }),
  handler: (graph, input) => {
    const [teamA, teamB] = requireDistinctTeams(graph.teams, input.teamA, input.teamB);
    const result = headToHead(graph, teamA, teamB, scopeToFilter(input));

    const mostRecent = result.matches[result.matches.length - 1];
    const text = [
      formatHeadToHead(graph, result, input.limit),
      mostRecent ? `\nMost recent meeting: ${formatMatchLine(graph, mostRecent)}` : '',
    ]
      .filter(Boolean)
      .join('\n');

    return {
      text,
      data: {
        teamA: { id: teamA.id, name: teamA.name },
        teamB: { id: teamB.id, name: teamB.name },
        rivalry: result.rivalry ?? null,
        meetings: result.matches.length,
        aWins: result.aWins,
        bWins: result.bWins,
        draws: result.draws,
        aGoals: result.aGoals,
        bGoals: result.bGoals,
        withoutScore: result.withoutScore,
        aAtHome: result.aAtHome,
        aAway: result.aAway,
        matches: newestFirst(result.matches)
          .slice(0, input.limit)
          .map((match) => matchToJson(graph, match)),
      },
    };
  },
});

export const findDerbies = defineTool({
  name: 'find_derbies',
  title: 'Find derby matches',
  description:
    'List matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal, Atletiba and others). ' +
    'Answers "show me all derbies in 2023".',
  schema: z.object({
    rivalry: optionalNameArg('Restrict to one named derby, e.g. "Grenal".'),
    limit: limitArg(10).describe(
      'Maximum matches listed per derby. Each derby also reports its full count.',
    ),
    ...scopeShape,
  }),
  handler: (graph, input) => {
    const scope = scopeToFilter(input);
    const wanted = input.rivalry?.toLowerCase();
    const selected = RIVALRIES.filter(
      (rivalry) => !wanted || rivalry.name.toLowerCase().includes(wanted),
    );

    if (selected.length === 0) {
      const names = RIVALRIES.map((r) => r.name).join(', ');
      return {
        text: `No derby matches the name "${input.rivalry}". Known derbies: ${names}.`,
        data: { rivalries: RIVALRIES.map((r) => r.name), matches: [] },
      };
    }

    const groups = selected
      .map((rivalry) => {
        const matches = newestFirst(
          selectMatches(graph, { ...scope, teamId: rivalry.teams[0], opponentId: rivalry.teams[1] }),
        );
        return { rivalry, matches };
      })
      .filter((group) => group.matches.length > 0);

    const total = groups.reduce((sum, group) => sum + group.matches.length, 0);
    if (total === 0) {
      return {
        text: 'No derby matches found for that scope.',
        data: { total: 0, derbies: [] },
      };
    }

    const perDerbyLimit = input.limit;
    const text = groups
      .map((group) => {
        const [a, b] = group.rivalry.teams;
        const label = `${group.rivalry.name} (${graph.teams.get(a)?.name} vs ${graph.teams.get(b)?.name}) — ${group.matches.length} match(es)`;
        return `${label}\n${formatMatchList(graph, group.matches, perDerbyLimit)}`;
      })
      .join('\n\n');

    return {
      text,
      data: {
        total,
        derbies: groups.map((group) => ({
          name: group.rivalry.name,
          teams: group.rivalry.teams,
          count: group.matches.length,
          matches: group.matches.slice(0, perDerbyLimit).map((match) => matchToJson(graph, match)),
        })),
      },
    };
  },
});
