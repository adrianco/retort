/**
 * MCP tool definitions. Each tool has a zod input schema and a handler that
 * runs a query and renders a text answer. Handlers are plain functions so
 * they can be unit-tested without an MCP transport.
 */
import { z } from "zod";
import { COMPETITIONS, LEAGUES, type Competition } from "./data.js";
import {
  formatMatch,
  formatPlayerDetail,
  formatPlayerLine,
  formatRecord,
  formatStandingRow,
  formatTie,
  shortRecord,
} from "./format.js";
import { pct } from "./normalize.js";
import { parseCompetition, type RankingMetric, type SoccerQueries } from "./query.js";

const competitionHelp = `Competition: ${Object.entries(COMPETITIONS)
  .map(([k, v]) => `"${k}" (${v})`)
  .join(", ")}. Free text like "Brasileirão" or "Copa do Brasil" also works.`;

const matchFilterShape = {
  team: z.string().optional().describe('Team name, any spelling ("Flamengo", "Palmeiras-SP", "Sao Paulo")'),
  opponent: z.string().optional().describe("Second team: only matches between team and opponent"),
  venue: z.enum(["home", "away", "any"]).optional().describe("Restrict to the team's home or away matches"),
  competition: z.string().optional().describe(competitionHelp),
  season: z.number().int().optional().describe("Season year, e.g. 2019"),
  season_from: z.number().int().optional().describe("First season (inclusive)"),
  season_to: z.number().int().optional().describe("Last season (inclusive)"),
  date_from: z.string().optional().describe("Start date (YYYY-MM-DD or DD/MM/YYYY)"),
  date_to: z.string().optional().describe("End date (YYYY-MM-DD or DD/MM/YYYY)"),
  stage: z.string().optional().describe('Cup stage, e.g. "final", "semifinals", "round of 16", "group stage", "round 3"'),
  round: z.number().int().optional().describe("League round (rodada) or cup round number"),
};

type FilterArgs = {
  team?: string;
  opponent?: string;
  venue?: "home" | "away" | "any";
  competition?: string;
  season?: number;
  season_from?: number;
  season_to?: number;
  date_from?: string;
  date_to?: string;
  stage?: string;
  round?: number;
};

function toFilter(a: FilterArgs) {
  return {
    team: a.team,
    opponent: a.opponent,
    venue: a.venue,
    competition: a.competition,
    season: a.season,
    seasonFrom: a.season_from,
    seasonTo: a.season_to,
    dateFrom: a.date_from,
    dateTo: a.date_to,
    stage: a.stage,
    round: a.round,
  };
}

function describeScope(a: FilterArgs): string {
  const bits: string[] = [];
  if (a.competition) bits.push(COMPETITIONS[parseCompetition(a.competition)]);
  if (a.season !== undefined) bits.push(String(a.season));
  if (a.season_from !== undefined || a.season_to !== undefined) bits.push(`${a.season_from ?? "…"}-${a.season_to ?? "…"}`);
  if (a.date_from || a.date_to) bits.push(`${a.date_from ?? "…"} to ${a.date_to ?? "…"}`);
  if (a.stage) bits.push(a.stage);
  return bits.length ? bits.join(", ") : "all competitions in dataset";
}

export interface ToolDef {
  name: string;
  title: string;
  description: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  inputSchema: Record<string, z.ZodType<any>>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handler: (q: SoccerQueries, args: any) => string;
}

const RANKING_METRICS = [
  "points",
  "points_per_game",
  "win_rate",
  "home_win_rate",
  "away_win_rate",
  "goals_for",
  "goals_against",
  "goal_difference",
  "goals_per_game",
  "wins",
  "clean_sheets",
] as const;

const METRIC_LABEL: Record<RankingMetric, string> = {
  points: "Points",
  points_per_game: "Points per game",
  win_rate: "Win rate",
  home_win_rate: "Home win rate",
  away_win_rate: "Away win rate",
  goals_for: "Goals scored",
  goals_against: "Goals conceded",
  goal_difference: "Goal difference",
  goals_per_game: "Goals scored per game",
  wins: "Wins",
  clean_sheets: "Clean sheets",
};

export const TOOLS: ToolDef[] = [
  {
    name: "search_matches",
    title: "Search matches",
    description:
      "Find matches by team (home/away/either), opponent, competition, season, date range, cup stage or round. Returns the most recent matches first plus the team's W/D/L summary. Use order='asc' for oldest first, limit=1 for 'when did X last play Y'.",
    inputSchema: {
      ...matchFilterShape,
      limit: z.number().int().min(1).max(500).optional().describe("Max matches to list (default 20)"),
      order: z.enum(["asc", "desc"]).optional().describe("Sort by date (default desc = newest first)"),
      include_stats: z.boolean().optional().describe("Show shots/corners when available"),
    },
    handler: (q, a) => {
      const res = q.searchMatches(toFilter(a), { limit: a.limit ?? 20, order: a.order });
      const head = res.team
        ? res.opponent
          ? `${res.team} vs ${res.opponent}`
          : `${res.team}${a.venue && a.venue !== "any" ? ` (${a.venue} matches)` : ""}`
        : "Matches";
      const lines = [`${head} — ${describeScope(a)}: ${res.total} match(es) found`];
      if (!res.total) return lines.join("\n");
      for (const m of res.matches) lines.push(`- ${formatMatch(q, m, { stats: a.include_stats })}`);
      if (res.total > res.matches.length) lines.push(`- ... (${res.total - res.matches.length} more matches in dataset)`);
      if (res.summary && res.teamId) {
        lines.push("");
        if (res.opponent) {
          lines.push(
            `Head-to-head in dataset: ${res.team} ${res.summary.wins} wins, ${res.opponent} ${res.summary.losses} wins, ${res.summary.draws} draws (goals ${res.summary.goalsFor}-${res.summary.goalsAgainst})`,
          );
        } else lines.push(`${res.team} record in these matches: ${shortRecord(res.summary)}`);
      }
      return lines.join("\n");
    },
  },
  {
    name: "head_to_head",
    title: "Head-to-head",
    description:
      "Compare two teams head-to-head: wins for each side, draws, goals, breakdown by competition and the most recent meetings (includes derby name, e.g. Fla-Flu).",
    inputSchema: {
      team_a: z.string().describe("First team"),
      team_b: z.string().describe("Second team"),
      competition: matchFilterShape.competition,
      season_from: matchFilterShape.season_from,
      season_to: matchFilterShape.season_to,
      limit: z.number().int().min(0).max(200).optional().describe("Recent meetings to list (default 10)"),
    },
    handler: (q, a) => {
      const h = q.headToHead(
        a.team_a,
        a.team_b,
        { competition: a.competition, seasonFrom: a.season_from, seasonTo: a.season_to },
        a.limit ?? 10,
      );
      const derby = h.derby ? (/derby|cl[aá]ssico/i.test(h.derby) ? h.derby : `${h.derby} derby`) : "";
      const lines = [`${h.teamA} vs ${h.teamB}${derby ? ` (${derby})` : ""}:`];
      if (!h.total) {
        lines.push("No meetings found in the dataset.");
        return lines.join("\n");
      }
      for (const m of h.matches) lines.push(`- ${formatMatch(q, m)}`);
      if (h.total > h.matches.length) lines.push(`- ... (${h.total - h.matches.length} more matches in dataset)`);
      lines.push("");
      lines.push(`Head-to-head in dataset (${h.total} matches): ${h.teamA} ${h.winsA} wins, ${h.teamB} ${h.winsB} wins, ${h.draws} draws`);
      lines.push(`Goals: ${h.teamA} ${h.goalsA} - ${h.goalsB} ${h.teamB}`);
      for (const c of h.byCompetition) {
        lines.push(`- ${c.name}: ${c.record.played} matches, ${h.teamA} ${c.record.wins}W / ${c.record.draws}D / ${c.record.losses}L`);
      }
      if (h.lastMatch) lines.push(`Last meeting: ${formatMatch(q, h.lastMatch)}`);
      return lines.join("\n");
    },
  },
  {
    name: "team_record",
    title: "Team record",
    description:
      "Win/draw/loss record, goals for/against, points and win rate for a team, optionally filtered by competition, season, date range and venue (home/away). Includes per-competition breakdown and home vs away split.",
    inputSchema: {
      team: z.string().describe("Team name"),
      venue: matchFilterShape.venue,
      competition: matchFilterShape.competition,
      season: matchFilterShape.season,
      season_from: matchFilterShape.season_from,
      season_to: matchFilterShape.season_to,
      date_from: matchFilterShape.date_from,
      date_to: matchFilterShape.date_to,
    },
    handler: (q, a) => {
      const { team, ...rest } = a;
      const r = q.teamRecord(team, toFilter(rest));
      const venueLabel = r.venue === "home" ? "home record" : r.venue === "away" ? "away record" : "record";
      const lines = [`${r.team} ${venueLabel} (${describeScope(a)}):`, ...formatRecord(r.record)];
      if (!r.record.played) return lines.join("\n");
      if (r.venue === "any") {
        lines.push("", `Home: ${shortRecord(r.home)}`, `Away: ${shortRecord(r.away)}`);
      }
      if (r.byCompetition.length > 1 || !a.competition) {
        lines.push("", "By competition:");
        for (const c of r.byCompetition) {
          const seasons = c.seasons.length > 1 ? `${c.seasons[0]}-${c.seasons[c.seasons.length - 1]}` : String(c.seasons[0]);
          lines.push(`- ${c.name} (${seasons}): ${shortRecord(c.record)}`);
        }
      }
      if (r.biggestWin) lines.push("", `Biggest win: ${formatMatch(q, r.biggestWin)}`);
      if (r.worstDefeat) lines.push(`Heaviest defeat: ${formatMatch(q, r.worstDefeat)}`);
      return lines.join("\n");
    },
  },
  {
    name: "team_profile",
    title: "Team profile",
    description:
      "Overview of a club across ALL datasets: name variants, competitions and seasons played, overall record, derbies, and FIFA players linked to the club (cross-file query).",
    inputSchema: { team: z.string().describe("Team name") },
    handler: (q, a) => {
      const p = q.teamProfile(a.team);
      const t = p.teamInfo;
      const lines = [
        `${t.name}${t.state ? ` (${t.state.toUpperCase()})` : ""}`,
        `- Name variants in data: ${[...t.rawNames].slice(0, 12).join(", ")}`,
        `- Matches in dataset: ${p.record.played} (${p.firstMatch?.date} to ${p.lastMatch?.date})`,
        `- Overall: ${shortRecord(p.record)}`,
        "",
        "Competitions played:",
      ];
      for (const c of p.byCompetition) {
        lines.push(`- ${c.name}: seasons ${c.seasons.join(", ")} — ${shortRecord(c.record)}`);
      }
      if (p.rivals.length) lines.push("", `Derbies: ${p.rivals.map((r) => `${r.derby} (vs ${r.team})`).join("; ")}`);
      lines.push("");
      if (p.players.length) {
        const avg = p.players.reduce((s, x) => s + (x.overall ?? 0), 0) / p.players.length;
        lines.push(`FIFA 19 squad: ${p.players.length} players (avg overall ${avg.toFixed(1)}). Top players:`);
        p.players.slice(0, 5).forEach((x, i) => lines.push(formatPlayerLine(x, i)));
      } else lines.push("FIFA 19 squad: club not present in the FIFA player dataset.");
      return lines.join("\n");
    },
  },
  {
    name: "standings",
    title: "League standings",
    description:
      "League table for a Brasileirão season (Série A 2003-2023, Série B/C 2014-2023) calculated from match results: champion, Libertadores places and relegated teams. Answers 'who won the 2019 Brasileirão' and 'which teams were relegated in 2020'.",
    inputSchema: {
      season: z.number().int().describe("Season year"),
      competition: z.string().optional().describe('League: "serie-a" (default), "serie-b" or "serie-c"'),
      top: z.number().int().min(1).max(30).optional().describe("Only show the first N rows (default: full table)"),
    },
    handler: (q, a) => {
      const st = q.standings(a.competition ?? "serie-a", a.season);
      const rows = a.top ? st.rows.slice(0, a.top) : st.rows;
      const lines = [`${a.season} ${COMPETITIONS[st.competition]} Final Standings (calculated from ${st.matches} matches):`];
      const n = st.rows.length;
      for (const r of rows) {
        let note = "";
        if (r.position === 1) note = " - Champion";
        else if (st.competition === "serie-a" && r.position > n - 4) note = " - Relegated";
        else if (st.competition === "serie-b" && r.position <= 4) note = " - Promoted";
        lines.push(formatStandingRow(r) + note);
      }
      if (st.competition === "serie-a") {
        lines.push("", `Relegated (bottom 4): ${st.rows.slice(-4).map((r) => r.team).join(", ")}`);
      }
      if (!st.complete && st.competition !== "serie-c") lines.push("Note: some matches for this season are missing from the source data, so the table may be incomplete.");
      if (st.competition === "serie-c") lines.push("Note: Série C uses a group + playoff format; this is an aggregate table of all matches.");
      return lines.join("\n");
    },
  },
  {
    name: "cup_bracket",
    title: "Cup bracket",
    description:
      "Knockout bracket for Copa Libertadores (2013-2022) or Copa do Brasil (2012-2023) season: each tie with legs, aggregate score and who advanced.",
    inputSchema: {
      competition: z.string().describe('"libertadores" or "copa-do-brasil"'),
      season: z.number().int().describe("Season year"),
      include_group_stage: z.boolean().optional().describe("Also list Libertadores group stage matches"),
    },
    handler: (q, a) => {
      const b = q.bracket(a.competition, a.season, a.include_group_stage);
      const lines = [`${a.season} ${COMPETITIONS[b.competition]} bracket:`];
      for (const s of b.stages) {
        lines.push("", `${s.stage.toUpperCase()} (${s.ties.length} ties)`);
        for (const t of s.ties) lines.push(`- ${formatTie(q, t)}`);
      }
      const final = b.stages.find((s) => s.stage === "final")?.ties[0];
      if (final?.winnerId) lines.push("", `Champion: ${q.teamName(final.winnerId)}`);
      return lines.join("\n");
    },
  },
  {
    name: "cup_finals",
    title: "Cup finals",
    description: "List all finals in the dataset for Copa do Brasil or Copa Libertadores, with scores and winners.",
    inputSchema: { competition: z.string().describe('"copa-do-brasil" or "libertadores"') },
    handler: (q, a) => {
      const f = q.finals(a.competition);
      const lines = [`${COMPETITIONS[f.competition]} finals in dataset (${f.finals.length}):`];
      for (const { season, tie } of f.finals) lines.push(`- ${season}: ${formatTie(q, tie)}`);
      return lines.join("\n");
    },
  },
  {
    name: "match_statistics",
    title: "Match statistics",
    description:
      "Aggregate statistics over a set of matches: average goals per match, home/away win and draw rates, most common scorelines, average shots/corners (where available) and the highest-scoring match. Filter by competition, season, team, etc.",
    inputSchema: { ...matchFilterShape },
    handler: (q, a) => {
      const s = q.matchStats(toFilter(a));
      const who = a.team ? `${q.resolveTeam(a.team).name} matches, ` : "";
      const lines = [`Statistics (${who}${describeScope(a)}):`, `- Matches: ${s.matches}`];
      if (!s.matches) return lines.join("\n");
      lines.push(
        `- Total goals: ${s.goals}`,
        `- Average goals per match: ${s.avgGoals.toFixed(2)}`,
        `- Home win rate: ${pct(s.homeWins, s.matches)} (${s.homeWins})`,
        `- Draw rate: ${pct(s.draws, s.matches)} (${s.draws})`,
        `- Away win rate: ${pct(s.awayWins, s.matches)} (${s.awayWins})`,
        `- Most common scorelines: ${s.commonScorelines.map(([sl, n]) => `${sl} (${n})`).join(", ")}`,
      );
      if (s.avgShots !== undefined) lines.push(`- Average shots per match: ${s.avgShots.toFixed(1)}`);
      if (s.avgCorners !== undefined) lines.push(`- Average corners per match: ${s.avgCorners.toFixed(1)}`);
      if (s.highestScoring) lines.push(`- Highest-scoring match: ${formatMatch(q, s.highestScoring)}`);
      if (s.seasons.length) lines.push(`- Seasons covered: ${s.seasons[0]}-${s.seasons[s.seasons.length - 1]}`);
      return lines.join("\n");
    },
  },
  {
    name: "biggest_wins",
    title: "Biggest wins",
    description: "Largest victories by goal margin, optionally filtered by competition, season or team (team = wins by that team).",
    inputSchema: {
      ...matchFilterShape,
      limit: z.number().int().min(1).max(100).optional().describe("Number of matches (default 10)"),
    },
    handler: (q, a) => {
      const ms = q.biggestWins(toFilter(a), a.limit ?? 10);
      const who = a.team ? ` by ${q.resolveTeam(a.team).name}` : "";
      const lines = [`Biggest victories${who} (${describeScope(a)}):`];
      ms.forEach((m, i) => lines.push(`${i + 1}. ${formatMatch(q, m)}`));
      if (!ms.length) lines.push("No decisive matches found.");
      return lines.join("\n");
    },
  },
  {
    name: "team_rankings",
    title: "Team rankings",
    description:
      "Rank teams by a metric over filtered matches: best home/away record (home_win_rate/away_win_rate), most goals scored (goals_for), fewest conceded (goals_against), points, win_rate, etc. Rate metrics apply a minimum-matches threshold.",
    inputSchema: {
      metric: z.enum(RANKING_METRICS).describe("Metric to rank by"),
      competition: matchFilterShape.competition,
      season: matchFilterShape.season,
      season_from: matchFilterShape.season_from,
      season_to: matchFilterShape.season_to,
      limit: z.number().int().min(1).max(100).optional().describe("Rows to show (default 10)"),
      min_matches: z.number().int().min(1).optional().describe("Minimum matches for a team to qualify"),
      ascending: z.boolean().optional().describe("Sort ascending (default: descending, except goals_against)"),
    },
    handler: (q, a) => {
      const r = q.teamRankings(
        a.metric,
        { competition: a.competition, season: a.season, seasonFrom: a.season_from, seasonTo: a.season_to },
        { limit: a.limit, minMatches: a.min_matches, ascending: a.ascending },
      );
      const metric = a.metric as RankingMetric;
      const lines = [
        `Teams ranked by ${METRIC_LABEL[metric].toLowerCase()} (${describeScope(a)}; min ${r.minMatches} matches, ${r.totalTeams} teams qualify):`,
      ];
      r.rows.forEach((row, i) => {
        const v = /rate/.test(metric) ? pct(row.record.wins, row.record.played) : Number.isInteger(row.value) ? String(row.value) : row.value.toFixed(2);
        lines.push(`${i + 1}. ${row.team} - ${METRIC_LABEL[metric]}: ${v} (${shortRecord(row.record)})`);
      });
      return lines.join("\n");
    },
  },
  {
    name: "compare_seasons",
    title: "Compare seasons",
    description: "Side-by-side season statistics for a competition: matches, goals per game, home win rate, champion and top-scoring team.",
    inputSchema: {
      seasons: z.array(z.number().int()).min(1).describe("Season years, e.g. [2018, 2019]"),
      competition: z.string().optional().describe('Competition (default "serie-a")'),
    },
    handler: (q, a) => {
      const comp = parseCompetition(a.competition ?? "serie-a");
      const rows = q.compareSeasons(comp, a.seasons);
      const lines = [`${COMPETITIONS[comp]} season comparison:`];
      for (const r of rows) {
        lines.push("", `${r.season}:`);
        if (!r.stats.matches) {
          lines.push("- No matches in dataset");
          continue;
        }
        lines.push(
          `- Matches: ${r.stats.matches}, Goals: ${r.stats.goals} (${r.stats.avgGoals.toFixed(2)} per match)`,
          `- Home wins ${pct(r.stats.homeWins, r.stats.matches)}, Draws ${pct(r.stats.draws, r.stats.matches)}, Away wins ${pct(r.stats.awayWins, r.stats.matches)}`,
        );
        if (r.champion) lines.push(`- Champion: ${r.champion.team} (${r.champion.points} pts, ${r.champion.wins}W ${r.champion.draws}D ${r.champion.losses}L)`);
        if (r.topScoringTeam) lines.push(`- Most goals: ${r.topScoringTeam.team} (${r.topScoringTeam.goals})`);
      }
      return lines.join("\n");
    },
  },
  {
    name: "derbies",
    title: "Derby matches",
    description:
      "Find traditional rivalry matches (Fla-Flu, Grenal, Derby Paulista, Clássico Mineiro, Ba-Vi, ...) filtered by season, competition or team.",
    inputSchema: {
      ...matchFilterShape,
      limit: z.number().int().min(1).max(500).optional().describe("Max matches (default 50)"),
    },
    handler: (q, a) => {
      const res = q.derbies(toFilter(a), a.limit ?? 50);
      const lines = [`Derby matches (${a.team ? `${res.team}, ` : ""}${describeScope(a)}): ${res.total} found`];
      for (const { match, derby } of res.matches) lines.push(`- [${derby}] ${formatMatch(q, match)}`);
      if (res.total > res.matches.length) lines.push(`- ... (${res.total - res.matches.length} more)`);
      return lines.join("\n");
    },
  },
  {
    name: "search_players",
    title: "Search players",
    description:
      "Search the FIFA 19 player database (18,207 players) by name, nationality (e.g. 'Brazil'), club, position (code like 'ST' or group: forward/midfielder/defender/goalkeeper), minimum rating or maximum age. Sorted by overall rating.",
    inputSchema: {
      name: z.string().optional().describe("Player name or part of it"),
      nationality: z.string().optional().describe('Nationality, e.g. "Brazil"'),
      club: z.string().optional().describe('Club name, e.g. "Santos", "Grêmio", "Real Madrid"'),
      position: z.string().optional().describe('Position code(s) or group: "ST", "GK", "forward", "defender"...'),
      min_overall: z.number().int().optional().describe("Minimum overall rating"),
      max_age: z.number().int().optional().describe("Maximum age"),
      brazilian_clubs_only: z.boolean().optional().describe("Only players at Brazilian clubs"),
      sort_by: z.enum(["overall", "potential", "age", "name"]).optional(),
      limit: z.number().int().min(1).max(200).optional().describe("Max players (default 25)"),
    },
    handler: (q, a) => {
      const res = q.searchPlayers({
        name: a.name,
        nationality: a.nationality,
        club: a.club,
        position: a.position,
        minOverall: a.min_overall,
        maxAge: a.max_age,
        brazilianClubsOnly: a.brazilian_clubs_only,
        sortBy: a.sort_by,
        limit: a.limit ?? 25,
      });
      const crit = Object.entries({ name: a.name, nationality: a.nationality, club: a.club, position: a.position, min_overall: a.min_overall, max_age: a.max_age })
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => `${k}=${v}`)
        .join(", ");
      const lines = [`Players (${crit || "all"}${a.brazilian_clubs_only ? ", Brazilian clubs only" : ""}): ${res.total} found`];
      res.players.forEach((p, i) => lines.push(formatPlayerLine(p, i)));
      if (res.total > res.players.length) lines.push(`... (${res.total - res.players.length} more)`);
      for (const n of res.notes) lines.push(`Note: ${n}`);
      return lines.join("\n");
    },
  },
  {
    name: "get_player",
    title: "Player details",
    description: "Detailed FIFA 19 profile for one player (rating, position, club, physical attributes, key skills). Suggests similar names when there is no exact match.",
    inputSchema: { name: z.string().describe("Player name") },
    handler: (q, a) => {
      const r = q.getPlayer(a.name);
      if (!r.player) {
        const lines = [`No player named "${a.name}" in the FIFA 19 dataset.`];
        if (r.suggestions.length) {
          lines.push("Similar names:");
          r.suggestions.forEach((p) => lines.push(formatPlayerLine(p)));
        }
        return lines.join("\n");
      }
      const lines = [formatPlayerDetail(r.player, q)];
      if (r.others.length) {
        lines.push("", "Other players matching that name:");
        r.others.forEach((p) => lines.push(formatPlayerLine(p)));
      }
      return lines.join("\n");
    },
  },
  {
    name: "club_player_summary",
    title: "Players per club",
    description:
      "Group FIFA players by club with player count and average rating, e.g. Brazilian players at Brazilian clubs, or where Brazilian players play worldwide. Also lists top nationalities when group_by='nationality'.",
    inputSchema: {
      nationality: z.string().optional().describe('Only players of this nationality (e.g. "Brazil")'),
      brazilian_clubs_only: z.boolean().optional().describe("Only Brazilian clubs"),
      group_by: z.enum(["club", "nationality"]).optional().describe("Default club"),
      limit: z.number().int().min(1).max(100).optional(),
    },
    handler: (q, a) => {
      if (a.group_by === "nationality") {
        const rows = q.nationalitySummary(a.limit ?? 15);
        return ["Players by nationality:", ...rows.map((r, i) => `${i + 1}. ${r.nationality}: ${r.players} players (avg rating ${r.avgOverall.toFixed(1)})`)].join("\n");
      }
      const s = q.clubSummary({ nationality: a.nationality, brazilianClubsOnly: a.brazilian_clubs_only, limit: a.limit ?? 20 });
      const lines = [
        `${a.nationality ? `${a.nationality} players` : "Players"}${a.brazilian_clubs_only ? " at Brazilian clubs" : ""}: ${s.totalPlayers} players across ${s.totalClubs} clubs`,
      ];
      for (const c of s.clubs) {
        lines.push(`- ${c.club}: ${c.players} players (avg rating: ${c.avgOverall.toFixed(1)}; best: ${c.best.name} ${c.best.overall})`);
      }
      return lines.join("\n");
    },
  },
  {
    name: "find_team",
    title: "Find team",
    description: "Resolve a team name to its canonical form and show matching teams, spellings and match counts. Useful for ambiguous names (e.g. 'Atlético', 'Botafogo').",
    inputSchema: { query: z.string().describe("Team name or fragment") },
    handler: (q, a) => {
      const hits = q.findTeams(a.query).slice(0, 15);
      if (!hits.length) return `No teams matching "${a.query}".`;
      const lines = [`Teams matching "${a.query}":`];
      for (const t of hits) {
        const ms = q.searchMatches({ team: t.id }, { limit: 0 });
        const comps = [...new Set(q.teamRecord(t.id).byCompetition.map((c) => c.name))].join(", ");
        lines.push(`- ${t.name} [id: ${t.id}] — ${ms.total} matches (${comps}); spellings: ${[...t.rawNames].slice(0, 8).join(" | ")}`);
      }
      return lines.join("\n");
    },
  },
  {
    name: "dataset_info",
    title: "Dataset info",
    description: "Describe the loaded datasets: files, rows, competitions and seasons covered, number of teams and players.",
    inputSchema: {},
    handler: (q) => {
      const ds = q.ds;
      const lines = ["Loaded data files:"];
      for (const s of ds.sources) lines.push(`- ${s.file}: ${s.rows} rows (${s.loaded} loaded${s.skipped ? `, ${s.skipped} skipped: missing score/date` : ""})`);
      lines.push("", `Unique matches after merging duplicates across files: ${ds.matches.length}`);
      for (const comp of Object.keys(COMPETITIONS) as Competition[]) {
        const seasons = q.seasons(comp);
        const n = ds.matches.filter((m) => m.competition === comp).length;
        lines.push(`- ${COMPETITIONS[comp]}: ${n} matches, seasons ${seasons[0]}-${seasons[seasons.length - 1]}${LEAGUES.includes(comp) ? " (league)" : " (knockout)"}`);
      }
      lines.push(
        `Teams: ${ds.teams.teams.size}`,
        `Players: ${ds.players.length} (FIFA 19), Brazilian players: ${ds.players.filter((p) => p.nationality === "Brazil").length}`,
        `Brazilian clubs in FIFA data: ${[...ds.brazilianClubs].sort().join(", ")}`,
        `Load time: ${ds.loadMs.toFixed(0)} ms`,
      );
      return lines.join("\n");
    },
  },
];

export function runTool(q: SoccerQueries, name: string, args: unknown = {}): string {
  const tool = TOOLS.find((t) => t.name === name);
  if (!tool) throw new Error(`Unknown tool ${name}`);
  const parsed = z.object(tool.inputSchema).parse(args ?? {});
  return tool.handler(q, parsed);
}
