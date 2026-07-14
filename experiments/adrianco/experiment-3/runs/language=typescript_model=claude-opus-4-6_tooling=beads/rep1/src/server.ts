import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { SoccerData } from "./data.js";

export function createServer(data: SoccerData): McpServer {
  data.load();

  const server = new McpServer({
    name: "brazilian-soccer",
    version: "1.0.0",
  });

  server.tool(
    "search_matches",
    "Search for matches by team, competition, season, or date range",
    {
      team: z.string().optional().describe("Team name (matches home or away)"),
      home_team: z.string().optional().describe("Home team name"),
      away_team: z.string().optional().describe("Away team name"),
      competition: z.string().optional().describe("Competition name (e.g. Brasileirão, Copa do Brasil, Libertadores)"),
      season: z.number().optional().describe("Season year"),
      date_from: z.string().optional().describe("Start date (YYYY-MM-DD)"),
      date_to: z.string().optional().describe("End date (YYYY-MM-DD)"),
      limit: z.number().optional().describe("Max results (default 50)"),
    },
    async (params) => {
      const matches = data.searchMatches({
        team: params.team,
        homeTeam: params.home_team,
        awayTeam: params.away_team,
        competition: params.competition,
        season: params.season,
        dateFrom: params.date_from,
        dateTo: params.date_to,
        limit: params.limit,
      });

      if (matches.length === 0) {
        return { content: [{ type: "text", text: "No matches found for the given criteria." }] };
      }

      const lines = matches.map(
        (m) =>
          `${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition}${m.round ? `, Round ${m.round}` : ""}${m.stage ? `, ${m.stage}` : ""})`
      );

      return {
        content: [{ type: "text", text: `Found ${matches.length} matches:\n\n${lines.join("\n")}` }],
      };
    }
  );

  server.tool(
    "head_to_head",
    "Compare two teams head-to-head with win/loss/draw record",
    {
      team1: z.string().describe("First team name"),
      team2: z.string().describe("Second team name"),
    },
    async (params) => {
      const h2h = data.headToHead(params.team1, params.team2);

      if (h2h.matches.length === 0) {
        return {
          content: [{ type: "text", text: `No matches found between ${params.team1} and ${params.team2}.` }],
        };
      }

      const recentMatches = h2h.matches.slice(0, 10).map(
        (m) => `  ${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition})`
      );

      const text = [
        `${params.team1} vs ${params.team2} — ${h2h.matches.length} matches:`,
        `  ${params.team1} wins: ${h2h.team1Wins}`,
        `  ${params.team2} wins: ${h2h.team2Wins}`,
        `  Draws: ${h2h.draws}`,
        `  Goals: ${params.team1} ${h2h.team1Goals} - ${h2h.team2Goals} ${params.team2}`,
        "",
        "Recent matches:",
        ...recentMatches,
      ].join("\n");

      return { content: [{ type: "text", text }] };
    }
  );

  server.tool(
    "team_stats",
    "Get team statistics: wins, losses, draws, goals for a given team, optionally filtered by season, competition, or home/away",
    {
      team: z.string().describe("Team name"),
      season: z.number().optional().describe("Season year"),
      competition: z.string().optional().describe("Competition name"),
      home_only: z.boolean().optional().describe("Only home matches"),
      away_only: z.boolean().optional().describe("Only away matches"),
    },
    async (params) => {
      const stats = data.teamStats(params.team, {
        season: params.season,
        competition: params.competition,
        homeOnly: params.home_only,
        awayOnly: params.away_only,
      });

      if (stats.matches === 0) {
        return { content: [{ type: "text", text: `No matches found for ${params.team}.` }] };
      }

      const winRate = Math.round((stats.wins / stats.matches) * 1000) / 10;
      const location = params.home_only ? "home " : params.away_only ? "away " : "";
      const text = [
        `${params.team} ${location}record${params.season ? ` (${params.season})` : ""}${params.competition ? ` — ${params.competition}` : ""}:`,
        `  Matches: ${stats.matches}`,
        `  Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}`,
        `  Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst}`,
        `  Goal Difference: ${stats.goalsFor - stats.goalsAgainst}`,
        `  Points: ${stats.points}`,
        `  Win rate: ${winRate}%`,
      ].join("\n");

      return { content: [{ type: "text", text }] };
    }
  );

  server.tool(
    "search_players",
    "Search FIFA player database by name, nationality, club, position, or rating",
    {
      name: z.string().optional().describe("Player name (partial match)"),
      nationality: z.string().optional().describe("Player nationality"),
      club: z.string().optional().describe("Club name"),
      position: z.string().optional().describe("Playing position (e.g. ST, GK, CB)"),
      min_overall: z.number().optional().describe("Minimum overall rating"),
      max_overall: z.number().optional().describe("Maximum overall rating"),
      limit: z.number().optional().describe("Max results (default 50)"),
    },
    async (params) => {
      const players = data.searchPlayers({
        name: params.name,
        nationality: params.nationality,
        club: params.club,
        position: params.position,
        minOverall: params.min_overall,
        maxOverall: params.max_overall,
        limit: params.limit,
      });

      if (players.length === 0) {
        return { content: [{ type: "text", text: "No players found for the given criteria." }] };
      }

      const lines = players.map(
        (p, i) =>
          `${i + 1}. ${p.name} — Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club}, Nationality: ${p.nationality}, Age: ${p.age}`
      );

      return {
        content: [{ type: "text", text: `Found ${players.length} players:\n\n${lines.join("\n")}` }],
      };
    }
  );

  server.tool(
    "competition_standings",
    "Calculate league standings for a given season and competition",
    {
      season: z.number().describe("Season year"),
      competition: z.string().optional().describe("Competition name (default: Brasileirão)"),
    },
    async (params) => {
      const standings = data.competitionStandings(params.season, params.competition);

      if (standings.length === 0) {
        return {
          content: [{ type: "text", text: `No standings data for season ${params.season}.` }],
        };
      }

      const lines = standings.map(
        (s, i) =>
          `${String(i + 1).padStart(2)}. ${s.team.padEnd(25)} ${String(s.points).padStart(3)} pts  ${s.wins}W ${s.draws}D ${s.losses}L  ${s.goalsFor}:${s.goalsAgainst} (${s.goalDifference >= 0 ? "+" : ""}${s.goalDifference})`
      );

      return {
        content: [
          {
            type: "text",
            text: `${params.competition || "Brasileirão"} ${params.season} Standings:\n\n${lines.join("\n")}`,
          },
        ],
      };
    }
  );

  server.tool(
    "statistical_analysis",
    "Get aggregate statistics: average goals, home/away win rates, biggest wins",
    {
      analysis_type: z
        .enum(["averages", "biggest_wins"])
        .describe("Type of analysis"),
      competition: z.string().optional().describe("Competition name filter"),
      season: z.number().optional().describe("Season year filter"),
      limit: z.number().optional().describe("Max results for biggest_wins (default 20)"),
    },
    async (params) => {
      if (params.analysis_type === "averages") {
        const stats = data.averageGoals({
          competition: params.competition,
          season: params.season,
        });
        const text = [
          `Statistical averages${params.competition ? ` — ${params.competition}` : ""}${params.season ? ` (${params.season})` : ""}:`,
          `  Total matches: ${stats.totalMatches}`,
          `  Total goals: ${stats.totalGoals}`,
          `  Average goals per match: ${stats.avgGoalsPerMatch}`,
          `  Home win rate: ${stats.homeWinRate}%`,
          `  Away win rate: ${stats.awayWinRate}%`,
          `  Draw rate: ${stats.drawRate}%`,
        ].join("\n");
        return { content: [{ type: "text", text }] };
      }

      const matches = data.biggestWins({
        competition: params.competition,
        limit: params.limit,
      });

      const lines = matches.map(
        (m, i) =>
          `${i + 1}. ${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition}, diff: ${Math.abs(m.homeGoals - m.awayGoals)})`
      );

      return {
        content: [{ type: "text", text: `Biggest wins:\n\n${lines.join("\n")}` }],
      };
    }
  );

  return server;
}
