/**
 * MCP server definition: registers the Brazilian-soccer query tools
 * against a McpServer instance. Transport wiring lives in index.ts so
 * tests can attach an in-memory transport instead of stdio.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  bestRecords,
  biggestWins,
  competitionStats,
  filterMatches,
  formatMatchLine,
  headToHead,
  searchPlayers,
  standings,
  teamCompetitions,
  teamStats,
} from "./queries.js";
import type { Dataset, Player } from "./types.js";

function text(s: string) {
  return { content: [{ type: "text" as const, text: s }] };
}

function pct(x: number): string {
  return `${(x * 100).toFixed(1)}%`;
}

function playerLine(p: Player): string {
  const club = p.club || "no club";
  return `${p.name} — Overall: ${p.overall}, Position: ${p.position || "?"}, Age: ${p.age ?? "?"}, Nationality: ${p.nationality}, Club: ${club}`;
}

export function createServer(ds: Dataset): McpServer {
  const server = new McpServer({
    name: "brazilian-soccer-mcp",
    version: "1.0.0",
  });

  server.tool(
    "search_matches",
    "Search matches by team, opponent, competition (Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores), season and/or date range. Team names are matched loosely: 'Flamengo' finds 'Flamengo-RJ'.",
    {
      team: z.string().optional().describe("Team name (either home or away)"),
      opponent: z.string().optional().describe("Opposing team name, to find fixtures between two teams"),
      competition: z.string().optional().describe("Competition, e.g. 'Brasileirão', 'Serie A', 'Copa do Brasil', 'Libertadores'"),
      season: z.number().int().optional().describe("Season year, e.g. 2019"),
      date_from: z.string().optional().describe("Earliest date, ISO format YYYY-MM-DD"),
      date_to: z.string().optional().describe("Latest date, ISO format YYYY-MM-DD"),
      limit: z.number().int().min(1).max(200).optional().describe("Max matches to return (default 20, most recent first)"),
    },
    async (args) => {
      const matches = filterMatches(ds, {
        team: args.team,
        opponent: args.opponent,
        competition: args.competition,
        season: args.season,
        dateFrom: args.date_from,
        dateTo: args.date_to,
      });
      if (matches.length === 0) return text("No matches found for those criteria.");
      const limit = args.limit ?? 20;
      const shown = matches.slice(-limit).reverse(); // most recent first
      const lines = shown.map(formatMatchLine);
      const more = matches.length - shown.length;
      const header = `Found ${matches.length} match(es)${more > 0 ? `, showing the ${shown.length} most recent` : ""}:`;
      return text([header, ...lines, more > 0 ? `... (${more} earlier matches omitted)` : ""].filter(Boolean).join("\n"));
    },
  );

  server.tool(
    "head_to_head",
    "Head-to-head record between two teams across all competitions in the dataset: wins, draws, goals, and the most recent meetings.",
    {
      team1: z.string().describe("First team name"),
      team2: z.string().describe("Second team name"),
      limit: z.number().int().min(1).max(100).optional().describe("How many recent meetings to list (default 10)"),
    },
    async (args) => {
      const h2h = headToHead(ds, args.team1, args.team2);
      if (h2h.matches.length === 0) {
        return text(`No matches found between "${args.team1}" and "${args.team2}".`);
      }
      const limit = args.limit ?? 10;
      const recent = h2h.matches.slice(-limit).reverse();
      const lines = [
        `${args.team1} vs ${args.team2} — ${h2h.matches.length} meetings in dataset`,
        `Head-to-head: ${args.team1} ${h2h.team1Wins} wins, ${args.team2} ${h2h.team2Wins} wins, ${h2h.draws} draws`,
        `Goals: ${args.team1} ${h2h.team1Goals}, ${args.team2} ${h2h.team2Goals}`,
        "",
        `Most recent meetings:`,
        ...recent.map(formatMatchLine),
      ];
      if (h2h.matches.length > recent.length) {
        lines.push(`... (${h2h.matches.length - recent.length} earlier matches omitted)`);
      }
      return text(lines.join("\n"));
    },
  );

  server.tool(
    "team_stats",
    "Win/draw/loss record, goals for/against and win rate for a team, optionally filtered by season, competition and venue (home/away).",
    {
      team: z.string().describe("Team name"),
      season: z.number().int().optional().describe("Season year, e.g. 2022"),
      competition: z.string().optional().describe("Competition filter"),
      venue: z.enum(["home", "away", "all"]).optional().describe("Only home matches, only away matches, or all (default)"),
    },
    async (args) => {
      const s = teamStats(ds, args.team, {
        season: args.season,
        competition: args.competition,
        venue: args.venue,
      });
      if (s.matches === 0) return text(`No matches found for "${args.team}" with those filters.`);
      const scope = [
        args.season ? `season ${args.season}` : "all seasons",
        args.competition ?? "all competitions",
        args.venue && args.venue !== "all" ? `${args.venue} matches only` : "home & away",
      ].join(", ");
      const lines = [
        `${args.team} record (${scope}):`,
        `- Matches: ${s.matches}`,
        `- Wins: ${s.wins}, Draws: ${s.draws}, Losses: ${s.losses}`,
        `- Goals For: ${s.goalsFor}, Goals Against: ${s.goalsAgainst} (diff ${s.goalsFor - s.goalsAgainst >= 0 ? "+" : ""}${s.goalsFor - s.goalsAgainst})`,
        `- Win rate: ${pct(s.winRate)}`,
        `- By competition: ${Object.entries(s.competitions)
          .map(([c, n]) => `${c}: ${n}`)
          .join("; ")}`,
        `- Seasons covered: ${s.seasons.length ? `${s.seasons[0]}–${s.seasons[s.seasons.length - 1]}` : "n/a"}`,
      ];
      return text(lines.join("\n"));
    },
  );

  server.tool(
    "league_standings",
    "League table for a season, computed from match results (3 points per win). Defaults to Brasileirão Série A.",
    {
      season: z.number().int().describe("Season year, e.g. 2019"),
      competition: z.string().optional().describe("League: 'Serie A' (default), 'Serie B' or 'Serie C'"),
    },
    async (args) => {
      const table = standings(ds, args.season, args.competition);
      if (table.length === 0) return text(`No league matches found for season ${args.season}.`);
      const comp = args.competition ?? "Brasileirão Série A";
      const lines = [
        `${args.season} ${comp} standings (computed from ${table.reduce((n, r) => n + r.played, 0) / 2} matches):`,
        "Pos Team                      P   W  D  L   GF  GA  GD  Pts",
        ...table.map(
          (r) =>
            `${String(r.position).padStart(2)}. ${r.team.padEnd(24).slice(0, 24)} ${String(r.played).padStart(3)} ${String(r.wins).padStart(3)} ${String(r.draws).padStart(2)} ${String(r.losses).padStart(2)} ${String(r.goalsFor).padStart(4)} ${String(r.goalsAgainst).padStart(3)} ${String(r.goalDifference).padStart(3)} ${String(r.points).padStart(4)}`,
        ),
        "",
        `Champion (by points): ${table[0].team} with ${table[0].points} points`,
        table.length >= 20
          ? `Bottom four (relegation zone): ${table.slice(-4).map((r) => r.team).join(", ")}`
          : "",
      ].filter(Boolean);
      return text(lines.join("\n"));
    },
  );

  server.tool(
    "search_players",
    "Search the FIFA player database by name, nationality, club, position and/or minimum overall rating.",
    {
      name: z.string().optional().describe("Player name (partial, accent-insensitive)"),
      nationality: z.string().optional().describe("e.g. 'Brazil'"),
      club: z.string().optional().describe("Club name (partial), e.g. 'Flamengo'"),
      position: z.string().optional().describe("Exact position code, e.g. ST, GK, CDM, LW"),
      min_overall: z.number().int().optional().describe("Minimum FIFA overall rating"),
      sort_by: z.enum(["overall", "potential", "age", "name"]).optional().describe("Sort order (default overall, descending)"),
      limit: z.number().int().min(1).max(100).optional().describe("Max players to return (default 15)"),
    },
    async (args) => {
      const players = searchPlayers(ds, {
        name: args.name,
        nationality: args.nationality,
        club: args.club,
        position: args.position,
        minOverall: args.min_overall,
        sortBy: args.sort_by,
        limit: args.limit ?? 15,
      });
      if (players.length === 0) return text("No players found for those criteria.");
      const lines = [
        `Found ${players.length} player(s):`,
        ...players.map((p, i) => `${i + 1}. ${playerLine(p)}`),
      ];
      return text(lines.join("\n"));
    },
  );

  server.tool(
    "player_profile",
    "Detailed profile for one player (best name match): ratings, physical attributes, value and top skills.",
    {
      name: z.string().describe("Player name, e.g. 'Gabriel Barbosa' or 'Neymar'"),
    },
    async (args) => {
      let found = searchPlayers(ds, { name: args.name, limit: 3 });
      let note = "";
      if (found.length === 0) {
        // Fall back to individual name tokens so "Gabriel Barbosa" still
        // surfaces the closest names when the exact form is absent.
        const tokens = args.name.split(/\s+/).filter((t) => t.length >= 3);
        const candidates = new Map<number, (typeof ds.players)[number]>();
        for (const tok of tokens) {
          for (const p of searchPlayers(ds, { name: tok, limit: 5 })) {
            candidates.set(p.id, p);
          }
        }
        found = [...candidates.values()].sort((a, b) => b.overall - a.overall).slice(0, 3);
        if (found.length === 0) return text(`No player matching "${args.name}" found.`);
        note = `No exact match for "${args.name}" in the FIFA dataset; showing the closest name match.\n\n`;
      }
      const p = found[0];
      const topSkills = Object.entries(p.skills)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ");
      const lines = [
        `${note}${p.name}`,
        `- Age: ${p.age ?? "?"}, Nationality: ${p.nationality}`,
        `- Club: ${p.club || "n/a"}, Position: ${p.position || "?"}, Jersey: ${p.jerseyNumber ?? "?"}`,
        `- Overall: ${p.overall}, Potential: ${p.potential ?? "?"}`,
        `- Height: ${p.height}, Weight: ${p.weight}, Preferred foot: ${p.preferredFoot}`,
        `- Market value: ${p.value}, Wage: ${p.wage}`,
        `- Top skills: ${topSkills}`,
      ];
      if (found.length > 1) {
        lines.push("", `Other matches: ${found.slice(1).map((q) => `${q.name} (${q.club || "no club"})`).join("; ")}`);
      }
      return text(lines.join("\n"));
    },
  );

  server.tool(
    "competition_stats",
    "Aggregate statistics for a competition (or the whole dataset): match count, total and average goals, home/away win rates.",
    {
      competition: z.string().optional().describe("Competition filter; omit for all competitions"),
      season: z.number().int().optional().describe("Season year filter"),
    },
    async (args) => {
      const s = competitionStats(ds, { competition: args.competition, season: args.season });
      if (s.matches === 0) return text("No matches found for those filters.");
      const lines = [
        `${s.competition}${s.season ? ` — season ${s.season}` : ""}:`,
        `- Matches: ${s.matches}`,
        `- Total goals: ${s.totalGoals}`,
        `- Average goals per match: ${s.avgGoalsPerMatch.toFixed(2)}`,
        `- Home wins: ${s.homeWins} (${pct(s.homeWinRate)}), Away wins: ${s.awayWins} (${pct(s.awayWins / s.matches)}), Draws: ${s.draws} (${pct(s.draws / s.matches)})`,
      ];
      return text(lines.join("\n"));
    },
  );

  server.tool(
    "biggest_wins",
    "The most lopsided results in the dataset, optionally filtered by competition and season.",
    {
      competition: z.string().optional(),
      season: z.number().int().optional(),
      limit: z.number().int().min(1).max(50).optional().describe("Default 10"),
    },
    async (args) => {
      const wins = biggestWins(ds, { competition: args.competition, season: args.season, limit: args.limit ?? 10 });
      if (wins.length === 0) return text("No matches found for those filters.");
      const lines = [
        "Biggest victories:",
        ...wins.map((m, i) => `${i + 1}. ${formatMatchLine(m)}`),
      ];
      return text(lines.join("\n"));
    },
  );

  server.tool(
    "best_records",
    "Rank teams by home or away win rate, optionally within a competition/season. Useful for 'which team has the best home/away record?'",
    {
      venue: z.enum(["home", "away"]).describe("Rank by home or away record"),
      competition: z.string().optional(),
      season: z.number().int().optional(),
      min_matches: z.number().int().optional().describe("Minimum matches to qualify (default 10)"),
      limit: z.number().int().min(1).max(50).optional().describe("Default 10"),
    },
    async (args) => {
      const rows = bestRecords(ds, {
        venue: args.venue,
        competition: args.competition,
        season: args.season,
        minMatches: args.min_matches,
        limit: args.limit ?? 10,
      });
      if (rows.length === 0) return text("No qualifying teams found (try lowering min_matches).");
      const lines = [
        `Best ${args.venue} records${args.season ? ` in ${args.season}` : ""}${args.competition ? ` (${args.competition})` : ""}:`,
        ...rows.map(
          (r, i) =>
            `${i + 1}. ${r.team} — ${r.wins}W ${r.draws}D ${r.losses}L in ${r.matches} matches (win rate ${pct(r.winRate)})`,
        ),
      ];
      return text(lines.join("\n"));
    },
  );

  server.tool(
    "team_competitions",
    "List every competition a team appears in within the dataset, with match counts and season ranges.",
    {
      team: z.string().describe("Team name"),
    },
    async (args) => {
      const rows = teamCompetitions(ds, args.team);
      if (rows.length === 0) return text(`No matches found for "${args.team}".`);
      const lines = [
        `${args.team} competitions in dataset:`,
        ...rows.map(
          (r) =>
            `- ${r.competition}: ${r.matches} matches (seasons ${r.seasons.length ? `${r.seasons[0]}–${r.seasons[r.seasons.length - 1]}` : "unknown"})`,
        ),
      ];
      return text(lines.join("\n"));
    },
  );

  server.tool(
    "data_summary",
    "Overview of the loaded datasets: files, row counts, match/player totals and covered competitions.",
    {},
    async () => {
      const compCounts = new Map<string, number>();
      for (const m of ds.matches) {
        compCounts.set(m.competition, (compCounts.get(m.competition) ?? 0) + 1);
      }
      const lines = [
        "Brazilian Soccer MCP dataset summary:",
        `- Unique matches loaded: ${ds.matches.length} (after merging ${ds.duplicatesMerged} cross-file duplicates)`,
        `- Players loaded: ${ds.players.length}`,
        "- Matches by competition:",
        ...[...compCounts.entries()].map(([c, n]) => `    ${c}: ${n}`),
        "- Source files:",
        ...Object.entries(ds.fileCounts).map(([f, n]) => `    ${f}: ${n} rows`),
      ];
      return text(lines.join("\n"));
    },
  );

  return server;
}
