#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { loadAllData } from "./data-loader.js";
import { searchMatches, getTeamStats, getHeadToHead, searchPlayers, getStandings, getStatistics, } from "./queries.js";
const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, "..", "data", "kaggle");
let dataStore;
function ensureData() {
    if (!dataStore) {
        dataStore = loadAllData(DATA_DIR);
    }
    return dataStore;
}
function formatMatch(m) {
    const extra = m.round ? ` (Round ${m.round})` : m.stage ? ` (${m.stage})` : "";
    return `${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} [${m.competition}${extra}]`;
}
const server = new McpServer({
    name: "brazilian-soccer",
    version: "1.0.0",
});
server.tool("search_matches", "Search for matches by team, competition, season, or date range. Returns match results with scores.", {
    team: z.string().optional().describe("Team name to search for (home or away)"),
    homeTeam: z.string().optional().describe("Home team name"),
    awayTeam: z.string().optional().describe("Away team name"),
    opponent: z.string().optional().describe("Opponent team (use with 'team' for head-to-head)"),
    competition: z.string().optional().describe("Competition name (e.g., 'Brasileirão', 'Copa do Brasil', 'Libertadores')"),
    season: z.number().optional().describe("Season year"),
    dateFrom: z.string().optional().describe("Start date (YYYY-MM-DD)"),
    dateTo: z.string().optional().describe("End date (YYYY-MM-DD)"),
    limit: z.number().optional().describe("Max results to return (default 50)"),
}, async (args) => {
    const data = ensureData();
    const matches = searchMatches(data, args);
    const lines = matches.map(formatMatch);
    const total = data.matches.filter((m) => {
        if (args.team) {
            const tl = args.team.toLowerCase();
            if (!m.homeTeam.toLowerCase().includes(tl) && !m.awayTeam.toLowerCase().includes(tl))
                return false;
        }
        return true;
    }).length;
    return {
        content: [
            {
                type: "text",
                text: `Found ${matches.length} matches (${total} total matching):\n\n${lines.join("\n")}`,
            },
        ],
    };
});
server.tool("team_statistics", "Get team statistics including wins, losses, draws, goals scored/conceded, and points.", {
    team: z.string().describe("Team name"),
    competition: z.string().optional().describe("Filter by competition"),
    season: z.number().optional().describe("Filter by season year"),
    homeOnly: z.boolean().optional().describe("Only home matches"),
    awayOnly: z.boolean().optional().describe("Only away matches"),
}, async (args) => {
    const data = ensureData();
    const stats = getTeamStats(data, args.team, args);
    const winRate = stats.matches > 0 ? Math.round((stats.wins / stats.matches) * 1000) / 10 : 0;
    const gd = stats.goalsFor - stats.goalsAgainst;
    const text = [
        `${stats.team} statistics:`,
        `  Matches: ${stats.matches}`,
        `  Record: ${stats.wins}W ${stats.draws}D ${stats.losses}L`,
        `  Points: ${stats.points}`,
        `  Goals For: ${stats.goalsFor}, Against: ${stats.goalsAgainst} (GD: ${gd >= 0 ? "+" : ""}${gd})`,
        `  Win Rate: ${winRate}%`,
    ].join("\n");
    return { content: [{ type: "text", text }] };
});
server.tool("head_to_head", "Compare two teams head-to-head with match history and aggregate statistics.", {
    team1: z.string().describe("First team name"),
    team2: z.string().describe("Second team name"),
    competition: z.string().optional().describe("Filter by competition"),
    season: z.number().optional().describe("Filter by season year"),
}, async (args) => {
    const data = ensureData();
    const h2h = getHeadToHead(data, args.team1, args.team2, args);
    const s1 = h2h.team1Stats;
    const s2 = h2h.team2Stats;
    const lines = [
        `Head-to-head: ${args.team1} vs ${args.team2}`,
        `Total matches: ${s1.matches}`,
        `${args.team1}: ${s1.wins} wins | ${args.team2}: ${s2.wins} wins | Draws: ${s1.draws}`,
        `Goals: ${args.team1} ${s1.goalsFor} - ${s2.goalsFor} ${args.team2}`,
        "",
        "Recent matches:",
        ...h2h.matches.slice(0, 20).map(formatMatch),
    ];
    return { content: [{ type: "text", text: lines.join("\n") }] };
});
server.tool("search_players", "Search FIFA player database by name, nationality, club, position, or rating.", {
    name: z.string().optional().describe("Player name to search"),
    nationality: z.string().optional().describe("Player nationality (e.g., 'Brazil')"),
    club: z.string().optional().describe("Club name"),
    position: z.string().optional().describe("Playing position (e.g., 'ST', 'GK', 'CB')"),
    minOverall: z.number().optional().describe("Minimum overall rating"),
    maxOverall: z.number().optional().describe("Maximum overall rating"),
    sortBy: z.string().optional().describe("Sort by field (default: 'overall')"),
    limit: z.number().optional().describe("Max results (default 25)"),
}, async (args) => {
    const data = ensureData();
    const players = searchPlayers(data, args);
    const lines = players.map((p, i) => `${i + 1}. ${p.name} - OVR: ${p.overall}, POT: ${p.potential}, Pos: ${p.position}, Club: ${p.club}, Nationality: ${p.nationality}${p.age ? `, Age: ${p.age}` : ""}`);
    return {
        content: [
            {
                type: "text",
                text: `Found ${players.length} players:\n\n${lines.join("\n")}`,
            },
        ],
    };
});
server.tool("competition_standings", "Get league standings for a specific season, calculated from match results.", {
    season: z.number().describe("Season year"),
    competition: z.string().optional().describe("Competition name (default: Brasileirão)"),
}, async (args) => {
    const data = ensureData();
    const standings = getStandings(data, args.season, args.competition);
    const lines = standings.map((s, i) => {
        const gd = s.goalsFor - s.goalsAgainst;
        return `${String(i + 1).padStart(2)}. ${s.team.padEnd(25)} ${String(s.points).padStart(3)} pts | ${s.wins}W ${s.draws}D ${s.losses}L | GF: ${s.goalsFor} GA: ${s.goalsAgainst} GD: ${gd >= 0 ? "+" : ""}${gd}`;
    });
    return {
        content: [
            {
                type: "text",
                text: `${args.competition ?? "Brasileirão"} ${args.season} Standings:\n\n${lines.join("\n")}`,
            },
        ],
    };
});
server.tool("statistics", "Get aggregate statistics: goals per match, home/away win rates, biggest wins, and more.", {
    competition: z.string().optional().describe("Filter by competition"),
    season: z.number().optional().describe("Filter by season"),
    team: z.string().optional().describe("Filter by team"),
}, async (args) => {
    const data = ensureData();
    const stats = getStatistics(data, args);
    const lines = [
        "Aggregate Statistics:",
        `  Total Matches: ${stats.totalMatches}`,
        `  Total Goals: ${stats.totalGoals}`,
        `  Avg Goals/Match: ${stats.avgGoalsPerMatch}`,
        `  Home Wins: ${stats.homeWins} (${stats.homeWinRate}%)`,
        `  Away Wins: ${stats.awayWins} (${stats.awayWinRate}%)`,
        `  Draws: ${stats.draws} (${stats.drawRate}%)`,
        "",
        "Biggest victories:",
        ...stats.biggestWins.map(formatMatch),
    ];
    return { content: [{ type: "text", text: lines.join("\n") }] };
});
async function main() {
    ensureData();
    const transport = new StdioServerTransport();
    await server.connect(transport);
}
main().catch(console.error);
export { server, ensureData };
//# sourceMappingURL=index.js.map