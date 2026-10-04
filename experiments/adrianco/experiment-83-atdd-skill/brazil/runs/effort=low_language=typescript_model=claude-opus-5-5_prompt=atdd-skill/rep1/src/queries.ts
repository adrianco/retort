import { Dataset, Match, Player } from "./data.js";
import { DERBIES, displayName, stripAccents, teamKey } from "./teams.js";

export interface MatchFilter {
  team?: string; opponent?: string; venue?: "home" | "away" | "all"; season?: number; competition?: string;
  stage?: string; from?: string; to?: string; limit?: number;
}

const COMPETITIONS: Record<string, string> = {
  brasileirao: "Brasileirão", "serie a": "Brasileirão", "campeonato brasileiro": "Brasileirão", "serie b": "Serie B",
  "serie c": "Serie C", "copa do brasil": "Copa do Brasil", "brazilian cup": "Copa do Brasil", libertadores: "Libertadores",
  "copa libertadores": "Libertadores",
};
export function competitionName(input?: string): string | undefined {
  if (!input) return undefined;
  const k = stripAccents(input).toLowerCase().trim();
  return COMPETITIONS[k] ?? Object.entries(COMPETITIONS).find(([alias]) => k.includes(alias))?.[1] ?? input;
}

// Resolve user input to the set of canonical team keys it refers to.
export function resolveTeam(ds: Dataset, input: string): Set<string> {
  const key = teamKey(input);
  const all = new Set<string>();
  for (const m of ds.matches) { all.add(m.home); all.add(m.away); }
  if (all.has(key)) return new Set([key]);
  const partial = [...all].filter(k => k.includes(key) || key.includes(k));
  if (!partial.length) throw new Error(`No team found matching "${input}"`);
  return new Set(partial);
}

const fmtMatch = (m: Match) => {
  const ctx = [m.competition, m.season ? String(m.season) : "", m.round && m.competition !== "Copa do Brasil" ? `Round ${m.round}` : "", m.stage ?? ""]
    .filter(Boolean).join(" ");
  return `${m.date}: ${displayName(m.home)} ${m.homeGoals}-${m.awayGoals} ${displayName(m.away)} (${ctx})`;
};

export function filterMatches(ds: Dataset, f: MatchFilter, pool = ds.matches): Match[] {
  const teams = f.team ? resolveTeam(ds, f.team) : undefined;
  const opps = f.opponent ? resolveTeam(ds, f.opponent) : undefined;
  const comp = competitionName(f.competition);
  const stage = f.stage?.toLowerCase();
  return pool.filter(m => {
    if (f.season && m.season !== f.season) return false;
    if (comp && m.competition !== comp) return false;
    if (stage && !(m.stage ?? "").toLowerCase().includes(stage)) return false;
    if (f.from && m.date < f.from) return false;
    if (f.to && m.date > f.to) return false;
    if (teams) {
      const venue = f.venue ?? "all";
      const atHome = teams.has(m.home), away = teams.has(m.away);
      if (venue === "home" ? !atHome : venue === "away" ? !away : !(atHome || away)) return false;
      if (opps && !(atHome ? opps.has(m.away) : opps.has(m.home))) return false;
    } else if (opps && !(opps.has(m.home) || opps.has(m.away))) return false;
    return true;
  });
}

function headToHeadSummary(ds: Dataset, ms: Match[], team: string, opponent: string): string {
  const t = resolveTeam(ds, team);
  let w = 0, l = 0, d = 0;
  for (const m of ms) {
    const diff = t.has(m.home) ? m.homeGoals - m.awayGoals : m.awayGoals - m.homeGoals;
    diff > 0 ? w++ : diff < 0 ? l++ : d++;
  }
  const tn = displayName([...t][0]), on = displayName([...resolveTeam(ds, opponent)][0]);
  return `Head-to-head in dataset: ${tn} ${w} wins, ${on} ${l} wins, ${d} draws`;
}

export function searchMatches(ds: Dataset, f: MatchFilter): string {
  const ms = filterMatches(ds, f);
  const limit = f.limit ?? 50;
  const desc = [f.team && displayName([...resolveTeam(ds, f.team)][0]), f.opponent && `vs ${displayName([...resolveTeam(ds, f.opponent)][0])}`,
    competitionName(f.competition), f.stage, f.season && `season ${f.season}`, f.from && `from ${f.from}`, f.to && `to ${f.to}`].filter(Boolean).join(" ");
  const lines = [`Matches${desc ? ` (${desc})` : ""}: ${ms.length} found`];
  for (const m of ms.slice(0, limit)) lines.push(`- ${fmtMatch(m)}`);
  if (ms.length > limit) lines.push(`... (${ms.length - limit} more matches in dataset)`);
  if (f.team && f.opponent && ms.length) lines.push("", headToHeadSummary(ds, ms, f.team, f.opponent));
  return lines.join("\n");
}

export function lastMeeting(ds: Dataset, team: string, opponent: string): string {
  const m = filterMatches(ds, { team, opponent })[0];
  if (!m) return `No matches found between ${team} and ${opponent}.`;
  return `Most recent meeting:\n- ${fmtMatch(m)}\nScore: ${displayName(m.home)} ${m.homeGoals}-${m.awayGoals} ${displayName(m.away)}`;
}

export function headToHead(ds: Dataset, team: string, opponent: string): string {
  const ms = filterMatches(ds, { team, opponent });
  if (!ms.length) return `No matches found between ${team} and ${opponent}.`;
  const t = resolveTeam(ds, team);
  let gf = 0, ga = 0;
  for (const m of ms) { gf += t.has(m.home) ? m.homeGoals : m.awayGoals; ga += t.has(m.home) ? m.awayGoals : m.homeGoals; }
  const byComp = new Map<string, number>();
  for (const m of ms) byComp.set(m.competition, (byComp.get(m.competition) ?? 0) + 1);
  return [`${displayName([...t][0])} vs ${displayName([...resolveTeam(ds, opponent)][0])}: ${ms.length} matches`,
    headToHeadSummary(ds, ms, team, opponent),
    `Goals: ${displayName([...t][0])} ${gf} - ${ga}`,
    `By competition: ${[...byComp].map(([c, n]) => `${c} ${n}`).join(", ")}`,
    "Recent meetings:", ...ms.slice(0, 5).map(m => `- ${fmtMatch(m)}`)].join("\n");
}

interface Rec { team: string; played: number; w: number; d: number; l: number; gf: number; ga: number; pts: number }
function records(ms: Match[], venue: "home" | "away" | "all" = "all", only?: Set<string>): Map<string, Rec> {
  const map = new Map<string, Rec>();
  const add = (team: string, gf: number, ga: number) => {
    if (only && !only.has(team)) return;
    const r = map.get(team) ?? { team, played: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, pts: 0 };
    r.played++; r.gf += gf; r.ga += ga;
    if (gf > ga) { r.w++; r.pts += 3; } else if (gf === ga) { r.d++; r.pts++; } else r.l++;
    map.set(team, r);
  };
  for (const m of ms) {
    if (venue !== "away") add(m.home, m.homeGoals, m.awayGoals);
    if (venue !== "home") add(m.away, m.awayGoals, m.homeGoals);
  }
  return map;
}
const pct = (a: number, b: number) => (b ? ((100 * a) / b).toFixed(1) : "0.0") + "%";

export function teamRecord(ds: Dataset, team: string, opts: { season?: number; venue?: "home" | "away" | "all"; competition?: string }): string {
  const venue = opts.venue ?? "all";
  const comp = competitionName(opts.competition);
  const pool = comp === "Brasileirão" && opts.season && ds.seasonSources.has(opts.season) ? ds.league : ds.matches;
  const keys = resolveTeam(ds, team);
  const ms = filterMatches(ds, { team, venue, season: opts.season, competition: comp }, pool);
  const merged = [...records(ms, venue, keys).values()].reduce<Rec>((a, r) => ({ ...a, played: a.played + r.played, w: a.w + r.w, d: a.d + r.d,
    l: a.l + r.l, gf: a.gf + r.gf, ga: a.ga + r.ga, pts: a.pts + r.pts }), { team, played: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, pts: 0 });
  const label = `${displayName([...keys][0])} ${venue === "all" ? "overall" : venue} record (${[opts.season, comp ?? "all competitions"].filter(Boolean).join(" ")})`;
  return [`${label}:`, `- Matches: ${merged.played}`, `- Wins: ${merged.w}, Draws: ${merged.d}, Losses: ${merged.l}`,
    `- Goals For: ${merged.gf}, Goals Against: ${merged.ga}`, `- Win rate: ${pct(merged.w, merged.played)}`].join("\n");
}

export function teamCompetitions(ds: Dataset, team: string): string {
  const ms = filterMatches(ds, { team });
  const by = new Map<string, { n: number; seasons: Set<number> }>();
  for (const m of ms) {
    const e = by.get(m.competition) ?? { n: 0, seasons: new Set() };
    e.n++; e.seasons.add(m.season); by.set(m.competition, e);
  }
  return [`Competitions played by ${displayName([...resolveTeam(ds, team)][0])} in dataset:`,
    ...[...by].sort((a, b) => b[1].n - a[1].n).map(([c, e]) => {
      const s = [...e.seasons].sort();
      return `- ${c}: ${e.n} matches (seasons ${s[0]}-${s[s.length - 1]})`;
    })].join("\n");
}

function table(ds: Dataset, season: number): Rec[] {
  const ms = ds.league.filter(m => m.season === season);
  return [...records(ms).values()].sort((a, b) => b.pts - a.pts || b.w - a.w || (b.gf - b.ga) - (a.gf - a.ga) || b.gf - a.gf);
}

export function standings(ds: Dataset, season: number): string {
  const t = table(ds, season);
  if (!t.length) return `No Brasileirão data for season ${season}. Available seasons: ${[...ds.seasonSources.keys()].sort().join(", ")}`;
  const lines = [`${season} Brasileirão Final Standings (calculated from matches):`];
  t.forEach((r, i) => lines.push(`${i + 1}. ${displayName(r.team)} - ${r.pts} pts (${r.w}W, ${r.d}D, ${r.l}L, GF ${r.gf}, GA ${r.ga})${i === 0 ? " - Champion" : ""}`));
  if (t.length >= 20) lines.push("", `Relegated: ${t.slice(-4).map(r => displayName(r.team)).join(", ")}`);
  return lines.join("\n");
}

export function topScoringTeams(ds: Dataset, season?: number, limit = 10): string {
  const ms = season ? ds.league.filter(m => m.season === season) : ds.league;
  const t = [...records(ms).values()].sort((a, b) => b.gf - a.gf).slice(0, limit);
  return [`Top scoring teams (Brasileirão${season ? ` ${season}` : ", all seasons"}):`,
    ...t.map((r, i) => `${i + 1}. ${displayName(r.team)} - ${r.gf} goals in ${r.played} matches`)].join("\n");
}

function statsBlock(ms: Match[]): string[] {
  const goals = ms.reduce((s, m) => s + m.homeGoals + m.awayGoals, 0);
  const hw = ms.filter(m => m.homeGoals > m.awayGoals).length, dr = ms.filter(m => m.homeGoals === m.awayGoals).length;
  return [`- Matches: ${ms.length}`, `- Total goals: ${goals}`, `- Average goals per match: ${(ms.length ? goals / ms.length : 0).toFixed(2)}`,
    `- Home win rate: ${pct(hw, ms.length)}`, `- Draw rate: ${pct(dr, ms.length)}`, `- Away win rate: ${pct(ms.length - hw - dr, ms.length)}`];
}

export function competitionStats(ds: Dataset, competition?: string, season?: number): string {
  const ms = filterMatches(ds, { competition, season });
  return [`Statistics for ${competitionName(competition) ?? "all competitions"}${season ? ` ${season}` : ""}:`, ...statsBlock(ms)].join("\n");
}

export function compareSeasons(ds: Dataset, seasons: number[], competition = "Brasileirão"): string {
  const lines = [`Season comparison (${competitionName(competition)}):`];
  for (const s of seasons) {
    const ms = competitionName(competition) === "Brasileirão" ? ds.league.filter(m => m.season === s) : filterMatches(ds, { competition, season: s });
    const champ = competitionName(competition) === "Brasileirão" ? table(ds, s)[0] : undefined;
    lines.push("", `${s}:`, ...statsBlock(ms), ...(champ ? [`- Champion: ${displayName(champ.team)} (${champ.pts} pts)`] : []));
  }
  return lines.join("\n");
}

export function biggestWins(ds: Dataset, opts: { competition?: string; season?: number; team?: string; limit?: number }): string {
  const ms = filterMatches(ds, opts).slice().sort((a, b) => Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals)
    || (b.homeGoals + b.awayGoals) - (a.homeGoals + a.awayGoals));
  return [`Biggest victories (${competitionName(opts.competition) ?? "all competitions"}):`,
    ...ms.slice(0, opts.limit ?? 10).map((m, i) => `${i + 1}. ${fmtMatch(m)}`)].join("\n");
}

export function bestRecord(ds: Dataset, opts: { venue?: "home" | "away" | "all"; season?: number; competition?: string; minMatches?: number; limit?: number }): string {
  const venue = opts.venue ?? "all";
  const comp = opts.competition ?? "Brasileirão";
  const ms = filterMatches(ds, { competition: comp, season: opts.season });
  const min = opts.minMatches ?? (opts.season ? 5 : 19);
  const rs = [...records(ms, venue).values()].filter(r => r.played >= min)
    .sort((a, b) => b.w / b.played - a.w / a.played || b.pts - a.pts).slice(0, opts.limit ?? 10);
  return [`Best ${venue} records (${competitionName(comp)}${opts.season ? ` ${opts.season}` : ", all seasons"}, min ${min} matches):`,
    ...rs.map((r, i) => `${i + 1}. ${displayName(r.team)} - Win rate ${pct(r.w, r.played)} (${r.played} matches: ${r.w}W ${r.d}D ${r.l}L, GF ${r.gf} GA ${r.ga})`)].join("\n");
}

export function derbies(ds: Dataset, season?: number, limit = 100): string {
  const lines: string[] = [];
  let total = 0;
  for (const [a, b, name] of DERBIES) {
    const ms = ds.matches.filter(m => (!season || m.season === season) &&
      ((m.home === a && m.away === b) || (m.home === b && m.away === a)));
    if (!ms.length) continue;
    total += ms.length;
    lines.push(`${name} (${displayName(a)} vs ${displayName(b)}):`, ...ms.slice(0, limit).map(m => `- ${fmtMatch(m)}`));
  }
  return [`Derbies${season ? ` in ${season}` : ""}: ${total} matches`, ...lines].join("\n");
}

export function searchPlayers(ds: Dataset, f: { name?: string; nationality?: string; club?: string; position?: string; minOverall?: number; limit?: number }): string {
  const norm = (s: string) => stripAccents(s).toLowerCase();
  const pos = f.position?.toUpperCase();
  const FORWARDS = ["ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"];
  const ps = ds.players.filter(p =>
    (!f.name || norm(p.name).includes(norm(f.name))) &&
    (!f.nationality || norm(p.nationality) === norm(f.nationality) || (norm(f.nationality) === "brazilian" && p.nationality === "Brazil")) &&
    (!f.club || norm(p.club).includes(norm(f.club))) &&
    (!pos || p.position === pos || (pos === "FORWARD" && FORWARDS.includes(p.position))) &&
    (!f.minOverall || p.overall >= f.minOverall)).sort((a, b) => b.overall - a.overall);
  const limit = f.limit ?? 20;
  const lines = [`Players found: ${ps.length}`];
  ps.slice(0, limit).forEach((p, i) => lines.push(`${i + 1}. ${p.name} - Overall: ${p.overall}, Potential: ${p.potential}, Position: ${p.position}, ` +
    `Club: ${p.club || "Free agent"}, Nationality: ${p.nationality}, Age: ${p.age}`));
  if (ps.length > limit) lines.push(`... (${ps.length - limit} more players)`);
  if (ps.length === 1) lines.push(playerDetail(ps[0]));
  return lines.join("\n");
}

function playerDetail(p: Player): string {
  const top = Object.entries(p.skills).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, v]) => `${k} ${v}`).join(", ");
  return `Details: Jersey ${p.jersey}, Height ${p.height}, Weight ${p.weight}, Preferred foot ${p.foot}, Value ${p.value}\nTop attributes: ${top}`;
}

export function datasetInfo(ds: Dataset): string {
  const seasons = [...new Set(ds.matches.map(m => m.season))].sort();
  return ["Loaded datasets:", ...Object.entries(ds.files).map(([f, n]) => `- ${f}: ${n} rows`),
    `Unique matches after merging sources: ${ds.matches.length}`, `Players: ${ds.players.length}`,
    `Match seasons: ${seasons[0]}-${seasons[seasons.length - 1]}`,
    `Competitions: ${[...new Set(ds.matches.map(m => m.competition))].join(", ")}`].join("\n");
}
