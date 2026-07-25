/**
 * Competition tools: derived league tables, cup brackets and dataset coverage.
 */

import { z } from 'zod';
import { COMPETITIONS, type CompetitionId } from '../domain/types.js';
import { bullets, formatMatchList, formatStandings, titleise } from '../format/format.js';
import { resolveCompetition, stageMatches } from '../query/filters.js';
import { cupSummary, decideTie, standings } from '../query/competitionQueries.js';
import { COMPETITION_HELP, competitionArg, limitArg, matchToJson } from './common.js';
import { defineTool } from './types.js';

export const competitionStandings = defineTool({
  name: 'competition_standings',
  title: 'Competition standings',
  description:
    'League table for a season, computed from the match results in the data. Includes points, ' +
    'wins/draws/losses, goals, the inferred champion and the inferred relegation places. ' +
    'Answers "who won the 2019 Brasileirão" and "which teams were relegated in 2020".',
  schema: z.object({
    competition: competitionArg.default('serie-a').describe(COMPETITION_HELP),
    season: z.number().int().describe('Season year, e.g. 2019.'),
    limit: limitArg(30),
  }),
  handler: (graph, input) => {
    const competition = resolveCompetition(input.competition);
    const table = standings(graph, competition, input.season);

    if (table.rows.length === 0) {
      const available = graph.seasonsOf(competition);
      return {
        text:
          `No ${COMPETITIONS[competition].name} matches for ${input.season}. ` +
          (available.length > 0
            ? `Seasons available: ${available[0]}–${available[available.length - 1]}.`
            : 'This competition has no data.'),
        data: { rows: [], availableSeasons: available },
      };
    }

    return {
      text: formatStandings(table, input.limit),
      data: {
        competition,
        season: input.season,
        complete: table.complete,
        matchesPlayed: table.matchesPlayed,
        expectedMatches: table.expectedMatches,
        champion: table.champion
          ? { teamId: table.champion.team.id, team: table.champion.team.name, points: table.champion.record.points }
          : null,
        relegated: table.relegated.map((row) => ({
          position: row.position,
          teamId: row.team.id,
          team: row.team.name,
          points: row.record.points,
        })),
        notes: table.notes,
        rows: table.rows.slice(0, input.limit).map((row) => ({
          position: row.position,
          teamId: row.team.id,
          team: row.team.name,
          ...row.record,
        })),
      },
    };
  },
});

export const competitionBracket = defineTool({
  name: 'competition_bracket',
  title: 'Cup bracket',
  description:
    'Stage-by-stage results for a knockout competition season, with the winner inferred from the ' +
    'final when the aggregate score decides it. Answers "show the 2018 Copa Libertadores bracket" ' +
    'and "find all Copa do Brasil finals".',
  schema: z.object({
    competition: competitionArg.default('libertadores').describe(COMPETITION_HELP),
    season: z.number().int().describe('Season year, e.g. 2018.'),
    stage: z.string().optional().describe('Show only stages whose label contains this text.'),
    limit: limitArg(20).describe('Maximum matches shown per stage.'),
  }),
  handler: (graph, input) => {
    const competition = resolveCompetition(input.competition);
    const summary = cupSummary(graph, competition, input.season);

    const wanted = input.stage;
    const stages = wanted
      ? summary.stages.filter((stage) => stageMatches(stage.stage, wanted))
      : summary.stages;

    if (stages.length === 0) {
      const available = graph.seasonsOf(competition);
      return {
        text:
          `No ${COMPETITIONS[competition].name} matches for ${input.season}${wanted ? ` at stage "${input.stage}"` : ''}. ` +
          (available.length > 0
            ? `Seasons available: ${available[0]}–${available[available.length - 1]}.`
            : ''),
        data: { stages: [], availableSeasons: available },
      };
    }

    const sections = [`${input.season} ${COMPETITIONS[competition].name}:`];
    for (const stage of stages) {
      sections.push('', `${titleise(stage.stage)} (${stage.matches.length} match(es)):`);
      sections.push(formatMatchList(graph, stage.matches, input.limit));
      const winner = decideTie(graph, stage.matches);
      if (stage.matches.length <= 2 && winner) {
        sections.push(`Winner on aggregate: ${winner.name}`);
      }
    }
    if (summary.winner) sections.push('', `Champion: ${summary.winner.name}`);
    if (summary.notes.length > 0) sections.push('', ...summary.notes.map((n) => `Note: ${n}`));

    return {
      text: sections.join('\n'),
      data: {
        competition,
        season: input.season,
        winner: summary.winner ? { id: summary.winner.id, name: summary.winner.name } : null,
        notes: summary.notes,
        stages: stages.map((stage) => ({
          stage: stage.stage,
          matches: stage.matches.slice(0, input.limit).map((match) => matchToJson(graph, match)),
          total: stage.matches.length,
        })),
      },
    };
  },
});

export const datasetInfo = defineTool({
  name: 'dataset_info',
  title: 'Dataset coverage',
  description:
    'What the graph contains: source files and their row counts, how many fixtures survived ' +
    'de-duplication, the seasons covered by each competition, and the number of teams and players. ' +
    'Call this first when unsure whether the data can answer a question.',
  schema: z.object({}),
  handler: (graph) => {
    const info = graph.info;
    const lines = [
      `Brazilian soccer knowledge graph — loaded in ${info.loadMillis} ms from ${info.dataDir}`,
      '',
      'Source files (rows read):',
      bullets(Object.entries(info.rawMatchRows).map(([file, count]) => `${file}: ${count}`)),
      `- fifa_data.csv: ${info.rawPlayerRows}`,
      '',
      `Merged fixtures: ${info.mergedMatches} (duplicates across overlapping files collapsed into one match each)`,
      `Teams: ${info.teams}`,
      `Players: ${info.players}`,
      `Rows skipped as unparseable: ${info.skippedRows}`,
      '',
      'Competitions:',
      bullets(
        info.competitions
          .filter((c) => c.matches > 0)
          .map(
            (c) =>
              `${c.name} [${c.id}]: ${c.matches} matches, seasons ${c.seasons[0]}–${c.seasons[c.seasons.length - 1]}`,
          ),
      ),
    ];

    return {
      text: lines.join('\n'),
      data: info as unknown as Record<string, unknown>,
    };
  },
});

export const listSeasons = defineTool({
  name: 'list_seasons',
  title: 'List seasons',
  description: 'Seasons available for a competition, with the number of matches in each.',
  schema: z.object({
    competition: competitionArg.default('serie-a').describe(COMPETITION_HELP),
  }),
  handler: (graph, input) => {
    const competition: CompetitionId = resolveCompetition(input.competition);
    const seasons = graph.seasonsOf(competition).map((season) => ({
      season,
      matches: graph.matchesIn(competition, season).length,
    }));

    return {
      text: [
        `${COMPETITIONS[competition].name} — ${seasons.length} season(s):`,
        bullets(seasons.map((s) => `${s.season}: ${s.matches} matches`)),
      ].join('\n'),
      data: { competition, seasons },
    };
  },
});
