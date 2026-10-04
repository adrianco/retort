#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { loadDataset } from "./data.js";
import * as q from "./queries.js";

const dataDir = process.env.SOCCER_DATA_DIR ?? join(dirname(fileURLToPath(import.meta.url)), "..", "data", "kaggle");
const ds = loadDataset(dataDir);

const score = (m: q.MatchView) =>
  `${m.date}: ${m.home} ${m.homeGoals}-${m.awayGoals} ${m.away} (${m.competition}${m.stage ? ` ${m.stage}` : m.round ? ` Round ${m.round}` : ""})`;
const recordText = (r: q.Record_) =>
  `- Matches: ${r.matches}\n- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}\n- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst}\n- Win rate: ${r.winRate}%`;

function reply(text: string, data: Record<string, unknown>) {
  return { content: [{ type: "text" as const, text }], structuredContent: data };
}

const server = new McpServer({ name: "brazilian-soccer", version: "1.0.0" });

const matchFilter = {
  team: z.string().optional().describe("Team name, any spelling (e.g. 'Flamengo', 'Palmeiras-SP', 'Sao Paulo')"),
  opponent: z.string().optional().describe("Opponent team, for head-to-head fixtures"),
  venue: z.enum(["home", "away", "any"]).optional(),
  competition: z.string().optional().describe("Brasileirão, Copa do Brasil, Libertadores, Serie B, Serie C"),
  season: z.number().int().optional(),
  from: z.string().optional().describe("Start date YYYY-MM-DD"),
  to: z.string().optional().describe("End date YYYY-MM-DD"),
  stage: z.string().optional().describe("Stage, e.g. 'final', 'semifinals', 'group stage'"),
};

server.registerTool("search_matches", {
  description: "Find matches by team, opponent, competition, season, date range or stage across all match datasets.",
  inputSchema: { ...matchFilter, limit: z.number().int().optional() },
}, async ({ limit = 20, ...f }) => {
  const all = q.filterMatches(ds, f);
  const shown = all.slice(0, limit).map(q.matchView);
  const h2h = f.team && f.opponent ? q.headToHead(ds, f.team, f.opponent, f) : undefined;
  let text = shown.length ? shown.map((m) => `- ${score(m)}`).join("\n") : "No matches found.";
  if (all.length > shown.length) text += `\n- ... (${all.length - shown.length} more matches in dataset)`;
  if (h2h) text = `${h2h.team} vs ${h2h.opponent}:\n${text}\n\nHead-to-head in dataset: ${h2h.team} ${h2h.teamWins} wins, ${h2h.opponent} ${h2h.opponentWins} wins, ${h2h.draws} draws`;
  return reply(text, { total: all.length, matches: shown, headToHead: h2h });
});

server.registerTool("last_meeting", {
  description: "Most recent match between two teams, with the score.",
  inputSchema: { team: z.string(), opponent: z.string() },
}, async ({ team, opponent }) => {
  const m = q.filterMatches(ds, { team, opponent })[0];
  const v = m ? q.matchView(m) : undefined;
  return reply(v ? `Last meeting: ${score(v)}` : "These teams have not met in the dataset.", { match: v });
});

server.registerTool("team_record", {
  description: "Win/draw/loss record and goals for a team, optionally by season, competition and home/away.",
  inputSchema: { team: z.string(), season: z.number().int().optional(), competition: z.string().optional(), venue: z.enum(["home", "away", "any"]).optional() },
}, async (f) => {
  const r = q.recordFor(f.team, q.filterMatches(ds, f));
  r.team = q.resolveTeamName(ds, f.team);
  const label = `${r.team} ${f.venue && f.venue !== "any" ? f.venue + " " : ""}record${f.season || f.competition ? ` (${[f.season, f.competition].filter(Boolean).join(" ")})` : ""}`;
  return reply(`${label}:\n${recordText(r)}`, { record: r });
});

server.registerTool("head_to_head", {
  description: "Head-to-head comparison of two teams across all competitions.",
  inputSchema: { team: z.string(), opponent: z.string(), competition: z.string().optional() },
}, async ({ team, opponent, competition }) => {
  const h = q.headToHead(ds, team, opponent, { competition });
  const text = `${h.team} vs ${h.opponent} head-to-head (${h.matches} matches):\n- ${h.team} wins: ${h.teamWins}\n- ${h.opponent} wins: ${h.opponentWins}\n- Draws: ${h.draws}\n- Goals: ${h.team} ${h.teamGoals}, ${h.opponent} ${h.opponentGoals}\nRecent:\n${h.recent.map((m) => `- ${score(m)}`).join("\n")}`;
  return reply(text, h);
});

server.registerTool("team_competitions", {
  description: "Which competitions (and seasons) a team appears in.",
  inputSchema: { team: z.string() },
}, async ({ team }) => {
  const r = q.teamCompetitions(ds, team);
  return reply(`${r.team} competitions:\n${r.competitions.map((c) => `- ${c.competition}: ${c.matches} matches, seasons ${c.seasons.join(", ")}`).join("\n")}`, r);
});

server.registerTool("team_profile", {
  description: "Combined profile of a club: match record, competitions, recent results and FIFA players.",
  inputSchema: { team: z.string() },
}, async ({ team }) => {
  const p = q.teamProfile(ds, team);
  const text = `${p.team} profile:\nRecord (all matches):\n${recordText(p.record)}\nCompetitions: ${p.competitions.map((c) => c.competition).join(", ") || "none"}\nPlayers (FIFA):\n${p.players.map((x) => `- ${x.name} - Overall: ${x.overall}, Position: ${x.position}`).join("\n") || "- none"}`;
  return reply(text, p);
});

server.registerTool("search_players", {
  description: "Search FIFA player data by name, nationality, club, position (code like ST or group like 'forward') and minimum rating. Sorted by overall rating.",
  inputSchema: { name: z.string().optional(), nationality: z.string().optional(), club: z.string().optional(), position: z.string().optional(), minOverall: z.number().int().optional(), limit: z.number().int().optional() },
}, async ({ limit = 20, ...f }) => {
  const all = q.searchPlayers(ds, f);
  const shown = all.slice(0, limit).map(q.playerView);
  const text = shown.length ? `Players (${all.length} found):\n${shown.map((p, i) => `${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club || "Free agent"}, Nationality: ${p.nationality}, Age: ${p.age}`).join("\n")}` : "No players found.";
  return reply(text, { total: all.length, players: shown });
});

server.registerTool("players_by_club", {
  description: "Count and average rating of players of a nationality, grouped by club.",
  inputSchema: { nationality: z.string(), limit: z.number().int().optional() },
}, async ({ nationality, limit }) => {
  const clubs = q.playersByClub(ds, nationality, limit);
  return reply(`${nationality} players by club:\n${clubs.map((c) => `- ${c.club}: ${c.players} players (avg rating: ${c.averageOverall})`).join("\n")}`, { clubs });
});

server.registerTool("standings", {
  description: "League table for a season calculated from match results (default Brasileirão), including champion and relegated teams.",
  inputSchema: { season: z.number().int(), competition: z.string().optional() },
}, async ({ season, competition }) => {
  const s = q.standings(ds, season, competition);
  const text = `${season} ${s.competition} Standings (calculated from matches):\n${s.table.map((r, i) => `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, GF ${r.goalsFor}, GA ${r.goalsAgainst})${i === 0 ? " - Champion" : ""}`).join("\n")}${s.relegated.length ? `\nRelegated: ${s.relegated.join(", ")}` : ""}`;
  return reply(text, s);
});

server.registerTool("libertadores_bracket", {
  description: "Copa Libertadores knockout bracket for a season.",
  inputSchema: { season: z.number().int() },
}, async ({ season }) => {
  const b = q.bracket(ds, season);
  return reply(`${season} Copa Libertadores knockout stage:\n${b.stages.map((s) => `${s.stage}:\n${s.matches.map((m) => `- ${score(m)}`).join("\n")}`).join("\n")}`, b);
});

server.registerTool("stats_overview", {
  description: "Average goals per match and home/away/draw rates for any match filter.",
  inputSchema: matchFilter,
}, async (f) => {
  const o = q.overview(ds, f);
  return reply(`Matches: ${o.matches}\nAverage goals per match: ${o.averageGoals}\nHome win rate: ${o.homeWinRate}%\nAway win rate: ${o.awayWinRate}%\nDraw rate: ${o.drawRate}%`, o);
});

server.registerTool("biggest_wins", {
  description: "Largest winning margins for any match filter.",
  inputSchema: { ...matchFilter, limit: z.number().int().optional() },
}, async ({ limit = 10, ...f }) => {
  const wins = q.biggestWins(ds, f, limit);
  return reply(`Biggest victories:\n${wins.map((m, i) => `${i + 1}. ${score(m)}`).join("\n")}`, { wins });
});

server.registerTool("best_records", {
  description: "Rank teams by win rate, at home, away or overall.",
  inputSchema: { venue: z.enum(["home", "away", "any"]), competition: z.string().optional(), season: z.number().int().optional(), minMatches: z.number().int().optional(), limit: z.number().int().optional() },
}, async ({ venue, minMatches, limit, ...f }) => {
  const ranking = q.bestRecords(ds, venue, f, minMatches, limit);
  return reply(`Best ${venue} records:\n${ranking.map((r, i) => `${i + 1}. ${r.team} - ${r.winRate}% (${r.wins}W ${r.draws}D ${r.losses}L in ${r.matches})`).join("\n")}`, { ranking });
});

server.registerTool("compare_seasons", {
  description: "Compare aggregate Brasileirão statistics between two seasons.",
  inputSchema: { first: z.number().int(), second: z.number().int(), competition: z.string().optional() },
}, async ({ first, second, competition = "Brasileirão" }) => {
  const seasons = [first, second].map((season) => ({ ...q.overview(ds, { season, competition }), season, champion: q.standings(ds, season, competition).champion }));
  return reply(seasons.map((s) => `${s.season}: ${s.matches} matches, ${s.averageGoals} goals/match, home win ${s.homeWinRate}%, champion ${s.champion ?? "n/a"}`).join("\n"), { seasons });
});

await server.connect(new StdioServerTransport());
