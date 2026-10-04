import { z } from "zod";
import { displayName, normalizeTeam } from "./data.js";
import { SoccerService, MatchFilter, normalizeCompetition, fmtMatches, fmtMatch, fmtRecord, fmtStandings, fmtPlayer, derbyName } from "./queries.js";

const filterShape = {
  competition: z.string().optional().describe("Brasileirão / Serie A, Copa do Brasil, Libertadores, Serie B, Serie C"),
  season: z.number().int().optional().describe("Season year, e.g. 2019"),
  dateFrom: z.string().optional().describe("Start date YYYY-MM-DD (inclusive)"),
  dateTo: z.string().optional().describe("End date YYYY-MM-DD (inclusive)"),
};

export interface ToolDef {
  description: string;
  shape: z.ZodRawShape;
  run: (svc: SoccerService, args: any) => string;
}

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

export const TOOLS: Record<string, ToolDef> = {
  search_matches: {
    description: "Find matches by team (home/away/either), opponent, competition, season, date range or stage (e.g. 'final', or Copa do Brasil round number). Results newest first, deduplicated across files.",
    shape: {
      team: z.string().optional(), opponent: z.string().optional(),
      venue: z.enum(["home", "away", "any"]).optional(),
      stage: z.string().optional().describe("Libertadores stage (final, semifinals, ...) or cup round number"),
      limit: z.number().int().optional(), ...filterShape,
    },
    run: (svc, a) => {
      const ms = svc.filterMatches(a as MatchFilter);
      const parts = [a.team, a.opponent && `vs ${a.opponent}`, a.competition, a.season, a.stage].filter(Boolean).join(" ");
      return `Matches${parts ? ` (${parts})` : ""}: ${ms.length} found\n${fmtMatches(ms, a.limit ?? 25)}`;
    },
  },

  last_match: {
    description: "Most recent match between two teams (or most recent match of one team).",
    shape: { team: z.string(), opponent: z.string().optional() },
    run: (svc, a) => {
      const m = svc.filterMatches({ team: a.team, opponent: a.opponent })[0];
      return m ? `Most recent match in dataset:\n${fmtMatch(m)}\nScore: ${m.homeGoals}-${m.awayGoals}` : "No matches found.";
    },
  },

  head_to_head: {
    description: "Head-to-head record between two teams with match list.",
    shape: { teamA: z.string(), teamB: z.string(), limit: z.number().int().optional(), ...filterShape },
    run: (svc, a) => {
      const h = svc.headToHead(a.teamA, a.teamB, a);
      const na = displayName(normalizeTeam(a.teamA)), nb = displayName(normalizeTeam(a.teamB));
      const derby = derbyName(normalizeTeam(a.teamA), normalizeTeam(a.teamB));
      return `${na} vs ${nb}${derby ? ` (${derby})` : ""}:\n${fmtMatches(h.matches, a.limit ?? 20)}\n\n` +
        `Head-to-head in dataset (${h.matches.length} matches): ${na} ${h.aWins} wins, ${nb} ${h.bWins} wins, ${h.draws} draws\n` +
        `Goals: ${na} ${h.aGoals}, ${nb} ${h.bGoals}`;
    },
  },

  team_record: {
    description: "Win/draw/loss record, goals for/against for a team, optionally filtered by venue, competition, season, dates.",
    shape: { team: z.string(), venue: z.enum(["home", "away", "any"]).optional(), ...filterShape },
    run: (svc, a) => {
      const r = svc.teamRecord(a.team, a);
      const ctx = [a.venue && a.venue !== "any" ? `${a.venue} record` : "record", [a.season, normalizeCompetition(a.competition)].filter(Boolean).join(" ")].filter(Boolean);
      return fmtRecord(`${r.team} ${ctx[0]}${ctx[1] ? ` (${ctx[1]})` : ""}`, r);
    },
  },

  standings: {
    description: "League table for a season calculated from match results (Brasileirão 2003-2023, Serie B/C from extended dataset). Also shows relegation zone.",
    shape: { season: z.number().int(), competition: z.string().optional(), limit: z.number().int().optional() },
    run: (svc, a) => {
      const comp = normalizeCompetition(a.competition) ?? "Brasileirão";
      const rows = svc.standings(a.season, comp);
      if (!rows.length) return `No ${comp} data for ${a.season}.`;
      let out = fmtStandings(`${a.season} ${comp} Final Standings (calculated from matches):`, rows, a.limit ?? 40);
      if (comp === "Brasileirão" && rows.length >= 20) out += `\n\nRelegated (bottom 4): ${rows.slice(-4).map((r) => r.team).join(", ")}`;
      return out;
    },
  },

  top_scoring_teams: {
    description: "Teams ranked by goals scored in a competition/season.",
    shape: { limit: z.number().int().optional(), ...filterShape },
    run: (svc, a) => {
      const comp = normalizeCompetition(a.competition);
      const rows = a.season && (comp ?? "Brasileirão") === "Brasileirão" && !a.dateFrom && !a.dateTo && !a.team
        ? svc.standings(a.season) : [];
      const src = rows.length ? rows : svc.bestRecords("any", a, 1, 1000);
      const sorted = [...src].sort((x, y) => y.gf - x.gf).slice(0, a.limit ?? 10);
      return `Top scoring teams${a.season ? ` ${a.season}` : ""}${comp ? ` ${comp}` : ""}:\n` +
        sorted.map((r, i) => `${i + 1}. ${r.team} - ${r.gf} goals in ${r.played} matches (${(r.gf / r.played).toFixed(2)}/match)`).join("\n");
    },
  },

  biggest_wins: {
    description: "Largest margin victories, optionally filtered by team/competition/season.",
    shape: { team: z.string().optional(), limit: z.number().int().optional(), ...filterShape },
    run: (svc, a) => {
      const ms = svc.biggestWins(a, a.limit ?? 10);
      return `Biggest victories:\n${ms.map((m, i) => `${i + 1}. ${fmtMatch(m)}`).join("\n")}`;
    },
  },

  match_statistics: {
    description: "Aggregate statistics: average goals per match, home/away win and draw rates.",
    shape: { team: z.string().optional(), ...filterShape },
    run: (svc, a) => {
      const s = svc.aggregateStats(a);
      const ctx = [a.team, normalizeCompetition(a.competition), a.season].filter(Boolean).join(" ") || "all competitions";
      return `Statistics (${ctx}):\n- Matches: ${s.matches}\n- Total goals: ${s.totalGoals}\n- Average goals per match: ${s.avgGoals.toFixed(2)}\n` +
        `- Home win rate: ${pct(s.homeWinRate)}\n- Away win rate: ${pct(s.awayWinRate)}\n- Draw rate: ${pct(s.drawRate)}`;
    },
  },

  best_records: {
    description: "Rank teams by win rate at home, away, or overall.",
    shape: { venue: z.enum(["home", "away", "any"]), minMatches: z.number().int().optional(), limit: z.number().int().optional(), ...filterShape },
    run: (svc, a) => {
      const rows = svc.bestRecords(a.venue, a, a.minMatches ?? 10, a.limit ?? 10);
      return `Best ${a.venue === "any" ? "overall" : a.venue} records${a.season ? ` ${a.season}` : ""}${a.competition ? ` ${normalizeCompetition(a.competition)}` : ""}:\n` +
        rows.map((r, i) => `${i + 1}. ${r.team} - ${pct(r.winRate)} win rate (${r.wins}W ${r.draws}D ${r.losses}L in ${r.played}, GF ${r.gf} GA ${r.ga})`).join("\n");
    },
  },

  team_competitions: {
    description: "Which competitions a team has played in, with match counts and seasons.",
    shape: { team: z.string() },
    run: (svc, a) => {
      const c = svc.teamCompetitions(a.team);
      if (!c.length) return `No matches found for ${a.team}.`;
      return `${displayName(normalizeTeam(a.team))} competitions in dataset:\n` +
        c.map((x) => `- ${x.competition}: ${x.matches} matches (seasons ${x.seasons[0]}-${x.seasons[x.seasons.length - 1]})`).join("\n");
    },
  },

  derbies: {
    description: "Traditional rivalry matches (Fla-Flu, Gre-Nal, Derby Paulista, ...), filtered by season/competition.",
    shape: { team: z.string().optional(), limit: z.number().int().optional(), ...filterShape },
    run: (svc, a) => {
      const ms = svc.derbies(a);
      return `Derbies: ${ms.length} found\n` + (ms.slice(0, a.limit ?? 30).map((m) => `- [${derbyName(m.homeKey, m.awayKey)}] ${fmtMatch(m)}`).join("\n") || "None");
    },
  },

  compare_seasons: {
    description: "Compare aggregate stats and champions between two or more Brasileirão seasons.",
    shape: { seasons: z.array(z.number().int()).min(1) },
    run: (svc, a) => a.seasons.map((s: number) => {
      const ms = svc.leagueMatches(s);
      const rows = svc.standings(s);
      const goals = ms.reduce((t, m) => t + m.homeGoals + m.awayGoals, 0);
      const hw = ms.filter((m) => m.homeGoals > m.awayGoals).length;
      return `${s} Brasileirão: ${ms.length} matches, ${goals} goals (${ms.length ? (goals / ms.length).toFixed(2) : 0}/match), home win rate ${pct(ms.length ? hw / ms.length : 0)}, champion ${rows[0]?.team ?? "n/a"} (${rows[0]?.points ?? 0} pts)`;
    }).join("\n"),
  },

  search_players: {
    description: "Search FIFA player database by name, nationality, club, position (e.g. ST or 'forward'), minimum rating, max age.",
    shape: {
      name: z.string().optional(), nationality: z.string().optional(), club: z.string().optional(), position: z.string().optional(),
      minOverall: z.number().int().optional(), maxAge: z.number().int().optional(),
      sortBy: z.enum(["overall", "potential", "age"]).optional(), limit: z.number().int().optional(),
    },
    run: (svc, a) => {
      const r = svc.searchPlayers(a);
      if (!r.total) return "No players found.";
      return `Players found: ${r.total}${r.total > r.players.length ? ` (showing top ${r.players.length})` : ""}\n` + r.players.map((p, i) => fmtPlayer(p, i)).join("\n");
    },
  },

  player_details: {
    description: "Full profile of a player by name, including skill ratings.",
    shape: { name: z.string() },
    run: (svc, a) => {
      const r = svc.searchPlayers({ name: a.name, limit: 3 });
      if (!r.total) return `No player named ${a.name} found.`;
      return r.players.map((p) => `${p.name}\n- Age: ${p.age}, Nationality: ${p.nationality}\n- Club: ${p.club || "Free agent"}, Position: ${p.position}, Jersey: ${p.jersey}\n` +
        `- Overall: ${p.overall}, Potential: ${p.potential}, Value: ${p.value}\n- Height: ${p.height}, Weight: ${p.weight}, Foot: ${p.preferredFoot}\n` +
        `- Skills: ${Object.entries(p.skills).map(([k, v]) => `${k} ${v}`).join(", ")}`).join("\n\n");
    },
  },

  players_by_club: {
    description: "Clubs with the most players of a given nationality (default Brazil), with average rating.",
    shape: { nationality: z.string().optional(), limit: z.number().int().optional() },
    run: (svc, a) => {
      const nat = a.nationality ?? "Brazil";
      return `${nat} players by club:\n` + svc.playersByClub(nat, a.limit ?? 15).map((c) => `- ${c.club}: ${c.count} players (avg rating: ${c.avgOverall.toFixed(0)})`).join("\n");
    },
  },

  team_profile: {
    description: "Cross-dataset team overview: overall match record, competitions, recent matches and FIFA players at the club.",
    shape: { team: z.string() },
    run: (svc, a) => {
      const r = svc.teamRecord(a.team);
      const comps = svc.teamCompetitions(a.team);
      const players = svc.searchPlayers({ club: a.team, limit: 10 });
      return [
        fmtRecord(`${r.team} overall record (all datasets)`, r),
        `Competitions: ${comps.map((c) => `${c.competition} (${c.matches})`).join(", ") || "none"}`,
        `Recent matches:\n${fmtMatches(r.matches, 5)}`,
        `FIFA players at club: ${players.total}${players.total ? "\n" + players.players.map((p, i) => fmtPlayer(p, i)).join("\n") : ""}`,
      ].join("\n\n");
    },
  },

  list_teams: {
    description: "List known teams (normalized names) matching a query, with match counts. Useful to resolve team name variations.",
    shape: { query: z.string().optional(), limit: z.number().int().optional() },
    run: (svc, a) => svc.listTeams(a.query).slice(0, a.limit ?? 30).map((t) => `- ${t.name} [${t.key}]: ${t.matches} matches`).join("\n") || "No teams found.",
  },

  dataset_info: {
    description: "Summary of loaded datasets and record counts.",
    shape: {},
    run: (svc) => "Loaded datasets:\n" + Object.entries(svc.ds.bySource).map(([f, n]) => `- ${f}: ${n} records`).join("\n"),
  },
};

export function runTool(svc: SoccerService, name: string, args: unknown): string {
  const t = TOOLS[name];
  if (!t) throw new Error(`Unknown tool ${name}`);
  return t.run(svc, z.object(t.shape).parse(args ?? {}));
}
