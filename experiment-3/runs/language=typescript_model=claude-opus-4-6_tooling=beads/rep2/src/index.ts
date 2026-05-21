import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import {
  searchMatches,
  getTeamStats,
  getHeadToHead,
  getStandings,
  searchPlayers,
  getBiggestWins,
  getAverageGoals,
  getTopScoringTeams,
} from "./queries.js";
import { getDataStats } from "./data-loader.js";

const server = new McpServer({
  name: "brazilian-soccer",
  version: "1.0.0",
});

server.tool(
  "search_matches",
  "Search for soccer matches by team, competition, season, or date range",
  {
    team: z.string().optional().describe("Team name to search (home or away)"),
    home_team: z.string().optional().describe("Home team name"),
    away_team: z.string().optional().describe("Away team name"),
    competition: z
      .string()
      .optional()
      .describe("Competition name (Brasileirão, Copa do Brasil, Copa Libertadores)"),
    season: z.number().optional().describe("Season year"),
    date_from: z.string().optional().describe("Start date (YYYY-MM-DD)"),
    date_to: z.string().optional().describe("End date (YYYY-MM-DD)"),
    limit: z.number().optional().describe("Max results to return (default 50)"),
  },
  async (params) => {
    const results = searchMatches({
      team: params.team,
      homeTeam: params.home_team,
      awayTeam: params.away_team,
      competition: params.competition,
      season: params.season,
      dateFrom: params.date_from,
      dateTo: params.date_to,
      limit: params.limit,
    });
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            { count: results.length, matches: results },
            null,
            2
          ),
        },
      ],
    };
  }
);

server.tool(
  "team_stats",
  "Get statistics for a team: wins, losses, draws, goals, win rate",
  {
    team: z.string().describe("Team name"),
    competition: z.string().optional().describe("Filter by competition"),
    season: z.number().optional().describe("Filter by season year"),
    home_only: z.boolean().optional().describe("Only home matches"),
    away_only: z.boolean().optional().describe("Only away matches"),
  },
  async (params) => {
    const stats = getTeamStats(params.team, {
      competition: params.competition,
      season: params.season,
      homeOnly: params.home_only,
      awayOnly: params.away_only,
    });
    return {
      content: [{ type: "text" as const, text: JSON.stringify(stats, null, 2) }],
    };
  }
);

server.tool(
  "head_to_head",
  "Compare two teams head-to-head: wins, goals, recent matches",
  {
    team1: z.string().describe("First team name"),
    team2: z.string().describe("Second team name"),
    competition: z.string().optional().describe("Filter by competition"),
    season: z.number().optional().describe("Filter by season year"),
  },
  async (params) => {
    const h2h = getHeadToHead(params.team1, params.team2, {
      competition: params.competition,
      season: params.season,
    });
    return {
      content: [{ type: "text" as const, text: JSON.stringify(h2h, null, 2) }],
    };
  }
);

server.tool(
  "standings",
  "Get league standings for a given season, calculated from match results",
  {
    season: z.number().describe("Season year"),
    competition: z
      .string()
      .optional()
      .describe("Competition name (default: Brasileirão)"),
  },
  async (params) => {
    const table = getStandings(params.season, params.competition);
    const formatted = table.map((s, i) => ({
      position: i + 1,
      ...s,
    }));
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify({ season: params.season, standings: formatted }, null, 2),
        },
      ],
    };
  }
);

server.tool(
  "search_players",
  "Search FIFA player database by name, nationality, club, position, or rating",
  {
    name: z.string().optional().describe("Player name (partial match)"),
    nationality: z.string().optional().describe("Player nationality"),
    club: z.string().optional().describe("Club name (partial match)"),
    position: z.string().optional().describe("Position (e.g., ST, GK, CB, LW)"),
    min_overall: z.number().optional().describe("Minimum overall rating"),
    max_overall: z.number().optional().describe("Maximum overall rating"),
    limit: z.number().optional().describe("Max results (default 25)"),
  },
  async (params) => {
    const players = searchPlayers({
      name: params.name,
      nationality: params.nationality,
      club: params.club,
      position: params.position,
      minOverall: params.min_overall,
      maxOverall: params.max_overall,
      limit: params.limit,
    });
    const summary = players.map((p) => ({
      name: p.name,
      age: p.age,
      nationality: p.nationality,
      overall: p.overall,
      potential: p.potential,
      club: p.club,
      position: p.position,
      preferredFoot: p.preferredFoot,
      value: p.value,
    }));
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify({ count: players.length, players: summary }, null, 2),
        },
      ],
    };
  }
);

server.tool(
  "biggest_wins",
  "Find the biggest victories by goal difference",
  {
    competition: z.string().optional().describe("Filter by competition"),
    season: z.number().optional().describe("Filter by season"),
    limit: z.number().optional().describe("Max results (default 20)"),
  },
  async (params) => {
    const wins = getBiggestWins({
      competition: params.competition,
      season: params.season,
      limit: params.limit,
    });
    const formatted = wins.map((m) => ({
      date: m.datetime,
      match: `${m.homeTeam} ${m.homeGoal}-${m.awayGoal} ${m.awayTeam}`,
      goalDifference: m.goalDiff,
      competition: m.competition,
    }));
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify({ count: formatted.length, biggest_wins: formatted }, null, 2),
        },
      ],
    };
  }
);

server.tool(
  "statistics",
  "Get aggregate statistics: average goals, home/away win rates",
  {
    competition: z.string().optional().describe("Filter by competition"),
    season: z.number().optional().describe("Filter by season"),
  },
  async (params) => {
    const stats = getAverageGoals({
      competition: params.competition,
      season: params.season,
    });
    return {
      content: [{ type: "text" as const, text: JSON.stringify(stats, null, 2) }],
    };
  }
);

server.tool(
  "top_scoring_teams",
  "Get the teams that scored the most goals",
  {
    competition: z.string().optional().describe("Filter by competition"),
    season: z.number().optional().describe("Filter by season"),
    limit: z.number().optional().describe("Max results (default 20)"),
  },
  async (params) => {
    const teams = getTopScoringTeams({
      competition: params.competition,
      season: params.season,
      limit: params.limit,
    });
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify({ count: teams.length, teams }, null, 2),
        },
      ],
    };
  }
);

server.tool("data_info", "Get information about available datasets and record counts", {}, async () => {
  const stats = getDataStats();
  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(
          {
            datasets: {
              "Brasileirão Serie A (2012+)": stats.brasileirao,
              "Copa do Brasil": stats.cup,
              "Copa Libertadores": stats.libertadores,
              "Extended Match Stats": stats.extended,
              "Historical Brasileirão (2003-2019)": stats.historical,
              "FIFA Player Database": stats.players,
            },
            totalMatches: stats.totalMatches,
            totalPlayers: stats.players,
          },
          null,
          2
        ),
      },
    ],
  };
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
