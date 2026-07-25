/**
 * Team-oriented tools: records, profiles, listing and leaderboards.
 */

import { z } from 'zod';
import { countryName } from '../domain/teams.js';
import { COMPETITIONS } from '../domain/types.js';
import { bullets, formatMatchLine, formatRecord, percent } from '../format/format.js';
import { requireTeam, selectMatches } from '../query/filters.js';
import { teamLeaderboard, teamProfile, teamStats } from '../query/teamQueries.js';
import { limitArg, matchToJson, nameArg, optionalNameArg, scopeShape, scopeToFilter } from './common.js';
import { defineTool } from './types.js';

export const teamStatsTool = defineTool({
  name: 'team_stats',
  title: 'Team statistics',
  description:
    'Win/draw/loss record, goals for and against, and win rate for one team, optionally narrowed to a ' +
    'competition, season, date range or venue. Answers "what is Corinthians\' home record in 2022".',
  schema: z.object({
    team: nameArg('Team name.'),
    venue: z
      .enum(['home', 'away', 'any'])
      .default('any')
      .describe('Restrict to home matches, away matches, or both.'),
    ...scopeShape,
  }),
  handler: (graph, input) => {
    const team = requireTeam(graph.teams, input.team);
    const filter = scopeToFilter(input);
    if (input.venue !== 'any') filter.venue = input.venue;
    const stats = teamStats(graph, team, filter);

    const scope = [
      input.season !== undefined ? String(input.season) : undefined,
      input.competition ? COMPETITIONS[filter.competition!].name : undefined,
      input.venue === 'home' ? 'home' : input.venue === 'away' ? 'away' : undefined,
    ]
      .filter(Boolean)
      .join(' ');

    const label = `${team.name}${scope ? ` ${scope}` : ''} record`;
    const sections = [formatRecord(stats.record, label)];

    if (input.venue === 'any' && stats.record.played > 0) {
      sections.push('', formatRecord(stats.home, 'Home'), '', formatRecord(stats.away, 'Away'));
    }
    if (stats.byCompetition.length > 1) {
      sections.push(
        '',
        'By competition:',
        bullets(
          stats.byCompetition.map(
            ({ competition, record }) =>
              `${COMPETITIONS[competition].name}: ${record.played} played, ${record.wins}W ${record.draws}D ${record.losses}L, ${percent(record.winRate)} win rate`,
          ),
        ),
      );
    }

    return {
      text: sections.join('\n'),
      data: {
        team: { id: team.id, name: team.name, state: team.state ?? null },
        record: stats.record,
        // A venue filter has already removed the other half, so reporting a
        // zeroed record for it would read as "played none" rather than
        // "excluded by your filter".
        home: input.venue === 'away' ? null : stats.home,
        away: input.venue === 'home' ? null : stats.away,
        venue: input.venue,
        byCompetition: stats.byCompetition,
        bySeason: stats.bySeason,
      },
    };
  },
});

export const teamProfileTool = defineTool({
  name: 'team_profile',
  title: 'Team profile',
  description:
    'Everything the graph knows about one club: overall record, competitions and seasons played, most ' +
    'frequent opponents, home stadiums, FIFA squad and the name variants used across the source files. ' +
    'Answers "what competitions has Palmeiras played in".',
  schema: z.object({
    team: nameArg('Team name.'),
  }),
  handler: (graph, input) => {
    const team = requireTeam(graph.teams, input.team);
    const profile = teamProfile(graph, team);

    const sections = [
      `${team.name}${team.state ? ` (${team.state})` : ''} — ${countryName(team.country)}`,
      '',
      formatRecord(profile.record, 'All competitions in the dataset'),
      '',
      'Competitions:',
      bullets(
        profile.competitions.map(
          ({ competition, matches, seasons }) =>
            `${COMPETITIONS[competition].name}: ${matches} matches, seasons ${seasons[0]}–${seasons[seasons.length - 1]}`,
        ),
      ),
    ];

    if (profile.firstMatch && profile.lastMatch) {
      sections.push(
        '',
        `First match in data: ${formatMatchLine(graph, profile.firstMatch)}`,
        `Last match in data:  ${formatMatchLine(graph, profile.lastMatch)}`,
      );
    }
    if (profile.topOpponents.length > 0) {
      sections.push(
        '',
        'Most frequent opponents:',
        bullets(profile.topOpponents.map((o) => `${o.team.name}: ${o.meetings} meetings`)),
      );
    }
    if (profile.venues.length > 0) {
      sections.push(
        '',
        'Home stadiums recorded:',
        bullets(profile.venues.map((v) => `${v.venue} (${v.matches} matches)`)),
      );
    }
    if (profile.squad.length > 0) {
      sections.push(
        '',
        `FIFA squad (${profile.squad.length} players):`,
        bullets(
          profile.squad
            .slice(0, 10)
            .map((p) => `${p.name} — ${p.overall ?? 'n/a'} (${p.position || 'n/a'})`),
        ),
      );
    } else {
      sections.push('', 'No FIFA squad in the player file for this club.');
    }
    sections.push('', `Known in the source files as: ${profile.knownAs.join(', ')}`);

    return {
      text: sections.join('\n'),
      data: {
        team: { id: team.id, name: team.name, state: team.state ?? null, country: team.country ?? null },
        record: profile.record,
        competitions: profile.competitions,
        topOpponents: profile.topOpponents.map((o) => ({ id: o.team.id, name: o.team.name, meetings: o.meetings })),
        venues: profile.venues,
        squad: profile.squad,
        knownAs: profile.knownAs,
        firstMatch: profile.firstMatch ? matchToJson(graph, profile.firstMatch) : null,
        lastMatch: profile.lastMatch ? matchToJson(graph, profile.lastMatch) : null,
      },
    };
  },
});

export const listTeams = defineTool({
  name: 'list_teams',
  title: 'List teams',
  description:
    'List the clubs present in the match data, optionally filtered by competition, season, state or a ' +
    'name fragment. Useful for discovering the exact spelling a later query should use.',
  schema: z.object({
    nameContains: optionalNameArg('Case- and accent-insensitive name fragment.'),
    state: z.string().max(2).optional().describe('Two-letter Brazilian state, e.g. "SP".'),
    limit: limitArg(60),
    ...scopeShape,
  }),
  handler: (graph, input) => {
    const filter = scopeToFilter(input);
    // Every scope argument is honoured by going through the shared selector,
    // rather than re-implementing two of the six and silently dropping the rest.
    const scoped = Object.keys(filter).length > 0;

    let teams = graph.teamsWithMatches();
    if (scoped) {
      const ids = new Set<string>();
      for (const match of selectMatches(graph, filter)) {
        ids.add(match.homeTeamId);
        ids.add(match.awayTeamId);
      }
      teams = teams.filter((team) => ids.has(team.id));
    }
    if (input.state) {
      const wanted = input.state.toUpperCase();
      teams = teams.filter((team) => team.state === wanted);
    }
    if (input.nameContains) {
      const { candidates } = graph.teams.resolveQuery(input.nameContains);
      const wanted = input.nameContains.toLowerCase();
      const ids = new Set(candidates.map((c) => c.id));
      teams = teams.filter(
        (team) => ids.has(team.id) || team.name.toLowerCase().includes(wanted),
      );
    }

    const shown = teams.slice(0, input.limit);
    return {
      text: [
        `${teams.length} team(s) found.`,
        bullets(
          shown.map(
            (team) =>
              `${team.name} [${team.id}]${team.state ? ` — ${team.state}` : ''}${team.country ? ` — ${countryName(team.country)}` : ''}`,
          ),
        ),
      ].join('\n'),
      data: {
        total: teams.length,
        teams: shown.map((team) => ({
          id: team.id,
          name: team.name,
          state: team.state ?? null,
          country: team.country ?? null,
          aliases: [...team.aliases],
        })),
      },
    };
  },
});

export const teamRankings = defineTool({
  name: 'team_rankings',
  title: 'Rank teams',
  description:
    'Rank teams within a competition, season or date range by points, wins, win rate, goals scored or ' +
    'goals conceded, at home, away or overall. Answers "which team has the best away record" and ' +
    '"which team scored the most goals in Serie A 2023".',
  schema: z.object({
    metric: z
      .enum(['points', 'wins', 'winRate', 'goalsFor', 'goalsAgainst', 'goalDifference'])
      .default('points')
      .describe('Record field to rank by.'),
    venue: z
      .enum(['home', 'away', 'any'])
      .default('any')
      .describe('Count only home matches, only away matches, or all of them.'),
    order: z
      .enum(['best', 'worst'])
      .default('best')
      .describe(
        'Whether position 1 is the best or the worst team by this metric. ' +
          'For goalsAgainst "best" means fewest conceded.',
      ),
    minimumPlayed: z.number().int().min(1).default(5).describe('Ignore teams with fewer matches.'),
    limit: limitArg(10),
    ...scopeShape,
  }),
  handler: (graph, input) => {
    const filter = scopeToFilter(input);
    const rows = teamLeaderboard(graph, filter, input.venue, input.minimumPlayed);

    // For every metric except goals conceded, more is better. Ranking by a raw
    // descending sort would put the leakiest defence at position 1 under the
    // heading "ranked by goalsAgainst", which reads as the opposite of the
    // truth to anyone asking who conceded fewest.
    const lowerIsBetter = input.metric === 'goalsAgainst';
    const bestFirst = input.order === 'best';
    const direction = lowerIsBetter === bestFirst ? 1 : -1;

    rows.sort((a, b) => {
      const left = a.record[input.metric];
      const right = b.record[input.metric];
      return (left - right) * direction || a.team.name.localeCompare(b.team.name);
    });

    const shown = rows.slice(0, input.limit);
    const venueLabel = input.venue === 'any' ? 'overall' : input.venue;
    const scope = [
      input.competition ? COMPETITIONS[filter.competition!].name : 'all competitions',
      input.season !== undefined ? String(input.season) : undefined,
    ]
      .filter(Boolean)
      .join(' ');

    const lines = shown.map((row, index) => {
      const r = row.record;
      const value = input.metric === 'winRate' ? percent(r.winRate) : String(r[input.metric]);
      return `${index + 1}. ${row.team.name} — ${input.metric}: ${value} (${r.played} played, ${r.wins}W ${r.draws}D ${r.losses}L, GF ${r.goalsFor} GA ${r.goalsAgainst})`;
    });

    return {
      text: [
        `Teams ranked by ${input.metric} (${venueLabel}) — ${scope}, minimum ${input.minimumPlayed} matches:`,
        lines.length > 0 ? lines.join('\n') : 'No teams met the criteria.',
      ].join('\n'),
      data: {
        metric: input.metric,
        venue: input.venue,
        total: rows.length,
        rankings: shown.map((row, index) => ({
          position: index + 1,
          teamId: row.team.id,
          team: row.team.name,
          ...row.record,
        })),
      },
    };
  },
});
