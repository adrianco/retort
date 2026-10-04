/**
 * MCP server definition: registers the Brazilian soccer tools on an McpServer.
 *
 * Every tool takes simple, LLM-friendly arguments (team names in any spelling,
 * competition names like "Brasileirão" or "Libertadores") and returns a
 * formatted text answer. Errors (unknown team, no data for a season, ...) are
 * returned as tool errors with an explanatory message rather than thrown.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { COMPETITION_NAMES, MATCH_SOURCES, type CompetitionId } from "./data.js";
import {
  formatMatch,
  formatMatchList,
  formatRecord,
  playerDetail,
  playerLine,
  pct,
  fixed,
  recordLine,
  standingLine,
  tieLine,
} from "./format.js";
import { SoccerKnowledgeBase, resolveCompetition, type MatchFilter, type Venue } from "./queries.js";
import { RIVALRIES } from "./teams.js";

type ToolResult = { content: { type: "text"; text: string }[]; isError?: boolean };

const ok = (text: string): ToolResult => ({ content: [{ type: "text", text }] });
const fail = (text: string): ToolResult => ({ content: [{ type: "text", text }], isError: true });

function guard<A>(fn: (args: A) => string): (args: A) => Promise<ToolResult> {
  return async (args: A) => {
    try {
      return ok(fn(args));
    } catch (e) {
      return fail(e instanceof Error ? e.message : String(e));
    }
  };
}

// Shared argument schemas -----------------------------------------------------

const competition = z
  .string()
  .optional()
  .describe('Competition: "Brasileirão"/"Serie A", "Serie B", "Serie C", "Copa do Brasil", "Libertadores". Omit for all.');
const season = z.number().int().optional().describe("Season year, e.g. 2019");
const seasonFrom = z.number().int().optional().describe("First season (inclusive)");
const seasonTo = z.number().int().optional().describe("Last season (inclusive)");
const venue = z.enum(["home", "away", "any"]).optional().describe("Restrict to home or away matches (default any)");
const limit = (d: number) => z.number().int().min(1).max(500).optional().describe(`Maximum rows to list (default ${d})`);

function describeFilter(f: MatchFilter & { competition?: string }): string {
  const bits: string[] = [];
  const comp = resolveCompetition(f.competition);
  if (comp) bits.push(COMPETITION_NAMES[comp]);
  if (f.season !== undefined) bits.push(String(f.season));
  if (f.seasonFrom !== undefined || f.seasonTo !== undefined) bits.push(`${f.seasonFrom ?? "…"}-${f.seasonTo ?? "…"}`);
  if (f.dateFrom || f.dateTo) bits.push(`${f.dateFrom ?? "…"} to ${f.dateTo ?? "…"}`);
  if (f.stage) bits.push(f.stage);
  if (f.round) bits.push(`round ${f.round}`);
  return bits.length ? bits.join(", ") : "all competitions";
}

function interpretation(kb: SoccerKnowledgeBase, query: string): string | undefined {
  const r = kb.resolveTeam(query);
  const chosen = r.teams[0];
  if (r.keys.length > 1) {
    const others = r.keys.slice(1, 6).map((k) => kb.teamName(k) + (kb.data.teams.get(k)?.state ? ` (${kb.data.teams.get(k)!.state})` : ""));
    return `Note: "${query}" interpreted as ${chosen.name}${chosen.state ? ` (${chosen.state})` : ""}; other possible teams: ${others.join(", ")}.`;
  }
  return undefined;
}

export function createServer(kb: SoccerKnowledgeBase): McpServer {
  const server = new McpServer(
    { name: "brazilian-soccer-mcp", version: "1.0.0" },
    {
      instructions:
        "Knowledge base of Brazilian soccer: Brasileirão Série A/B/C, Copa do Brasil and Copa Libertadores matches (2003-2023) " +
        "plus the FIFA 19 player database. Team names may be given in any spelling (accents, state suffixes, full names). " +
        "Statistics and standings are calculated from the match results in the provided datasets.",
    },
  );

  // ---------------------------------------------------------------- matches
  server.registerTool(
    "search_matches",
    {
      title: "Search matches",
      description:
        "Find matches by team (home/away/either), opponent, competition, season, date range, stage (Libertadores) or round. " +
        "Use stage='final' to find Copa do Brasil / Libertadores finals. Results are newest first.",
      inputSchema: {
        team: z.string().optional().describe("Team name, e.g. 'Flamengo', 'Palmeiras-SP', 'São Paulo'"),
        opponent: z.string().optional().describe("Opponent team name"),
        venue,
        competition,
        season,
        season_from: seasonFrom,
        season_to: seasonTo,
        date_from: z.string().optional().describe("Start date (YYYY-MM-DD, DD/MM/YYYY or YYYY)"),
        date_to: z.string().optional().describe("End date (YYYY-MM-DD, DD/MM/YYYY or YYYY)"),
        stage: z.string().optional().describe("Stage, e.g. 'final', 'semifinals', 'group stage'"),
        round: z.string().optional().describe("Round number"),
        include_stats: z.boolean().optional().describe("Include shots/corners/attacks when available"),
        limit: limit(25),
      },
    },
    guard((a) => {
      const f: MatchFilter = {
        team: a.team, opponent: a.opponent, venue: a.venue as Venue | undefined, competition: a.competition,
        season: a.season, seasonFrom: a.season_from, seasonTo: a.season_to, dateFrom: a.date_from, dateTo: a.date_to,
        stage: a.stage, round: a.round,
      };
      const matches = kb.findMatches(f);
      const lines: string[] = [];
      const who = [a.team && kb.team(a.team).name, a.opponent && kb.team(a.opponent).name].filter(Boolean).join(" vs ");
      lines.push(`${who ? who + " - " : ""}matches (${describeFilter(f)}${a.venue && a.venue !== "any" ? `, ${a.venue}` : ""}): ${matches.length} found`);
      for (const q of [a.team, a.opponent]) if (q) { const n = interpretation(kb, q); if (n) lines.push(n); }
      lines.push(...formatMatchList(kb, matches, a.limit ?? 25, { stats: a.include_stats }));
      if (a.team && matches.length) {
        const key = kb.team(a.team).key;
        let w = 0, d = 0, l = 0;
        for (const m of matches) {
          const gf = m.home === key ? m.homeGoals : m.awayGoals, ga = m.home === key ? m.awayGoals : m.homeGoals;
          if (gf > ga) w++; else if (gf === ga) d++; else l++;
        }
        lines.push("", `${kb.team(a.team).name} in these matches: ${w} wins, ${d} draws, ${l} losses`);
      }
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "head_to_head",
    {
      title: "Head-to-head",
      description:
        "Head-to-head record and match list between two teams across all competitions (or a filtered one). " +
        "Also answers 'when did X last play Y' (most recent match listed first).",
      inputSchema: {
        team_a: z.string().describe("First team"),
        team_b: z.string().describe("Second team"),
        competition,
        season_from: seasonFrom,
        season_to: seasonTo,
        limit: limit(15),
      },
    },
    guard((a) => {
      const h = kb.headToHead(a.team_a, a.team_b, { competition: a.competition, seasonFrom: a.season_from, seasonTo: a.season_to });
      const A = h.teamA.name, B = h.teamB.name;
      const lines = [`${A} vs ${B}${h.rivalry ? ` (${h.rivalry.name} derby)` : ""}:`];
      for (const q of [a.team_a, a.team_b]) { const n = interpretation(kb, q); if (n) lines.push(n); }
      if (!h.matches.length) {
        lines.push("No matches between these teams in the dataset.");
        return lines.join("\n");
      }
      lines.push(...formatMatchList(kb, h.matches, a.limit ?? 15));
      lines.push(
        "",
        `Head-to-head in dataset (${h.matches.length} matches): ${A} ${h.aWins} wins, ${B} ${h.bWins} wins, ${h.draws} draws`,
        `Goals: ${A} ${h.aGoals} - ${h.bGoals} ${B}`,
        `By competition: ${Object.entries(h.byCompetition).map(([c, n]) => `${COMPETITION_NAMES[c as CompetitionId]} ${n}`).join(", ")}`,
        `Most recent meeting: ${formatMatch(kb, h.matches[0])}`,
      );
      return lines.join("\n");
    }),
  );

  // ---------------------------------------------------------------- teams
  server.registerTool(
    "team_record",
    {
      title: "Team record",
      description: "Win/draw/loss record, goals for/against and win rate for a team, optionally by season, competition and home/away.",
      inputSchema: { team: z.string(), season, season_from: seasonFrom, season_to: seasonTo, competition, venue },
    },
    guard((a) => {
      const r = kb.teamRecord(a.team, { season: a.season, seasonFrom: a.season_from, seasonTo: a.season_to, competition: a.competition, venue: a.venue as Venue | undefined });
      const scope = describeFilter({ season: a.season, seasonFrom: a.season_from, seasonTo: a.season_to, competition: a.competition });
      const v = a.venue && a.venue !== "any" ? `${a.venue} ` : "";
      const total = a.venue === "home" ? r.home : a.venue === "away" ? r.away : r.overall;
      const lines = [`${r.team.name} ${v}record (${scope}):`];
      const n = interpretation(kb, a.team);
      if (n) lines.push(n);
      lines.push(...formatRecord(total));
      if (!a.venue || a.venue === "any") {
        lines.push(`- Home: ${recordLine(r.home)}`, `- Away: ${recordLine(r.away)}`);
      }
      const comps = Object.entries(r.byCompetition);
      if (comps.length > 1) {
        lines.push("", "By competition:");
        for (const [c, rec] of comps) lines.push(`- ${COMPETITION_NAMES[c as CompetitionId]}: ${recordLine(rec!)}`);
      }
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "team_profile",
    {
      title: "Team profile (cross-dataset)",
      description:
        "Everything known about a team: competitions and seasons it appears in across all match files, overall record, " +
        "calculated Brasileirão titles, last match, and FIFA-rated players at the club (player + match data combined).",
      inputSchema: { team: z.string() },
    },
    guard((a) => {
      const p = kb.teamProfile(a.team);
      const t = p.team;
      const lines = [`${t.name}${t.state ? ` (${t.state})` : ""}`];
      const n = interpretation(kb, a.team);
      if (n) lines.push(n);
      lines.push(`Name variants in data: ${[...t.rawNames].slice(0, 8).join("; ")}`, "", "Competitions in dataset:");
      for (const [c, e] of p.competitions) {
        const seasons = [...e.seasons].sort((x, y) => x - y);
        lines.push(`- ${COMPETITION_NAMES[c]}: ${e.matches} matches, seasons ${compressYears(seasons)} (files: ${[...e.sources].join(", ")})`);
      }
      lines.push("", `Overall record: ${recordLine(p.record.overall)}`, `Home: ${recordLine(p.record.home)}`, `Away: ${recordLine(p.record.away)}`);
      if (p.titles.length) lines.push(`Brasileirão titles (calculated from match data): ${p.titles.join(", ")}`);
      if (p.lastMatch) lines.push(`Most recent match in data: ${formatMatch(kb, p.lastMatch)}`);
      lines.push("");
      if (p.squad.length) {
        const avg = p.squad.reduce((s, x) => s + (x.overall ?? 0), 0) / p.squad.length;
        lines.push(`FIFA 19 squad: ${p.squad.length} players (avg overall ${fixed(avg, 1)}). Top players:`);
        p.squad.slice(0, 5).forEach((x, i) => lines.push(playerLine(x, i)));
      } else {
        lines.push("FIFA 19 squad: club not present in the FIFA player dataset (several Brazilian clubs are unlicensed in FIFA 19).");
      }
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "team_rankings",
    {
      title: "Team rankings",
      description:
        "Rank teams by a metric over matches: best home/away record (winRate), most goals scored (goalsFor), best defence " +
        "(goalsAgainst), points, pointsPerGame, goalDiff or wins. Filter by competition and season(s).",
      inputSchema: {
        metric: z.enum(["winRate", "points", "pointsPerGame", "goalsFor", "goalsAgainst", "goalDiff", "wins"]).optional(),
        venue,
        competition,
        season,
        season_from: seasonFrom,
        season_to: seasonTo,
        min_matches: z.number().int().optional().describe("Minimum matches for a team to qualify (default 19, or 1 for a single season)"),
        limit: limit(10),
      },
    },
    guard((a) => {
      const r = kb.teamRankings({
        metric: a.metric, venue: a.venue as Venue | undefined, competition: a.competition, season: a.season,
        seasonFrom: a.season_from, seasonTo: a.season_to, minMatches: a.min_matches, limit: a.limit,
      });
      const scope = describeFilter({ competition: a.competition, season: a.season, seasonFrom: a.season_from, seasonTo: a.season_to });
      const v = r.venue === "any" ? "all" : r.venue;
      const lines = [`Teams ranked by ${r.metric} (${v} matches, ${scope}, min ${r.minMatches} matches; ${r.matchesConsidered} matches considered):`];
      r.rows.forEach((x, i) =>
        lines.push(`${i + 1}. ${x.name} - win rate ${pct(x.winRate)}, ${x.matches} played (${x.wins}W ${x.draws}D ${x.losses}L), GF ${x.goalsFor} GA ${x.goalsAgainst}, ${x.points} pts`),
      );
      if (!r.rows.length) lines.push("No teams qualify - try lowering min_matches or widening the filters.");
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "find_team",
    {
      title: "Find team",
      description: "Resolve a team name (any spelling) to the teams in the dataset, showing the name variants used in each file.",
      inputSchema: { name: z.string() },
    },
    guard((a) => {
      const r = kb.resolveTeam(a.name);
      const lines = [`Teams matching "${a.name}":`];
      for (const t of r.teams.slice(0, 10)) lines.push(`- ${t.name}${t.state ? ` (${t.state})` : ""} [key: ${t.key}] - variants: ${[...t.rawNames].join("; ")}`);
      return lines.join("\n");
    }),
  );

  // ---------------------------------------------------------------- competitions
  server.registerTool(
    "league_standings",
    {
      title: "League standings",
      description:
        "Final league table for a Brasileirão (Série A/B/C) season, calculated from match results (3 pts per win). " +
        "Marks the champion and relegated clubs. Answers 'who won the 2019 Brasileirão' and 'who was relegated in 2020'.",
      inputSchema: { season: z.number().int(), competition, limit: limit(20) },
    },
    guard((a) => {
      const t = kb.standings(a.season, a.competition ?? "brasileirao");
      const lines = [`${a.season} ${COMPETITION_NAMES[t.competition]} Final Standings (calculated from ${t.matchesPlayed} matches; source: ${t.source}):`];
      if (!t.complete) lines.push(`Warning: dataset has only ${t.matchesPlayed} of ${t.rows.length * (t.rows.length - 1)} fixtures for this season; table may be incomplete.`);
      const rows = t.rows.slice(0, a.limit ?? t.rows.length);
      lines.push(...rows.map(standingLine));
      if (rows.length < t.rows.length) lines.push(`... (${t.rows.length - rows.length} more teams)`);
      const relegated = t.rows.filter((r) => r.note === "Relegated");
      if (relegated.length) lines.push("", `Relegated: ${relegated.map((r) => r.name).join(", ")}`);
      if (t.complete) lines.push(`Champion: ${t.rows[0].name}`);
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "cup_bracket",
    {
      title: "Cup bracket",
      description: "Knockout bracket for a Copa Libertadores or Copa do Brasil season: each tie with legs and aggregate score.",
      inputSchema: { season: z.number().int(), competition: z.string().optional().describe('"Libertadores" (default) or "Copa do Brasil"'), limit: limit(40) },
    },
    guard((a) => {
      const b = kb.bracket(a.season, a.competition ?? "libertadores");
      const lines = [`${a.season} ${COMPETITION_NAMES[b.competition]} knockout bracket (from match data):`];
      if (b.groupStageMatches) lines.push(`Group stage: ${b.groupStageMatches} matches`);
      for (const s of b.stages) {
        lines.push("", `${s.stage.replace(/\b\w/g, (c) => c.toUpperCase())}:`);
        for (const t of s.ties.slice(0, a.limit ?? 40)) lines.push(`- ${tieLine(kb, t)}`);
        if (s.ties.length > (a.limit ?? 40)) lines.push(`- ... (${s.ties.length - (a.limit ?? 40)} more ties)`);
      }
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "cup_finals",
    {
      title: "Cup finals",
      description: "List every final in the dataset for Copa do Brasil (default) or Copa Libertadores, with aggregate scores.",
      inputSchema: { competition: z.string().optional() },
    },
    guard((a) => {
      const comp = resolveCompetition(a.competition ?? "copa-do-brasil")!;
      const finals = kb.cupFinals(comp);
      const lines = [`${COMPETITION_NAMES[comp]} finals in dataset:`];
      for (const t of finals) lines.push(`- ${t.legs[0].season}: ${tieLine(kb, t)}`);
      if (!finals.length) lines.push("No finals found.");
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "list_competitions",
    {
      title: "Dataset overview",
      description: "List competitions, seasons and source files available, with row counts per CSV file.",
      inputSchema: {},
    },
    guard(() => {
      const lines = ["Competitions in dataset:"];
      for (const [c, e] of kb.listCompetitions()) {
        lines.push(`- ${COMPETITION_NAMES[c]}: ${e.matches} unique matches, seasons ${compressYears([...e.seasons].sort((x, y) => x - y))} (files: ${[...e.sources].join(", ")})`);
      }
      lines.push("", "Rows loaded per file:");
      for (const f of [...MATCH_SOURCES, "fifa_data.csv"]) {
        const dup = kb.data.stats.duplicatesPerSource[f];
        lines.push(`- ${f}: ${kb.data.stats.rowsPerSource[f] ?? 0}${dup ? ` (${dup} duplicates of fixtures in other files)` : ""}`);
      }
      lines.push(`Teams: ${kb.data.teams.size}, Players: ${kb.data.players.length}`);
      return lines.join("\n");
    }),
  );

  // ---------------------------------------------------------------- statistics
  server.registerTool(
    "biggest_wins",
    {
      title: "Biggest wins / highest-scoring matches",
      description: "Largest winning margins (or highest total goals) in the data, filterable by competition, season and team.",
      inputSchema: {
        competition, season, season_from: seasonFrom, season_to: seasonTo,
        team: z.string().optional(),
        sort: z.enum(["margin", "total_goals"]).optional().describe("margin (default) or total_goals"),
        limit: limit(10),
      },
    },
    guard((a) => {
      const f = { competition: a.competition, season: a.season, seasonFrom: a.season_from, seasonTo: a.season_to, team: a.team, limit: a.limit ?? 10 };
      const list = a.sort === "total_goals" ? kb.highestScoring(f) : kb.biggestWins(f);
      const title = a.sort === "total_goals" ? "Highest-scoring matches" : "Biggest victories";
      const lines = [`${title} (${describeFilter(f)}${a.team ? `, ${kb.team(a.team).name}` : ""}):`];
      list.forEach((m, i) => lines.push(`${i + 1}. ${formatMatch(kb, m)}`));
      const stats = kb.summarize(kb.findMatches(f));
      lines.push("", `Average goals per match: ${fixed(stats.avgGoals)}`, `Home win rate: ${pct(stats.homeWinRate)}`);
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "competition_stats",
    {
      title: "Competition statistics",
      description:
        "Aggregate statistics: matches, goals per match, home/draw/away win rates (and corners/shots where available), " +
        "optionally per season. Optional team filter for a team's matches.",
      inputSchema: { competition, season, season_from: seasonFrom, season_to: seasonTo, team: z.string().optional(), per_season: z.boolean().optional() },
    },
    guard((a) => {
      const f: MatchFilter = { competition: a.competition, season: a.season, seasonFrom: a.season_from, seasonTo: a.season_to, team: a.team };
      const s = kb.competitionStats(f);
      const o = s.overall;
      const lines = [
        `Statistics (${describeFilter(f)}${a.team ? `, ${kb.team(a.team).name} matches` : ""}):`,
        `- Matches: ${o.matches}`,
        `- Goals: ${o.goals} (average ${fixed(o.avgGoals)} per match; home ${fixed(o.avgHomeGoals)}, away ${fixed(o.avgAwayGoals)})`,
        `- Home wins: ${o.homeWins} (${pct(o.homeWinRate)}), Draws: ${o.draws} (${pct(o.drawRate)}), Away wins: ${o.awayWins} (${pct(o.awayWinRate)})`,
      ];
      if (s.extra) lines.push(`- Matches with detailed stats: ${s.extra.matchesWithStats} (avg corners ${fixed(s.extra.avgCorners, 1)}, avg shots ${fixed(s.extra.avgShots, 1)})`);
      if (a.per_season || (a.season === undefined && s.perSeason.length > 1 && s.perSeason.length <= 25)) {
        lines.push("", "Per season:");
        for (const p of s.perSeason) lines.push(`- ${p.season}: ${p.matches} matches, ${fixed(p.avgGoals)} goals/match, home win ${pct(p.homeWinRate)}, draws ${pct(p.drawRate)}, away win ${pct(p.awayWinRate)}`);
      }
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "compare_seasons",
    {
      title: "Compare seasons",
      description: "Compare two or more seasons of a league side by side: goals per match, home advantage, champion, best attack and defence.",
      inputSchema: { seasons: z.array(z.number().int()).min(1).max(25), competition },
    },
    guard((a) => {
      const rows = kb.compareSeasons(a.seasons, a.competition ?? "brasileirao");
      const comp = rows[0]?.competition ?? "brasileirao";
      const lines = [`Season comparison - ${COMPETITION_NAMES[comp]}:`];
      for (const r of rows) {
        if (!r.matches) {
          lines.push(`- ${r.season}: no matches in dataset`);
          continue;
        }
        lines.push(
          `- ${r.season}: ${r.matches} matches, ${r.goals} goals (${fixed(r.avgGoals)}/match), home win ${pct(r.homeWinRate)}, draws ${pct(r.drawRate)}, away win ${pct(r.awayWinRate)}` +
            (r.champion ? `; champion ${r.champion.name} (${r.champion.points} pts)` : "") +
            (r.topScoringTeam ? `; best attack ${r.topScoringTeam.name} (${r.topScoringTeam.goalsFor} GF)` : "") +
            (r.bestDefence ? `; best defence ${r.bestDefence.name} (${r.bestDefence.goalsAgainst} GA)` : ""),
        );
      }
      if (rows.length === 2 && rows[0].matches && rows[1].matches) {
        const d = rows[1].avgGoals - rows[0].avgGoals;
        lines.push("", `Goals per match changed by ${d >= 0 ? "+" : ""}${fixed(d)} from ${rows[0].season} to ${rows[1].season}.`);
      }
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "derby_matches",
    {
      title: "Derbies (clássicos)",
      description: `Matches between traditional rivals. Known rivalries: ${RIVALRIES.map((r) => r.name).join(", ")}.`,
      inputSchema: { season, rivalry: z.string().optional(), team: z.string().optional(), competition, limit: limit(10) },
    },
    guard((a) => {
      const res = kb.derbies({ season: a.season, rivalry: a.rivalry, team: a.team, competition: a.competition });
      const total = res.reduce((s, r) => s + r.matches.length, 0);
      const lines = [`Derby matches (${describeFilter({ season: a.season, competition: a.competition })}): ${total} matches`];
      for (const r of res) {
        const [x, y] = r.rivalry.teams;
        let xw = 0, yw = 0, d = 0;
        for (const m of r.matches) {
          const xg = m.home === x ? m.homeGoals : m.awayGoals, yg = m.home === x ? m.awayGoals : m.homeGoals;
          if (xg > yg) xw++; else if (yg > xg) yw++; else d++;
        }
        lines.push("", `${r.rivalry.name} (${kb.teamName(x)} vs ${kb.teamName(y)}) - ${r.matches.length} matches: ${kb.teamName(x)} ${xw} wins, ${kb.teamName(y)} ${yw} wins, ${d} draws`);
        lines.push(...formatMatchList(kb, r.matches, a.limit ?? 10));
      }
      if (!res.length) lines.push("No derby matches found for these filters.");
      return lines.join("\n");
    }),
  );

  // ---------------------------------------------------------------- players
  server.registerTool(
    "search_players",
    {
      title: "Search players",
      description:
        "Search the FIFA 19 player database by name, nationality (e.g. 'Brazil'/'Brazilian'), club, position " +
        "('forward', 'midfielder', 'defender', 'goalkeeper' or codes like ST, CB), minimum rating or age. Sorted by overall rating.",
      inputSchema: {
        name: z.string().optional(),
        nationality: z.string().optional(),
        club: z.string().optional(),
        position: z.string().optional(),
        min_overall: z.number().int().optional(),
        max_age: z.number().int().optional(),
        brazilian_clubs_only: z.boolean().optional().describe("Only players at Brazilian clubs"),
        sort_by: z.enum(["overall", "potential", "age", "name"]).optional(),
        limit: limit(20),
      },
    },
    guard((a) => {
      const r = kb.searchPlayers({
        name: a.name, nationality: a.nationality, club: a.club, position: a.position, minOverall: a.min_overall,
        maxAge: a.max_age, brazilianClubsOnly: a.brazilian_clubs_only, sortBy: a.sort_by, limit: a.limit ?? 20,
      });
      const crit = [a.name && `name "${a.name}"`, a.nationality && `nationality ${a.nationality}`, a.club && `club ${a.club}`, a.position && `position ${a.position}`,
        a.min_overall && `overall >= ${a.min_overall}`, a.max_age && `age <= ${a.max_age}`, a.brazilian_clubs_only && "at Brazilian clubs"].filter(Boolean).join(", ");
      const lines = [`Players (${crit || "all"}): ${r.total} found`];
      if (r.fuzzy) lines.push(`No exact match for "${a.name}"; closest name matches:`);
      if (!r.total && a.club) {
        lines.push(`No players for club "${a.club}" in the FIFA 19 dataset (Flamengo, Palmeiras, Corinthians, São Paulo, Vasco and some other Brazilian clubs are not licensed in FIFA 19).`);
      }
      r.players.forEach((p, i) => lines.push(playerLine(p, i)));
      if (r.total > r.players.length) lines.push(`... (${r.total - r.players.length} more)`);
      if (r.players.length) {
        const avg = r.players.reduce((s, p) => s + (p.overall ?? 0), 0) / r.players.length;
        lines.push(`Average overall of listed players: ${fixed(avg, 1)}`);
      }
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "get_player",
    {
      title: "Player details",
      description: "Detailed profile (club, position, ratings, physical data, top attributes) for a player by name or FIFA ID. 'Who is X?'",
      inputSchema: { name: z.string().optional(), id: z.number().int().optional() },
    },
    guard((a) => {
      if (!a.name && a.id === undefined) throw new Error("Provide a player name or id.");
      const found = kb.getPlayer(a.id ?? a.name!);
      if (!found.length) return `No player matching "${a.name ?? a.id}" in the FIFA 19 dataset.`;
      const exact = a.name ? kb.searchPlayers({ name: a.name, limit: 1 }) : undefined;
      const lines: string[] = [];
      if (exact?.fuzzy) lines.push(`"${a.name}" is not in the FIFA 19 dataset. Closest matches:`, ...found.map((p, i) => playerLine(p, i)));
      else {
        lines.push(playerDetail(found[0]));
        if (found.length > 1) lines.push("", "Other players with similar names:", ...found.slice(1).map((p) => playerLine(p)));
        const clubKey = found[0].clubKey;
        if (clubKey) {
          const rec = kb.teamRecord(clubKey, { competition: "brasileirao" });
          lines.push("", `${kb.teamName(clubKey)} in Brasileirão match data: ${recordLine(rec.overall)}`);
        }
      }
      return lines.join("\n");
    }),
  );

  server.registerTool(
    "players_by_club",
    {
      title: "Players grouped by club",
      description: "Count and average rating of players per club, e.g. Brazilian players at Brazilian clubs, or where Brazilian players play.",
      inputSchema: { nationality: z.string().optional(), brazilian_clubs_only: z.boolean().optional(), limit: limit(20) },
    },
    guard((a) => {
      const groups = kb.playersByClub({ nationality: a.nationality, brazilianClubsOnly: a.brazilian_clubs_only, limit: a.limit ?? 20 });
      const lines = [`${a.nationality ? `${a.nationality} players` : "Players"}${a.brazilian_clubs_only ? " at Brazilian clubs" : ""} by club:`];
      for (const g of groups) lines.push(`- ${g.club}: ${g.count} players (avg rating: ${fixed(g.avgOverall, 1)}; best: ${g.best.name} ${g.best.overall})`);
      return lines.join("\n");
    }),
  );

  return server;
}

function compressYears(years: number[]): string {
  const out: string[] = [];
  let start = years[0], prev = years[0];
  for (let i = 1; i <= years.length; i++) {
    const y = years[i];
    if (y === prev + 1) {
      prev = y;
      continue;
    }
    out.push(start === prev ? `${start}` : `${start}-${prev}`);
    start = prev = y;
  }
  return out.join(", ");
}

