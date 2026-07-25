/**
 * Player tools over the FIFA database, including the cross-file join from a
 * club's squad to that club's match history.
 */

import { z } from 'zod';
import { COMPETITIONS } from '../domain/types.js';
import {
  bullets,
  formatPlayerList,
  formatPlayerProfile,
  formatRecord,
  money,
} from '../format/format.js';
import { requireTeam } from '../query/filters.js';
import { brazilianClubSummaries, searchPlayers, squadOf, summariseSquad } from '../query/playerQueries.js';
import { buildRecord } from '../query/teamQueries.js';
import { limitArg, nameArg, optionalNameArg } from './common.js';
import { defineTool } from './types.js';

const POSITION_GROUPS = ['Goalkeeper', 'Defender', 'Midfielder', 'Forward', 'Unknown'] as const;

export const searchPlayersTool = defineTool({
  name: 'search_players',
  title: 'Search players',
  description:
    'Search the FIFA player database by name, nationality, club, position, rating or age. ' +
    'Answers "find all Brazilian players", "who are the highest-rated players at Fluminense" and ' +
    '"show me all forwards from Santos". Club matching accepts either the FIFA club label or a ' +
    'canonical team name.',
  schema: z.object({
    name: optionalNameArg('Full or partial player name.'),
    nationality: optionalNameArg('Country of birth, e.g. "Brazil".'),
    club: optionalNameArg('Club name or fragment.'),
    position: z.string().max(3).optional().describe('Exact FIFA position code, e.g. "LW", "GK".'),
    positionGroup: z.enum(POSITION_GROUPS).optional().describe('Coarse position group.'),
    minOverall: z.number().int().min(0).max(99).optional().describe('Lowest FIFA overall rating to include.'),
    maxOverall: z.number().int().min(0).max(99).optional().describe('Highest FIFA overall rating to include.'),
    minAge: z.number().int().min(0).optional().describe('Youngest age to include.'),
    maxAge: z.number().int().min(0).optional().describe('Oldest age to include.'),
    sortBy: z
      .enum(['overall', 'potential', 'age', 'value', 'wage', 'name'])
      .default('overall')
      .describe('Field to sort by.'),
    ascending: z.boolean().default(false).describe('Sort ascending instead of descending.'),
    limit: limitArg(20),
  }),
  handler: (graph, input) => {
    const result = searchPlayers(graph, input);
    const criteria = describeCriteria(input);

    const text = [
      `${result.total} player(s) matched${criteria ? ` (${criteria})` : ''}. Showing ${result.players.length}.`,
      formatPlayerList(result.players),
      ...result.notes.map((note) => `\nNote: ${note}`),
    ].join('\n');

    return {
      text,
      data: {
        total: result.total,
        notes: result.notes,
        players: result.players.map((player) => ({
          id: player.id,
          name: player.name,
          age: player.age,
          nationality: player.nationality,
          overall: player.overall,
          potential: player.potential,
          club: player.club,
          clubTeamId: player.clubTeamId ?? null,
          position: player.position,
          positionGroup: player.positionGroup,
          jerseyNumber: player.jerseyNumber,
          valueEur: player.valueEur,
          wageEur: player.wageEur,
        })),
      },
    };
  },
});

function describeCriteria(input: Record<string, unknown>): string {
  const interesting = ['name', 'nationality', 'club', 'position', 'positionGroup', 'minOverall', 'maxOverall', 'minAge', 'maxAge'];
  return interesting
    .filter((key) => input[key] !== undefined)
    .map((key) => `${key}=${String(input[key])}`)
    .join(', ');
}

export const playerProfileTool = defineTool({
  name: 'player_profile',
  title: 'Player profile',
  description:
    'Full FIFA record for one player: ratings, physical attributes, contract, value and best skills. ' +
    'Answers "who is Gabriel Barbosa".',
  schema: z.object({
    name: optionalNameArg('Player name; the closest match is returned.'),
    playerId: z.string().max(20).optional().describe('Exact FIFA player id.'),
  }),
  handler: (graph, input) => {
    if (!input.name && !input.playerId) {
      throw new Error('Provide either `name` or `playerId`.');
    }

    const search = input.playerId ? undefined : searchPlayers(graph, { name: input.name!, limit: 5 });
    const player = input.playerId ? graph.getPlayer(input.playerId) : search?.players[0];

    if (!player) {
      const label = input.playerId ?? input.name;
      return {
        text: `No player found for "${label}".`,
        data: { found: false },
      };
    }

    const sections: string[] = [];
    // The FIFA edition in this dataset omits many players, and its name forms
    // are abbreviated, so an inexact hit has to be stated rather than passed
    // off as the player that was asked for.
    if (search && search.notes.length > 0) {
      sections.push(...search.notes.map((note) => `Note: ${note}`), '');
    }
    sections.push(formatPlayerProfile(player));
    if (search && search.players.length > 1) {
      sections.push(
        '',
        `Other close matches: ${search.players.slice(1).map((p) => p.name).join(', ')}`,
      );
    }
    if (player.clubTeamId) {
      const team = graph.teams.get(player.clubTeamId);
      const matches = graph.matchesFor(player.clubTeamId);
      if (team && matches.length > 0) {
        sections.push(
          '',
          `Club in the match data: ${team.name} — ${matches.length} matches across ` +
            graph
              .competitionsOf(team.id)
              .map((c) => COMPETITIONS[c.competition].name)
              .join(', '),
        );
      }
    }

    return {
      text: sections.join('\n'),
      data: {
        found: true,
        exact: search ? search.notes.length === 0 : true,
        notes: search?.notes ?? [],
        player: { ...player, valueFormatted: money(player.valueEur), wageFormatted: money(player.wageEur) },
      },
    };
  },
});

export const clubSquad = defineTool({
  name: 'club_squad',
  title: 'Club squad and match record',
  description:
    'Join the FIFA squad of a Brazilian club to that club\'s match history: squad list with average ' +
    'rating plus the club\'s overall record. Call with no arguments for a coverage summary of every ' +
    'Brazilian club that has a squad in the player file.',
  schema: z.object({
    team: optionalNameArg('Club name. Omit for the coverage summary.'),
    limit: limitArg(30),
  }),
  handler: (graph, input) => {
    if (!input.team) {
      const all = brazilianClubSummaries(graph);
      const summaries = all.slice(0, input.limit);
      const total = all.reduce((sum, s) => sum + s.players, 0);
      return {
        text: [
          `Brazilian clubs with a squad in the FIFA player file: ${all.length} (${total} players).` +
            (summaries.length < all.length ? ` Showing ${summaries.length}.` : ''),
          bullets(
            summaries.map(
              (s) =>
                `${s.club}: ${s.players} players (avg rating ${s.averageOverall.toFixed(1)})${s.topPlayer ? `, best ${s.topPlayer.name} ${s.topPlayer.overall}` : ''}`,
            ),
          ),
          '',
          'Note: the FIFA edition in this dataset licensed only some Brazilian clubs, so several ' +
            'well-known teams that appear in the match data have no squad here.',
        ].join('\n'),
        data: {
          total: all.length,
          clubs: summaries.map((s) => ({
            club: s.club,
            teamId: s.teamId ?? null,
            players: s.players,
            averageOverall: Number(s.averageOverall.toFixed(2)),
            topPlayer: s.topPlayer ? { name: s.topPlayer.name, overall: s.topPlayer.overall } : null,
          })),
        },
      };
    }

    const team = requireTeam(graph.teams, input.team);
    const squad = squadOf(graph, team.id);
    const record = buildRecord(graph.matchesFor(team.id), team.id);
    const summary = summariseSquad(team.name, squad);
    const average = summary.averageOverall;

    const sections = [
      `${team.name} — ${squad.length} player(s) in the FIFA file` +
        (average > 0 ? `, average rating ${average.toFixed(1)}` : ''),
    ];
    sections.push(squad.length > 0 ? formatPlayerList(squad.slice(0, input.limit)) : 'No FIFA squad for this club.');
    sections.push('', formatRecord(record, `${team.name} match record in the dataset`));

    return {
      text: sections.join('\n'),
      data: {
        team: { id: team.id, name: team.name },
        squadSize: squad.length,
        averageOverall: Number(average.toFixed(2)),
        record,
        players: squad.slice(0, input.limit).map((p) => ({
          id: p.id,
          name: p.name,
          overall: p.overall,
          potential: p.potential,
          position: p.position,
          age: p.age,
          nationality: p.nationality,
        })),
      },
    };
  },
});
