/**
 * The MCP tools through which an LLM asks the knowledge base questions.
 * Each tool answers with readable text plus the same answer as structured data.
 */
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { allDerbies } from './derbies.js';
import * as format from './format.js';
import type { SoccerKnowledge } from './knowledge.js';

const team = z.string().describe('Team name in any common form, e.g. "Flamengo", "Palmeiras-SP", "Sao Paulo FC", "Atlético-MG"');
const competition = z
  .string()
  .describe('Competition: "Brasileirão" (Série A), "Série B", "Série C", "Copa do Brasil" or "Copa Libertadores"');
const season = z.number().int().describe('Season year, e.g. 2019');
const venue = z.enum(['home', 'away', 'any']).describe('Only home matches, only away matches, or any (default)');
const date = z.string().describe('Date as YYYY-MM-DD or DD/MM/YYYY');
const limit = (n: number) => z.number().int().min(1).max(500).optional().describe(`Maximum number of results (default ${n})`);

function answer(text: string, data: object): CallToolResult {
  return { content: [{ type: 'text', text }], structuredContent: data as { [key: string]: unknown } };
}

function failure(error: unknown): CallToolResult {
  const message = error instanceof Error ? error.message : String(error);
  return { content: [{ type: 'text', text: message }], isError: true };
}

function safely<A>(handler: (args: A) => CallToolResult): (args: A) => Promise<CallToolResult> {
  return async (args: A) => {
    try {
      return handler(args);
    } catch (error) {
      return failure(error);
    }
  };
}

export function registerTools(server: McpServer, kb: SoccerKnowledge): void {
  server.registerTool(
    'find_matches',
    {
      title: 'Find matches',
      description:
        'Search matches across all datasets (Brasileirão, Copa do Brasil, Copa Libertadores, Série B/C) by team, opponent, venue, competition, season, date range or stage. Results are most recent first. Use limit 1 with team+opponent to get the last meeting. With team and opponent it also gives the head-to-head summary.',
      inputSchema: {
        team: team.optional(),
        opponent: team.optional().describe('Second team, to find matches between the two'),
        venue: venue.optional(),
        competition: competition.optional(),
        season: season.optional(),
        date_from: date.optional(),
        date_to: date.optional(),
        stage: z.string().optional().describe('Knockout stage, e.g. "final", "semifinals", "quarterfinals", "round of 16", "group stage"'),
        limit: limit(20),
      },
    },
    safely((a) => {
      const result = kb.findMatches(
        { team: a.team, opponent: a.opponent, venue: a.venue, competition: a.competition, season: a.season, dateFrom: a.date_from, dateTo: a.date_to, stage: a.stage },
        a.limit ?? 20,
      );
      const title = [
        a.team && a.opponent ? `${a.team} vs ${a.opponent}` : a.team ? `${a.team} matches` : 'Matches',
        a.competition,
        a.season,
        a.stage,
      ].filter(Boolean).join(' - ');
      return answer(format.formatMatches(result, title), result);
    }),
  );

  server.registerTool(
    'head_to_head',
    {
      title: 'Head-to-head record',
      description: 'Compare two teams: wins, draws, losses and goals from the first team\'s point of view, split by competition, with recent meetings.',
      inputSchema: { team, opponent: team, competition: competition.optional(), season: season.optional(), limit: limit(10) },
    },
    safely((a) => {
      const result = kb.headToHead(a.team, a.opponent, a.competition, a.season, a.limit ?? 10);
      return answer(format.formatHeadToHead(result), result);
    }),
  );

  server.registerTool(
    'team_record',
    {
      title: 'Team record',
      description: 'Win/draw/loss record, goals for and against and win rate of a team, optionally for a season, competition, venue (home/away) or date range.',
      inputSchema: { team, season: season.optional(), competition: competition.optional(), venue: venue.optional(), date_from: date.optional(), date_to: date.optional() },
    },
    safely((a) => {
      const result = kb.teamRecord({ team: a.team, season: a.season, competition: a.competition, venue: a.venue, dateFrom: a.date_from, dateTo: a.date_to });
      return answer(format.formatTeamRecord(result), result);
    }),
  );

  server.registerTool(
    'team_competitions',
    {
      title: 'Competitions a team played in',
      description: 'Which competitions a team has played in according to the datasets, with seasons and record in each.',
      inputSchema: { team },
    },
    safely((a) => {
      const result = kb.teamCompetitions(a.team);
      return answer(format.formatCompetitions(result), result);
    }),
  );

  server.registerTool(
    'team_rankings',
    {
      title: 'Rank teams',
      description:
        'Rank teams by goals scored, fewest goals conceded, points, wins, overall win rate, home win rate or away win rate, optionally within a competition and season. E.g. "which team scored most goals in 2019", "best home record", "best away record".',
      inputSchema: {
        measure: z.enum(['goals_scored', 'goals_conceded', 'points', 'wins', 'win_rate', 'home_win_rate', 'away_win_rate']),
        competition: competition.optional(),
        season: season.optional(),
        min_matches: z.number().int().min(1).optional().describe('Minimum matches for a team to be ranked (rates default to 30% of the most matches played)'),
        limit: limit(10),
      },
    },
    safely((a) => {
      const result = kb.teamRankings(a.measure, { competition: a.competition, season: a.season, minMatches: a.min_matches }, a.limit ?? 10);
      return answer(format.formatRankings(result), result);
    }),
  );

  server.registerTool(
    'team_profile',
    {
      title: 'Team profile',
      description: 'Everything known about a club across files: overall match record, competitions, recent matches and its squad from the FIFA player data.',
      inputSchema: { team },
    },
    safely((a) => {
      const result = kb.teamProfile(a.team);
      return answer(format.formatTeamProfile(result), result);
    }),
  );

  server.registerTool(
    'standings',
    {
      title: 'League standings',
      description: 'Final league table for a season, calculated from match results (3 points a win), with champion and relegated teams. Answers "who won the 2019 Brasileirão" and "who was relegated in 2020".',
      inputSchema: { season, competition: competition.optional().describe('League competition (default Brasileirão Série A)') },
    },
    safely((a) => {
      const result = kb.standings(a.season, a.competition ?? 'Brasileirão');
      return answer(format.formatStandings(result), result);
    }),
  );

  server.registerTool(
    'knockout_bracket',
    {
      title: 'Knockout bracket',
      description: 'The knockout rounds (round of 16, quarter-finals, semi-finals, final) of a Copa do Brasil or Copa Libertadores season.',
      inputSchema: { competition, season },
    },
    safely((a) => {
      const result = kb.knockoutBracket(a.competition, a.season);
      return answer(format.formatBracket(result), result);
    }),
  );

  server.registerTool(
    'derbies',
    {
      title: 'Derbies',
      description: `Matches between traditional rivals, optionally for a season, competition or team. Known derbies: ${allDerbies().join('; ')}.`,
      inputSchema: { season: season.optional(), competition: competition.optional(), team: team.optional(), limit: limit(100) },
    },
    safely((a) => {
      const result = kb.derbies({ season: a.season, competition: a.competition, team: a.team }, a.limit ?? 100);
      const title = ['Derbies', a.team, a.competition, a.season].filter(Boolean).join(' - ');
      return answer(format.formatMatches(result, title), result);
    }),
  );

  server.registerTool(
    'match_statistics',
    {
      title: 'Match statistics',
      description: 'Aggregate statistics: number of matches, goals per match, home/draw/away rates, average corners and shots where recorded. Optionally for a competition, season or team.',
      inputSchema: { competition: competition.optional(), season: season.optional(), team: team.optional() },
    },
    safely((a) => {
      const result = kb.matchStatistics({ competition: a.competition, season: a.season, team: a.team });
      return answer(format.formatStatistics(result), result);
    }),
  );

  server.registerTool(
    'biggest_wins',
    {
      title: 'Biggest wins',
      description: 'The largest winning margins, optionally within a competition, season or for a team.',
      inputSchema: { competition: competition.optional(), season: season.optional(), team: team.optional(), limit: limit(10) },
    },
    safely((a) => {
      const result = kb.biggestWins({ competition: a.competition, season: a.season, team: a.team }, a.limit ?? 10);
      return answer(format.formatBiggestWins(result), result);
    }),
  );

  server.registerTool(
    'compare_seasons',
    {
      title: 'Compare seasons',
      description: 'Compare seasons of a competition side by side: matches, goals per match, home/draw/away rates, champion and top scoring team.',
      inputSchema: { seasons: z.array(season).min(1).max(30), competition: competition.optional().describe('Default Brasileirão Série A') },
    },
    safely((a) => {
      const result = kb.compareSeasons(a.seasons, a.competition ?? 'Brasileirão');
      return answer(format.formatSeasonComparison(result), result);
    }),
  );

  server.registerTool(
    'search_players',
    {
      title: 'Search players',
      description: 'Search the FIFA player database by name, nationality (country or demonym, e.g. "Brazil"/"Brazilian"), club, position (code like ST/GK or group: forward, midfielder, defender, goalkeeper) and minimum rating. Sorted by overall rating, best first.',
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        min_overall: z.number().int().optional(),
        limit: limit(25),
      },
    },
    safely((a) => {
      const result = kb.searchPlayers({ name: a.name, nationality: a.nationality, club: a.club, position: a.position, minOverall: a.min_overall }, a.limit ?? 25);
      const title = ['Players', a.name && `named "${a.name}"`, a.nationality && `from ${a.nationality}`, a.club && `at ${a.club}`, a.position && `playing ${a.position}`]
        .filter(Boolean)
        .join(' ');
      return answer(format.formatPlayers(result, title), result);
    }),
  );

  server.registerTool(
    'player_profile',
    {
      title: 'Player profile',
      description: 'Full profile of a player found by name (e.g. "Who is Gabriel Barbosa?"): club, position, ratings, physical details and best attributes.',
      inputSchema: { name: z.string() },
    },
    safely((a) => {
      const result = kb.playerProfile(a.name);
      return answer(format.formatPlayerProfile(result), result);
    }),
  );

  server.registerTool(
    'players_by_club',
    {
      title: 'Players grouped by club',
      description: 'How many players (optionally of one nationality) each club has, with average rating. By default only Brazilian clubs (clubs that played in the Brasileirão).',
      inputSchema: {
        nationality: z.string().optional(),
        brazilian_clubs_only: z.boolean().optional().describe('Default true'),
        limit: limit(30),
      },
    },
    safely((a) => {
      const result = kb.playersByClub({ nationality: a.nationality, brazilianClubsOnly: a.brazilian_clubs_only }, a.limit ?? 30);
      return answer(format.formatPlayersByClub(result), result);
    }),
  );

  server.registerTool(
    'dataset_overview',
    {
      title: 'Dataset overview',
      description: 'Which datasets are loaded, how many records each has, and what seasons and competitions they cover.',
      inputSchema: {},
    },
    safely(() => {
      const result = kb.overview();
      return answer(format.formatOverview(result), result);
    }),
  );
}
