import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { DataStore, Competition } from './data/types.js';
import { findMatches, formatMatch, headToHead } from './queries/matches.js';
import {
  teamStats,
  teamSplit,
  teamCompetitions,
  topScoringTeams,
} from './queries/teams.js';
import { findPlayers, formatPlayer, playersByClub } from './queries/players.js';
import { standings, seasonSummary, availableSeasons } from './queries/competitions.js';
import {
  overallStats,
  biggestWins,
  highestScoringMatches,
} from './queries/stats.js';
import { parseDate } from './data/normalize.js';

const competitionSchema = z
  .enum(['Brasileirao', 'Copa do Brasil', 'Libertadores', 'BR-Football', 'Brasileirao-Historical'])
  .describe('Competition name');

function text(content: unknown) {
  return {
    content: [
      {
        type: 'text' as const,
        text: typeof content === 'string' ? content : JSON.stringify(content, null, 2),
      },
    ],
  };
}

function dateFromString(s: string | undefined): Date | undefined {
  if (!s) return undefined;
  const d = parseDate(s);
  return d ?? undefined;
}

export function buildServer(store: DataStore): McpServer {
  const server = new McpServer(
    { name: 'brazilian-soccer-mcp', version: '1.0.0' },
    {
      capabilities: { tools: {}, resources: {} },
    },
  );

  // ---------------- Match queries ----------------
  server.registerTool(
    'find_matches',
    {
      description:
        'Search for matches by team, competition, season, or date range. Returns a list of matches with date, teams, score, and competition.',
      inputSchema: {
        team: z.string().optional().describe('Team name (matches as home OR away)'),
        opponent: z.string().optional().describe('When set with team, finds matches between these two teams'),
        homeTeam: z.string().optional(),
        awayTeam: z.string().optional(),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        startDate: z.string().optional().describe('ISO date (YYYY-MM-DD) or DD/MM/YYYY'),
        endDate: z.string().optional(),
        stage: z.string().optional().describe('Tournament stage (e.g., "final")'),
        limit: z.number().int().positive().max(500).default(50).optional(),
      },
    },
    async (args) => {
      const matches = findMatches(store, {
        team: args.team,
        opponentTeam: args.opponent,
        homeTeam: args.homeTeam,
        awayTeam: args.awayTeam,
        competition: args.competition as Competition | undefined,
        season: args.season,
        startDate: dateFromString(args.startDate),
        endDate: dateFromString(args.endDate),
        stage: args.stage,
        limit: args.limit ?? 50,
      });
      const out = {
        count: matches.length,
        matches: matches.map((m) => ({
          date: m.date.toISOString().slice(0, 10),
          home: m.homeTeamRaw,
          away: m.awayTeamRaw,
          score: `${m.homeGoals}-${m.awayGoals}`,
          competition: m.competition,
          season: m.season,
          round: m.round,
          stage: m.stage,
          formatted: formatMatch(m),
        })),
      };
      return text(out);
    },
  );

  server.registerTool(
    'head_to_head',
    {
      description: 'Compare two teams head-to-head across all data: matches played, wins, draws, goals.',
      inputSchema: {
        team: z.string(),
        opponent: z.string(),
      },
    },
    async (args) => text(headToHead(store, args.team, args.opponent)),
  );

  // ---------------- Team queries ----------------
  server.registerTool(
    'team_stats',
    {
      description:
        'Get aggregate stats for a team (wins, losses, draws, goals) — optionally filtered by competition, season, and venue (home/away/all).',
      inputSchema: {
        team: z.string(),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        venue: z.enum(['home', 'away', 'all']).optional(),
      },
    },
    async (args) =>
      text(
        teamStats(store, args.team, {
          competition: args.competition as Competition | undefined,
          season: args.season,
          venue: args.venue,
        }),
      ),
  );

  server.registerTool(
    'team_split',
    {
      description: 'Get overall, home, and away stats for a team side-by-side.',
      inputSchema: {
        team: z.string(),
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) =>
      text(
        teamSplit(store, args.team, {
          competition: args.competition as Competition | undefined,
          season: args.season,
        }),
      ),
  );

  server.registerTool(
    'team_competitions',
    {
      description: 'List competitions a team has appeared in (with match counts).',
      inputSchema: { team: z.string() },
    },
    async (args) => {
      const map = teamCompetitions(store, args.team);
      return text(Object.fromEntries(map.entries()));
    },
  );

  server.registerTool(
    'top_scoring_teams',
    {
      description: 'Rank teams by goals scored, optionally within a competition / season.',
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(50).default(10).optional(),
      },
    },
    async (args) =>
      text(
        topScoringTeams(store, {
          competition: args.competition as Competition | undefined,
          season: args.season,
          limit: args.limit ?? 10,
        }),
      ),
  );

  // ---------------- Player queries ----------------
  server.registerTool(
    'find_players',
    {
      description:
        'Search FIFA player data by name, nationality, club, position, rating range or age range.',
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional().describe('e.g., "Brazil"'),
        club: z.string().optional(),
        position: z.string().optional().describe('e.g., "ST", "GK", "LW"'),
        minOverall: z.number().int().optional(),
        maxOverall: z.number().int().optional(),
        minAge: z.number().int().optional(),
        maxAge: z.number().int().optional(),
        sortBy: z.enum(['overall', 'potential', 'age', 'name']).optional(),
        sortOrder: z.enum(['asc', 'desc']).optional(),
        limit: z.number().int().positive().max(200).default(25).optional(),
      },
    },
    async (args) => {
      const players = findPlayers(store, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
        maxOverall: args.maxOverall,
        minAge: args.minAge,
        maxAge: args.maxAge,
        sortBy: args.sortBy,
        sortOrder: args.sortOrder,
        limit: args.limit ?? 25,
      });
      return text({
        count: players.length,
        players: players.map((p) => ({
          ...p,
          formatted: formatPlayer(p),
        })),
      });
    },
  );

  server.registerTool(
    'players_by_club',
    {
      description:
        'Group players by club; returns count, average overall rating, and top players per club. Optionally filter by nationality.',
      inputSchema: {
        nationality: z.string().optional(),
        limitTopPerClub: z.number().int().positive().max(20).default(5).optional(),
        limitClubs: z.number().int().positive().max(100).default(25).optional(),
      },
    },
    async (args) => {
      const summary = playersByClub(store, {
        nationality: args.nationality,
        limitTopPerClub: args.limitTopPerClub ?? 5,
      });
      const limited = summary.slice(0, args.limitClubs ?? 25);
      return text(limited);
    },
  );

  // ---------------- Competition queries ----------------
  server.registerTool(
    'standings',
    {
      description:
        'Compute league standings for a competition + season from match results. 3 pts win, 1 pt draw. Sorted by points, then GD, then GF.',
      inputSchema: {
        competition: competitionSchema,
        season: z.number().int(),
      },
    },
    async (args) =>
      text(standings(store, args.competition as Competition, args.season)),
  );

  server.registerTool(
    'season_summary',
    {
      description: 'Summary of a season: matches, goals, average goals/match, home/away/draw rates.',
      inputSchema: {
        competition: competitionSchema,
        season: z.number().int(),
      },
    },
    async (args) =>
      text(seasonSummary(store, args.competition as Competition, args.season)),
  );

  server.registerTool(
    'available_seasons',
    {
      description: 'List seasons present in the data, optionally for a specific competition.',
      inputSchema: {
        competition: competitionSchema.optional(),
      },
    },
    async (args) =>
      text(availableSeasons(store, args.competition as Competition | undefined)),
  );

  // ---------------- Statistical analysis ----------------
  server.registerTool(
    'overall_stats',
    {
      description: 'Aggregate stats across the dataset, optionally scoped by competition/season.',
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
      },
    },
    async (args) =>
      text(
        overallStats(store, {
          competition: args.competition as Competition | undefined,
          season: args.season,
        }),
      ),
  );

  server.registerTool(
    'biggest_wins',
    {
      description: 'Return matches with the largest goal margins.',
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(50).default(10).optional(),
      },
    },
    async (args) => {
      const wins = biggestWins(store, {
        competition: args.competition as Competition | undefined,
        season: args.season,
        limit: args.limit ?? 10,
      });
      return text(
        wins.map((w) => ({
          date: w.match.date.toISOString().slice(0, 10),
          home: w.match.homeTeamRaw,
          away: w.match.awayTeamRaw,
          score: `${w.match.homeGoals}-${w.match.awayGoals}`,
          competition: w.match.competition,
          margin: w.margin,
        })),
      );
    },
  );

  server.registerTool(
    'highest_scoring_matches',
    {
      description: 'Return matches with the most total goals.',
      inputSchema: {
        competition: competitionSchema.optional(),
        season: z.number().int().optional(),
        limit: z.number().int().positive().max(50).default(10).optional(),
      },
    },
    async (args) => {
      const matches = highestScoringMatches(store, {
        competition: args.competition as Competition | undefined,
        season: args.season,
        limit: args.limit ?? 10,
      });
      return text(
        matches.map((w) => ({
          date: w.match.date.toISOString().slice(0, 10),
          home: w.match.homeTeamRaw,
          away: w.match.awayTeamRaw,
          score: `${w.match.homeGoals}-${w.match.awayGoals}`,
          competition: w.match.competition,
          totalGoals: w.totalGoals,
        })),
      );
    },
  );

  server.registerTool(
    'dataset_info',
    {
      description: 'Return counts of loaded matches and players, plus per-competition breakdown.',
      inputSchema: {},
    },
    async () => {
      const byComp: Record<string, number> = {};
      for (const m of store.matches) {
        byComp[m.competition] = (byComp[m.competition] ?? 0) + 1;
      }
      return text({
        totalMatches: store.matches.length,
        totalPlayers: store.players.length,
        matchesByCompetition: byComp,
      });
    },
  );

  return server;
}
