/**
 * The MCP interface: exposes the soccer knowledge base as tools an LLM can
 * call. Each tool returns readable text plus structured content; questions
 * that cannot be answered (unknown team, etc.) return an error result whose
 * text explains why and suggests alternatives.
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { QueryError, type Answer, type SoccerKnowledge } from './domain/knowledge.js';

const competition = z
  .string()
  .optional()
  .describe('Competition: "Brasileirão" (Serie A), "Copa do Brasil", "Libertadores", "Serie B" or "Serie C". Omit for all.');
const season = z.number().int().optional().describe('Season year, e.g. 2019');
const team = z.string().describe('Team name in any common form, e.g. "Flamengo", "Palmeiras-SP", "Sao Paulo", "Atletico Mineiro"');
const venue = z.enum(['home', 'away', 'all']).optional().describe('Only home matches, only away matches, or all (default)');
const limit = z.number().int().positive().optional().describe('Maximum number of items to list');

function respond(answer: () => Answer): CallToolResult {
  try {
    const { text, data } = answer();
    return { content: [{ type: 'text', text }], structuredContent: data };
  } catch (error) {
    if (error instanceof QueryError) {
      return { isError: true, content: [{ type: 'text', text: error.message }], structuredContent: error.data };
    }
    const message = error instanceof Error ? error.message : String(error);
    return { isError: true, content: [{ type: 'text', text: `Could not answer: ${message}` }] };
  }
}

export function createServer(knowledge: SoccerKnowledge): McpServer {
  const server = new McpServer(
    { name: 'brazilian-soccer', version: '1.0.0' },
    {
      instructions:
        'Answers questions about Brazilian soccer from Kaggle datasets: Brasileirão (2003-2023), Copa do Brasil (2012-2023), ' +
        'Copa Libertadores (2013-2022), Serie B/C (2014-2023) matches, and FIFA 19 player ratings. Team names may be given in any common form.',
    },
  );

  server.registerTool('search_matches', {
    title: 'Search matches',
    description:
      'Find matches by team, opponent, home/away, competition, season or date range, most recent first. ' +
      'With team and opponent, also gives the head-to-head summary. Use limit 1 for "when did X last play Y".',
    inputSchema: {
      team: team.optional(),
      opponent: team.optional().describe('Second team (matches between team and opponent)'),
      venue,
      competition,
      season,
      date_from: z.string().optional().describe('Earliest date, e.g. 2023-01-01 or 01/01/2023'),
      date_to: z.string().optional().describe('Latest date'),
      limit,
    },
  }, async (args) => respond(() => knowledge.searchMatches(args)));

  server.registerTool('head_to_head', {
    title: 'Head-to-head',
    description: 'Compare two teams head-to-head: wins each, draws, goals and recent meetings.',
    inputSchema: { team, opponent: team, competition, season },
  }, async (args) => respond(() => knowledge.headToHead(args)));

  server.registerTool('team_record', {
    title: 'Team record',
    description: "A team's win/draw/loss record, goals for/against and win rate, optionally for a season, competition and home/away.",
    inputSchema: { team, season, competition, venue },
  }, async (args) => respond(() => knowledge.teamRecord(args)));

  server.registerTool('team_competitions', {
    title: 'Team competitions',
    description: 'Which competitions a team has played in, with its record and seasons in each.',
    inputSchema: { team },
  }, async (args) => respond(() => knowledge.teamCompetitions(args)));

  server.registerTool('team_rankings', {
    title: 'Rank teams',
    description:
      'Rank teams by win_rate (best record), goals_for (most goals), goals_against (best defence), points, goal_difference or wins; ' +
      'optionally home/away only, for a season and competition. E.g. best home record, most goals in Serie A 2023.',
    inputSchema: {
      metric: z.enum(['win_rate', 'goals_for', 'goals_against', 'points', 'goal_difference', 'wins']).optional(),
      venue,
      season,
      competition,
      minMatches: z.number().int().positive().optional().describe('Ignore teams with fewer matches (default: a quarter of the most played)'),
      limit,
    },
  }, async (args) => respond(() => knowledge.teamRankings(args)));

  server.registerTool('team_profile', {
    title: 'Team profile',
    description: "Everything about a team: overall record, competitions, recent matches, and its FIFA squad (players' ratings).",
    inputSchema: { team },
  }, async (args) => respond(() => knowledge.teamProfile(args)));

  server.registerTool('standings', {
    title: 'League standings',
    description: 'Final league table for a season calculated from results, with champion and relegated teams. Default competition Brasileirão.',
    inputSchema: { competition, season: z.number().int().describe('Season year, e.g. 2019') },
  }, async (args) => respond(() => knowledge.standings(args)));

  server.registerTool('cup_finals', {
    title: 'Cup finals',
    description: 'Finals of a cup competition (default Copa do Brasil; also Libertadores) with the winner on aggregate, optionally for one season.',
    inputSchema: { competition, season },
  }, async (args) => respond(() => knowledge.cupFinals(args)));

  server.registerTool('knockout_bracket', {
    title: 'Knockout bracket',
    description: 'Knockout ties of a cup season (default Libertadores) stage by stage, with aggregate scores and who went through.',
    inputSchema: { competition, season: z.number().int().describe('Season year, e.g. 2018') },
  }, async (args) => respond(() => knowledge.knockoutBracket(args)));

  server.registerTool('find_derbies', {
    title: 'Find derbies',
    description: 'Matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal, Clássico Mineiro…), optionally by season, competition or team.',
    inputSchema: { season, competition, team: team.optional(), limit },
  }, async (args) => respond(() => knowledge.findDerbies(args)));

  server.registerTool('competition_stats', {
    title: 'Competition statistics',
    description: 'Average goals per match and home/draw/away win rates for a competition and/or season (or all data).',
    inputSchema: { competition, season },
  }, async (args) => respond(() => knowledge.competitionStats(args)));

  server.registerTool('biggest_wins', {
    title: 'Biggest wins',
    description: 'The largest winning margins, optionally by competition, season or team.',
    inputSchema: { competition, season, team: team.optional(), limit },
  }, async (args) => respond(() => knowledge.biggestWins(args)));

  server.registerTool('compare_seasons', {
    title: 'Compare seasons',
    description: 'Compare seasons side by side: matches, goals per match, result rates, champion and top-scoring team.',
    inputSchema: { seasons: z.array(z.number().int()).min(1).describe('Season years, e.g. [2018, 2019]'), competition },
  }, async (args) => respond(() => knowledge.compareSeasons(args)));

  server.registerTool('search_players', {
    title: 'Search players',
    description:
      'Search FIFA player data by name, nationality (e.g. "Brazil"), club (any common form), position (code like ST or group: goalkeeper, defender, midfielder, forward) and minimum rating; best rated first.',
    inputSchema: {
      name: z.string().optional(),
      nationality: z.string().optional(),
      club: z.string().optional(),
      position: z.string().optional(),
      minOverall: z.number().int().optional(),
      limit,
    },
  }, async (args) => respond(() => knowledge.searchPlayers(args)));

  server.registerTool('get_player', {
    title: 'Player details',
    description: 'Details of one player (club, position, ratings, attributes) by name; accents optional. Suggests similar names if not found.',
    inputSchema: { name: z.string() },
  }, async (args) => respond(() => knowledge.getPlayer(args)));

  server.registerTool('brazilian_club_squads', {
    title: 'Players at Brazilian clubs',
    description: 'For each Brazilian club in the FIFA data: number of players (optionally of one nationality) and average rating.',
    inputSchema: { nationality: z.string().optional().describe('e.g. "Brazil"; omit for all nationalities') },
  }, async (args) => respond(() => knowledge.brazilianClubSquads(args)));

  server.registerTool('dataset_info', {
    title: 'Dataset overview',
    description: 'Which datasets are loaded, how many records each has, and the competitions and seasons covered.',
    inputSchema: {},
  }, async () => respond(() => knowledge.datasetInfo()));

  return server;
}
