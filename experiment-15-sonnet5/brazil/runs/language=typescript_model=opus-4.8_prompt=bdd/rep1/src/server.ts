/**
 * MCP server wiring: registers one tool per query capability described in the
 * specification (match / team / player / competition / statistical queries).
 *
 * The server is transport-agnostic here — {@link createServer} builds the
 * McpServer with a loaded {@link DataStore}; the entry point (index.ts)
 * connects it to a stdio transport.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { DataStore, BRASILEIRAO } from "./dataStore.js";
import {
  findMatches,
  headToHead,
  lastMeeting,
} from "./queries/matches.js";
import { teamStats } from "./queries/teams.js";
import { brasileiraoStandings, brasileiraoChampion } from "./queries/competitions.js";
import { filterPlayers, rankByOverall, summarizeByClub } from "./queries/players.js";
import { aggregateStats, biggestWins, topScoringTeams } from "./queries/stats.js";
import {
  formatMatchList,
  formatHeadToHead,
  formatMatchLine,
  formatTeamStats,
  formatStandings,
  formatPlayerList,
  formatClubSummaries,
  formatAggregate,
  formatBiggestWins,
  formatTopScoringTeams,
} from "./format.js";
import type { MatchFilter } from "./queries/filters.js";

/** Wrap a plain string into the MCP tool-result content shape. */
function text(value: string) {
  return { content: [{ type: "text" as const, text: value }] };
}

/**
 * Build a fully-wired MCP server backed by an already-loaded data store.
 * Exposed separately from the transport so tests can exercise tools directly.
 */
export function createServer(store: DataStore): McpServer {
  const server = new McpServer(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    {
      instructions:
        "Query Brazilian soccer data: matches (Brasileirão, Copa do Brasil, Libertadores, " +
        "and extended stats), team records, FIFA player attributes, calculated league " +
        "standings, and aggregate statistics. Team names are matched leniently across the " +
        "different dataset naming conventions.",
    },
  );

  const matches = store.matches;
  const players = store.players;

  // --- 1. Match queries -----------------------------------------------------
  server.registerTool(
    "find_matches",
    {
      title: "Find matches",
      description:
        "Find matches by team, competition, season, and/or date range. " +
        "Examples: 'What matches did Palmeiras play in 2023?', 'Find Copa do Brasil matches'.",
      inputSchema: {
        team: z.string().optional().describe("Team on either side (home or away)"),
        homeTeam: z.string().optional().describe("Require this team as the home side"),
        awayTeam: z.string().optional().describe("Require this team as the away side"),
        competition: z
          .string()
          .optional()
          .describe("Competition, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores', 'Serie A'"),
        season: z.number().int().optional().describe("Season / year, e.g. 2023"),
        from: z.string().optional().describe("Inclusive start date YYYY-MM-DD"),
        to: z.string().optional().describe("Inclusive end date YYYY-MM-DD"),
        limit: z.number().int().positive().max(200).optional().describe("Max matches to return"),
      },
    },
    async (args) => {
      const filter: MatchFilter = {
        team: args.team,
        homeTeam: args.homeTeam,
        awayTeam: args.awayTeam,
        competition: args.competition,
        season: args.season,
        from: args.from,
        to: args.to,
      };
      const result = findMatches(matches, filter, {
        direction: "desc",
        limit: args.limit ?? 200,
      });
      const heading = describeMatchQuery(filter);
      return text(formatMatchList(result, heading, args.limit ?? 25));
    },
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head record",
      description:
        "Compare two teams head-to-head across all competitions in the data. " +
        "Example: 'Compare Palmeiras and Santos head-to-head'.",
      inputSchema: {
        teamA: z.string().describe("First team"),
        teamB: z.string().describe("Second team"),
        competition: z.string().optional().describe("Optional competition filter"),
        season: z.number().int().optional().describe("Optional season filter"),
      },
    },
    async (args) => {
      const { record, matches: h2h } = headToHead(matches, args.teamA, args.teamB, {
        competition: args.competition,
        season: args.season,
      });
      return text(formatHeadToHead(record, h2h));
    },
  );

  server.registerTool(
    "last_meeting",
    {
      title: "Last meeting between two teams",
      description:
        "Find the most recent match between two teams. " +
        "Example: 'When did Flamengo last play Corinthians? What was the score?'.",
      inputSchema: {
        teamA: z.string().describe("First team"),
        teamB: z.string().describe("Second team"),
      },
    },
    async (args) => {
      const match = lastMeeting(matches, args.teamA, args.teamB);
      if (!match) {
        return text(`No match found between ${args.teamA} and ${args.teamB} in the dataset.`);
      }
      return text(`Most recent ${args.teamA} vs ${args.teamB} meeting:\n- ${formatMatchLine(match)}`);
    },
  );

  // --- 2. Team queries ------------------------------------------------------
  server.registerTool(
    "team_record",
    {
      title: "Team record and statistics",
      description:
        "Win/draw/loss record, goals for/against, and home/away split for a team, " +
        "optionally scoped by competition and season. " +
        "Example: \"What is Corinthians' home record in 2022?\".",
      inputSchema: {
        team: z.string().describe("Team name"),
        competition: z.string().optional().describe("Optional competition filter"),
        season: z.number().int().optional().describe("Optional season filter"),
      },
    },
    async (args) => {
      const stats = teamStats(matches, args.team, {
        competition: args.competition,
        season: args.season,
      });
      const scope = [args.season, args.competition].filter(Boolean).join(" ") || "all competitions";
      return text(formatTeamStats(stats, scope));
    },
  );

  // --- 3. Player queries ----------------------------------------------------
  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search the FIFA player database by name, nationality, club, position, and/or " +
        "minimum rating; results ranked by overall rating. " +
        "Examples: 'Who is Gabriel Barbosa?', 'Highest-rated players at Flamengo', " +
        "'Top Brazilian players', 'Forwards from Sao Paulo'.",
      inputSchema: {
        name: z.string().optional().describe("Player name substring"),
        nationality: z.string().optional().describe("Nationality, e.g. 'Brazil'"),
        club: z.string().optional().describe("Club substring, e.g. 'Flamengo'"),
        position: z
          .string()
          .optional()
          .describe("Position code (ST, GK, ...) or role (forward, midfielder, defender, goalkeeper)"),
        minOverall: z.number().int().optional().describe("Minimum overall rating"),
        limit: z.number().int().positive().max(100).optional().describe("Max players to return"),
      },
    },
    async (args) => {
      const filtered = filterPlayers(players, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.minOverall,
      });
      const ranked = rankByOverall(filtered, args.limit ?? 25);
      const heading = describePlayerQuery(args) + ` (${filtered.length} match(es)):`;
      return text(formatPlayerList(ranked, heading, args.limit ?? 25));
    },
  );

  server.registerTool(
    "players_by_club_summary",
    {
      title: "Player counts by club",
      description:
        "Group players (optionally filtered by nationality) by club, showing counts and " +
        "average ratings. Example: 'Brazilian players at Brazilian clubs'.",
      inputSchema: {
        nationality: z.string().optional().describe("Nationality filter, e.g. 'Brazil'"),
        club: z.string().optional().describe("Club substring filter"),
        limit: z.number().int().positive().max(100).optional().describe("Max clubs to return"),
      },
    },
    async (args) => {
      const filtered = filterPlayers(players, {
        nationality: args.nationality,
        club: args.club,
      });
      const summaries = summarizeByClub(filtered, args.limit ?? 15);
      const heading =
        `Clubs${args.nationality ? ` for ${args.nationality} players` : ""} ` +
        `(${filtered.length} players across ${summaries.length} clubs):`;
      return text(formatClubSummaries(summaries, heading, args.limit ?? 15));
    },
  );

  // --- 4. Competition queries ----------------------------------------------
  server.registerTool(
    "league_standings",
    {
      title: "Brasileirão standings",
      description:
        "Calculate the Brasileirão Série A final standings for a season from match results " +
        "(3 pts win / 1 pt draw). Example: 'Who won the 2019 Brasileirão?'.",
      inputSchema: {
        season: z.number().int().describe("Season / year, e.g. 2019"),
        limit: z.number().int().positive().max(30).optional().describe("Number of rows to show"),
      },
    },
    async (args) => {
      const table = brasileiraoStandings(matches, args.season);
      const heading = `${args.season} ${BRASILEIRAO} standings (calculated from matches):`;
      return text(formatStandings(table, heading, args.limit ?? 20));
    },
  );

  server.registerTool(
    "competition_champion",
    {
      title: "Brasileirão champion",
      description:
        "Identify the Brasileirão Série A champion for a season (top of the calculated table). " +
        "Example: 'Who won the 2019 Brasileirão?'.",
      inputSchema: {
        season: z.number().int().describe("Season / year"),
      },
    },
    async (args) => {
      const champ = brasileiraoChampion(matches, args.season);
      if (!champ) {
        return text(`No Brasileirão data available for ${args.season}.`);
      }
      return text(
        `${args.season} ${BRASILEIRAO} champion: ${champ.team} — ${champ.points} pts ` +
          `(${champ.wins}W, ${champ.draws}D, ${champ.losses}L, GD ${champ.goalDifference >= 0 ? "+" : ""}${champ.goalDifference}).`,
      );
    },
  );

  // --- 5. Statistical analysis ---------------------------------------------
  server.registerTool(
    "aggregate_stats",
    {
      title: "Aggregate match statistics",
      description:
        "Average goals per match, home/away win rates over a set of matches. " +
        "Example: \"What's the average goals per match in the Brasileirão?\".",
      inputSchema: {
        competition: z.string().optional().describe("Optional competition filter"),
        season: z.number().int().optional().describe("Optional season filter"),
        team: z.string().optional().describe("Optional team filter"),
      },
    },
    async (args) => {
      const agg = aggregateStats(matches, {
        competition: args.competition,
        season: args.season,
        team: args.team,
      });
      const scope =
        [args.season, args.competition, args.team].filter(Boolean).join(" ") || "all matches";
      return text(formatAggregate(agg, scope));
    },
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest victories",
      description:
        "List the matches with the largest goal margins. " +
        "Example: 'Show me the biggest wins in the dataset'.",
      inputSchema: {
        competition: z.string().optional().describe("Optional competition filter"),
        season: z.number().int().optional().describe("Optional season filter"),
        team: z.string().optional().describe("Optional team filter"),
        limit: z.number().int().positive().max(50).optional().describe("Number of matches"),
      },
    },
    async (args) => {
      const wins = biggestWins(
        matches,
        { competition: args.competition, season: args.season, team: args.team },
        args.limit ?? 10,
      );
      const scope =
        [args.season, args.competition, args.team].filter(Boolean).join(" ") || "all matches";
      return text(formatBiggestWins(wins, `Biggest victories (${scope}):`));
    },
  );

  server.registerTool(
    "top_scoring_teams",
    {
      title: "Top scoring teams",
      description:
        "Rank teams by total goals scored over a set of matches. " +
        "Example: 'Which team scored the most goals in Serie A 2023?'.",
      inputSchema: {
        competition: z.string().optional().describe("Optional competition filter"),
        season: z.number().int().optional().describe("Optional season filter"),
        limit: z.number().int().positive().max(50).optional().describe("Number of teams"),
      },
    },
    async (args) => {
      const totals = topScoringTeams(
        matches,
        { competition: args.competition, season: args.season },
        args.limit ?? 10,
      );
      const scope = [args.season, args.competition].filter(Boolean).join(" ") || "all matches";
      return text(formatTopScoringTeams(totals, `Top scoring teams (${scope}):`));
    },
  );

  return server;
}

function describeMatchQuery(filter: MatchFilter): string {
  const parts: string[] = [];
  if (filter.homeTeam) parts.push(`home team ${filter.homeTeam}`);
  if (filter.awayTeam) parts.push(`away team ${filter.awayTeam}`);
  if (filter.team) parts.push(`team ${filter.team}`);
  if (filter.competition) parts.push(`competition ${filter.competition}`);
  if (filter.season) parts.push(`season ${filter.season}`);
  if (filter.from || filter.to) parts.push(`dates ${filter.from ?? "…"}..${filter.to ?? "…"}`);
  return `Matches (${parts.join(", ") || "all"}):`;
}

function describePlayerQuery(args: {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
}): string {
  const parts: string[] = [];
  if (args.name) parts.push(`name~"${args.name}"`);
  if (args.nationality) parts.push(args.nationality);
  if (args.club) parts.push(`club~"${args.club}"`);
  if (args.position) parts.push(args.position);
  if (args.minOverall) parts.push(`overall>=${args.minOverall}`);
  return `Players ${parts.length ? `(${parts.join(", ")})` : ""}`.trim();
}
