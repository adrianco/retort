import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getDataset } from "./dataLoader.js";
import { formatMatchLine, findMatches, headToHead } from "./queries/matchQueries.js";
import { teamCompetitions, teamRecord } from "./queries/teamQueries.js";
import { listCompetitions, standings } from "./queries/competitionQueries.js";
import { averageGoals, bestVenueRecord, biggestWins } from "./queries/statsQueries.js";
import { brazilianPlayersByClub, playersByClub, searchPlayers } from "./queries/playerQueries.js";

function textResult(text: string) {
  return { content: [{ type: "text" as const, text }] };
}

function playerLine(p: {
  name: string;
  overall: number | null;
  potential: number | null;
  position: string;
  club: string;
  nationality: string;
  age: number | null;
}): string {
  return `${p.name} - Overall: ${p.overall ?? "?"}, Potential: ${p.potential ?? "?"}, Position: ${p.position || "?"}, Club: ${p.club || "Free agent"}, Nationality: ${p.nationality}, Age: ${p.age ?? "?"}`;
}

export function createServer(): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.registerTool(
    "find_matches",
    {
      title: "Find matches",
      description:
        "Search match results across Brasileirao, Copa do Brasil, Copa Libertadores and the extended BR-Football dataset. " +
        "Filter by team, opponent, competition, season and/or date range (YYYY-MM-DD). " +
        "Team names are normalized so 'Flamengo', 'Flamengo-RJ' and similar variants all match.",
      inputSchema: {
        team: z.string().optional().describe("A team name, e.g. 'Flamengo' or 'Palmeiras-SP'"),
        opponent: z.string().optional().describe("Restrict to matches against this specific opponent"),
        competition: z
          .string()
          .optional()
          .describe("Competition filter, e.g. 'Brasileirao', 'Copa do Brasil', 'Libertadores', 'Serie B'"),
        season: z.number().int().optional().describe("Season/year, e.g. 2023"),
        dateFrom: z.string().optional().describe("Earliest date, inclusive, format YYYY-MM-DD"),
        dateTo: z.string().optional().describe("Latest date, inclusive, format YYYY-MM-DD"),
        limit: z.number().int().min(1).max(200).optional().describe("Max matches to return (default 25)"),
      },
    },
    async (args) => {
      const dataset = getDataset();
      const result = findMatches(dataset, args);
      if (result.total === 0) {
        return textResult("No matches found for the given filters.");
      }
      const lines = result.matches.map(formatMatchLine);
      const remaining = result.total - result.matches.length;
      const suffix = remaining > 0 ? `\n... (${remaining} more match${remaining === 1 ? "" : "es"} in dataset)` : "";
      return textResult(`Found ${result.total} match(es):\n${lines.join("\n")}${suffix}`);
    },
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head record",
      description:
        "Get the head-to-head record between two teams: overall wins/draws/losses, goal totals, and a list of recent matches. " +
        "Useful for derby questions like 'Flamengo vs Fluminense'.",
      inputSchema: {
        teamA: z.string().describe("First team name"),
        teamB: z.string().describe("Second team name"),
        competition: z.string().optional().describe("Restrict to a competition, e.g. 'Brasileirao'"),
        season: z.number().int().optional().describe("Restrict to a season/year"),
        limit: z.number().int().min(1).max(200).optional().describe("Max matches to list (default 25)"),
      },
    },
    async ({ teamA, teamB, competition, season, limit }) => {
      const dataset = getDataset();
      const result = headToHead(dataset, teamA, teamB, { competition, season, limit });
      if (result.totalMatches === 0) {
        return textResult(`No matches found between ${teamA} and ${teamB}.`);
      }
      const lines = result.matches.map(formatMatchLine);
      const remaining = result.totalMatches - result.matches.length;
      const suffix = remaining > 0 ? `\n... (${remaining} more match${remaining === 1 ? "" : "es"} in dataset)` : "";
      return textResult(
        `${result.teamA} vs ${result.teamB}:\n${lines.join("\n")}${suffix}\n\n` +
          `Head-to-head in dataset: ${result.teamA} ${result.teamAWins} wins, ${result.teamB} ${result.teamBWins} wins, ${result.draws} draws ` +
          `(goals ${result.teamAGoals}-${result.teamBGoals})`,
      );
    },
  );

  server.registerTool(
    "team_record",
    {
      title: "Team win/loss/draw record",
      description:
        "Compute a team's match record (wins, draws, losses, goals for/against, win rate), optionally scoped to a " +
        "competition, season, and/or home/away venue. Use for questions like \"Corinthians' home record in 2022\".",
      inputSchema: {
        team: z.string().describe("Team name, e.g. 'Corinthians'"),
        competition: z.string().optional().describe("Restrict to a competition, e.g. 'Brasileirao'"),
        season: z.number().int().optional().describe("Restrict to a season/year"),
        venue: z.enum(["home", "away", "all"]).optional().describe("Restrict to home games, away games, or all (default all)"),
      },
    },
    async ({ team, competition, season, venue }) => {
      const dataset = getDataset();
      const record = teamRecord(dataset, team, { competition, season, venue });
      if (record.matchesPlayed === 0) {
        return textResult(`No matches found for ${team} with the given filters.`);
      }
      const scope = [competition, season, venue && venue !== "all" ? `${venue} games` : null]
        .filter(Boolean)
        .join(", ");
      return textResult(
        `${record.team} record${scope ? ` (${scope})` : ""}:\n` +
          `- Matches: ${record.matchesPlayed}\n` +
          `- Wins: ${record.wins}, Draws: ${record.draws}, Losses: ${record.losses}\n` +
          `- Goals For: ${record.goalsFor}, Goals Against: ${record.goalsAgainst}\n` +
          `- Win rate: ${record.winRatePct.toFixed(1)}%`,
      );
    },
  );

  server.registerTool(
    "team_competitions",
    {
      title: "List a team's competitions",
      description: "List which competitions/datasets a team appears in, with match counts and seasons covered.",
      inputSchema: {
        team: z.string().describe("Team name"),
      },
    },
    async ({ team }) => {
      const dataset = getDataset();
      const result = teamCompetitions(dataset, team);
      if (result.competitions.length === 0) {
        return textResult(`No matches found for ${team}.`);
      }
      const lines = result.competitions.map(
        (c) => `- ${c.competition}: ${c.matches} matches (seasons ${c.seasons[0]}-${c.seasons[c.seasons.length - 1]})`,
      );
      return textResult(`${team} appears in:\n${lines.join("\n")}`);
    },
  );

  server.registerTool(
    "standings",
    {
      title: "Competition standings",
      description:
        "Calculate final or current standings for a competition/season from match results (points, W/D/L, goal difference). " +
        "Works best for league-format competitions like 'Brasileirao'.",
      inputSchema: {
        competition: z.string().describe("Competition name, e.g. 'Brasileirao', 'Serie B'"),
        season: z.number().int().describe("Season/year, e.g. 2019"),
      },
    },
    async ({ competition, season }) => {
      const dataset = getDataset();
      const result = standings(dataset, competition, season);
      if (result.table.length === 0) {
        return textResult(`No match data found for ${competition} ${season}.`);
      }
      const lines = result.table.map(
        (row, i) =>
          `${i + 1}. ${row.team} - ${row.points} pts (${row.wins}W, ${row.draws}D, ${row.losses}L), GD ${row.goalDifference >= 0 ? "+" : ""}${row.goalDifference}, GF ${row.goalsFor}` +
          (i === 0 ? " - Champion" : ""),
      );
      return textResult(
        `${result.competition} ${result.season} standings (calculated from ${result.matchesUsed} matches):\n${lines.join("\n")}`,
      );
    },
  );

  server.registerTool(
    "list_competitions",
    {
      title: "List available competitions",
      description: "List every competition/tournament label available across the loaded datasets, with match counts and season coverage.",
      inputSchema: {},
    },
    async () => {
      const dataset = getDataset();
      const infos = listCompetitions(dataset);
      const lines = infos.map(
        (c) => `- ${c.competition} (source: ${c.source}): ${c.matches} matches, seasons ${c.seasons[0]}-${c.seasons[c.seasons.length - 1]}`,
      );
      return textResult(`Available competitions:\n${lines.join("\n")}`);
    },
  );

  server.registerTool(
    "average_goals",
    {
      title: "Average goals and outcome rates",
      description: "Compute average goals per match plus home/draw/away win rates, optionally scoped to a competition and/or season.",
      inputSchema: {
        competition: z.string().optional().describe("Restrict to a competition, e.g. 'Brasileirao'"),
        season: z.number().int().optional().describe("Restrict to a season/year"),
      },
    },
    async ({ competition, season }) => {
      const dataset = getDataset();
      const result = averageGoals(dataset, { competition, season });
      if (result.matches === 0) {
        return textResult("No matches found for the given filters.");
      }
      return textResult(
        `Based on ${result.matches} matches${competition ? ` (${competition}${season ? ` ${season}` : ""})` : ""}:\n` +
          `Average goals per match: ${result.averageGoalsPerMatch.toFixed(2)}\n` +
          `Home win rate: ${result.homeWinRatePct.toFixed(1)}%, Draw rate: ${result.drawRatePct.toFixed(1)}%, Away win rate: ${result.awayWinRatePct.toFixed(1)}%`,
      );
    },
  );

  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins",
      description: "List the largest-margin victories in the dataset, optionally scoped to a competition and/or season.",
      inputSchema: {
        competition: z.string().optional().describe("Restrict to a competition, e.g. 'Libertadores'"),
        season: z.number().int().optional().describe("Restrict to a season/year"),
        limit: z.number().int().min(1).max(50).optional().describe("Number of results (default 10)"),
      },
    },
    async ({ competition, season, limit }) => {
      const dataset = getDataset();
      const results = biggestWins(dataset, { competition, season, limit });
      if (results.length === 0) {
        return textResult("No matches found for the given filters.");
      }
      const lines = results.map((r, i) => `${i + 1}. ${formatMatchLine(r.match)} (margin: ${r.goalDifference})`);
      return textResult(`Biggest victories:\n${lines.join("\n")}`);
    },
  );

  server.registerTool(
    "best_venue_record",
    {
      title: "Best home/away record",
      description:
        "Rank teams by win rate at a given venue (home or away), optionally scoped to a competition/season. " +
        "Teams with fewer than a minimum number of matches are excluded to avoid small-sample outliers.",
      inputSchema: {
        venue: z.enum(["home", "away"]).describe("Which venue to rank teams by"),
        competition: z.string().optional().describe("Restrict to a competition, e.g. 'Brasileirao'"),
        season: z.number().int().optional().describe("Restrict to a season/year"),
        minMatches: z.number().int().min(1).optional().describe("Minimum matches played to qualify (default 5)"),
        limit: z.number().int().min(1).max(50).optional().describe("Number of results (default 10)"),
      },
    },
    async ({ venue, competition, season, minMatches, limit }) => {
      const dataset = getDataset();
      const rows = bestVenueRecord(dataset, venue, { competition, season, minMatches, limit });
      if (rows.length === 0) {
        return textResult("No qualifying teams found for the given filters.");
      }
      const lines = rows.map(
        (r, i) =>
          `${i + 1}. ${r.team} - ${r.winRatePct.toFixed(1)}% win rate (${r.wins}W ${r.draws}D ${r.losses}L in ${r.played} ${venue} matches), GF ${r.goalsFor} GA ${r.goalsAgainst}`,
      );
      return textResult(`Best ${venue} records:\n${lines.join("\n")}`);
    },
  );

  server.registerTool(
    "search_players",
    {
      title: "Search FIFA players",
      description:
        "Search the FIFA player database by name, nationality, club and/or position. Results are sorted by Overall rating descending. " +
        "Use nationality 'Brazil' to find Brazilian players.",
      inputSchema: {
        name: z.string().optional().describe("Player name (substring match), e.g. 'Neymar'"),
        nationality: z.string().optional().describe("Nationality, e.g. 'Brazil'"),
        club: z.string().optional().describe("Club name (substring match), e.g. 'Santos'"),
        position: z.string().optional().describe("Position code, e.g. 'ST', 'GK', 'CDM'"),
        limit: z.number().int().min(1).max(100).optional().describe("Max players to return (default 25)"),
      },
    },
    async (args) => {
      const dataset = getDataset();
      const result = searchPlayers(dataset, args);
      if (result.total === 0) {
        return textResult("No players found for the given filters.");
      }
      const lines = result.players.map((p, i) => `${i + 1}. ${playerLine(p)}`);
      const remaining = result.total - result.players.length;
      const suffix = remaining > 0 ? `\n... (${remaining} more player${remaining === 1 ? "" : "s"} in dataset)` : "";
      return textResult(`Found ${result.total} player(s):\n${lines.join("\n")}${suffix}`);
    },
  );

  server.registerTool(
    "players_by_club",
    {
      title: "Players at a club",
      description: "Summarize FIFA players at a given club: player count, average Overall rating, and top-rated players.",
      inputSchema: {
        club: z.string().describe("Club name (substring match), e.g. 'Flamengo'"),
        limit: z.number().int().min(1).max(50).optional().describe("Number of top players to list (default 10)"),
      },
    },
    async ({ club, limit }) => {
      const dataset = getDataset();
      const result = playersByClub(dataset, club, { limit });
      if (result.playerCount === 0) {
        return textResult(`No players found at a club matching "${club}".`);
      }
      const lines = result.topPlayers.map((p, i) => `${i + 1}. ${playerLine(p)}`);
      return textResult(
        `${result.club}: ${result.playerCount} players (avg rating: ${result.averageOverall.toFixed(1)})\n${lines.join("\n")}`,
      );
    },
  );

  server.registerTool(
    "brazilian_players_by_club",
    {
      title: "Brazilian players grouped by club",
      description:
        "Group Brazilian (nationality) FIFA players by club, restricted to clubs whose name matches one of the given fragments. " +
        "Useful for 'Brazilian players at Brazilian clubs' style questions.",
      inputSchema: {
        clubs: z
          .array(z.string())
          .describe("List of club name fragments to include, e.g. ['Flamengo', 'Palmeiras', 'Santos']"),
      },
    },
    async ({ clubs }) => {
      const dataset = getDataset();
      const rows = brazilianPlayersByClub(dataset, clubs);
      if (rows.length === 0) {
        return textResult("No Brazilian players found at the given clubs.");
      }
      const lines = rows.map((r) => `- ${r.club}: ${r.playerCount} players (avg rating: ${r.averageOverall.toFixed(1)})`);
      return textResult(`Brazilian players at Brazilian clubs:\n${lines.join("\n")}`);
    },
  );

  return server;
}
