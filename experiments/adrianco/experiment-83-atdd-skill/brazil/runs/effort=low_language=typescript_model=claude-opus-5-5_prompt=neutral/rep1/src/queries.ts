/** Query functions over the dataset. Each returns plain text formatted for an LLM/user. */
import type { Competition, Dataset, Match, Player } from "./data.js";
import { stripAccents, teamKey, teamMatches } from "./normalize.js";

export interface MatchFilter {
  team?: string;
  opponent?: string;
  venue?: "home" | "away" | "any";
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  stage?: string;
  limit?: number;
}

const COMP_ALIASES: [RegExp, Competition][] = [
  [/brasileir|serie a|série a|campeonato brasileiro/i, "Brasileirão"],
  [/copa do brasil|brazilian cup/i, "Copa do Brasil"],
  [/libertadores/i, "Libertadores"],
  [/serie b|série b/i, "Serie B"],
  [/serie c|série c/i, "Serie C"],
];

export function parseCompetition(c?: string): Competition | undefined {
  if (!c) return undefined;
  for (const [re, comp] of COMP_ALIASES) if (re.test(c)) return comp;
  throw new Error(`Unknown competition "${c}". Use Brasileirão, Copa do Brasil, Libertadores, Serie B or Serie C.`);
}

const byDateDesc = (a: Match, b: Match) => b.date.localeCompare(a.date);

export function fmtMatch(m: Match): string {
  const extra = m.stage ? m.stage : m.round ? `Round ${m.round}` : "";
  return `${m.date}: ${m.home} ${m.homeGoals}-${m.awayGoals} ${m.away} (${m.competition}${extra ? " " + extra : ""})`;
}

/** Name of a team as it appears in the data, for display. */
function teamLabel(ds: Dataset, q: string): string {
  const ms = ds.matches.find((m) => teamMatches(m.homeKey, q));
  return ms ? ms.home : q;
}

export function filterMatches(ds: Dataset, f: MatchFilter): Match[] {
  const comp = parseCompetition(f.competition);
  const venue = f.venue ?? "any";
  return ds.matches
    .filter((m) => {
      if (comp && m.competition !== comp) return false;
      if (f.season && m.season !== f.season) return false;
      if (f.dateFrom && m.date < f.dateFrom) return false;
      if (f.dateTo && m.date > f.dateTo) return false;
      if (f.stage && !(`${m.stage ?? ""} ${m.round ?? ""}`.toLowerCase().includes(f.stage.toLowerCase()))) return false;
      if (f.team) {
        const h = teamMatches(m.homeKey, f.team), a = teamMatches(m.awayKey, f.team);
        if (venue === "home" ? !h : venue === "away" ? !a : !(h || a)) return false;
        if (f.opponent) {
          const oh = teamMatches(m.homeKey, f.opponent), oa = teamMatches(m.awayKey, f.opponent);
          if (!((h && oa) || (a && oh))) return false;
        }
      }
      return true;
    })
    .sort(byDateDesc);
}

export function searchMatches(ds: Dataset, f: MatchFilter): string {
  const ms = filterMatches(ds, f);
  if (!ms.length) return "No matches found for the given criteria.";
  const limit = f.limit ?? 20;
  const lines = ms.slice(0, limit).map((m) => "- " + fmtMatch(m));
  if (ms.length > limit) lines.push(`- ... (${ms.length - limit} more matches in dataset)`);
  let head = `Found ${ms.length} matches:`;
  if (f.team && f.opponent) head = `${teamLabel(ds, f.team)} vs ${teamLabel(ds, f.opponent)} (${ms.length} matches):`;
  return [head, ...lines].join("\n");
}

export interface H2H { aWins: number; bWins: number; draws: number; aGoals: number; bGoals: number; matches: Match[] }

export function headToHeadData(ds: Dataset, a: string, b: string, competition?: string): H2H {
  const matches = filterMatches(ds, { team: a, opponent: b, competition });
  const r: H2H = { aWins: 0, bWins: 0, draws: 0, aGoals: 0, bGoals: 0, matches };
  for (const m of matches) {
    const aHome = teamMatches(m.homeKey, a);
    const ag = aHome ? m.homeGoals : m.awayGoals, bg = aHome ? m.awayGoals : m.homeGoals;
    r.aGoals += ag; r.bGoals += bg;
    if (ag > bg) r.aWins++; else if (bg > ag) r.bWins++; else r.draws++;
  }
  return r;
}

export function headToHead(ds: Dataset, a: string, b: string, competition?: string, limit = 10): string {
  const h = headToHeadData(ds, a, b, competition);
  const la = teamLabel(ds, a), lb = teamLabel(ds, b);
  if (!h.matches.length) return `No matches found between ${la} and ${lb}.`;
  const lines = [`${la} vs ${lb}${competition ? ` (${parseCompetition(competition)})` : ""}:`];
  for (const m of h.matches.slice(0, limit)) lines.push("- " + fmtMatch(m));
  if (h.matches.length > limit) lines.push(`- ... (${h.matches.length - limit} more matches in dataset)`);
  lines.push("", `Head-to-head in dataset (${h.matches.length} matches): ${la} ${h.aWins} wins, ${lb} ${h.bWins} wins, ${h.draws} draws`);
  lines.push(`Goals: ${la} ${h.aGoals}, ${lb} ${h.bGoals}`);
  return lines.join("\n");
}

export interface Record_ { team: string; played: number; wins: number; draws: number; losses: number; gf: number; ga: number; points: number }

function accumulate(rec: Record_, gf: number, ga: number) {
  rec.played++; rec.gf += gf; rec.ga += ga;
  if (gf > ga) { rec.wins++; rec.points += 3; } else if (gf === ga) { rec.draws++; rec.points++; } else rec.losses++;
}

export function teamRecordData(ds: Dataset, team: string, f: Omit<MatchFilter, "team" | "opponent"> = {}): Record_ {
  const rec: Record_ = { team: teamLabel(ds, team), played: 0, wins: 0, draws: 0, losses: 0, gf: 0, ga: 0, points: 0 };
  const pool = f.season && parseCompetition(f.competition) === "Brasileirão" ? seasonMatches(ds, f.season) : undefined;
  const ms = pool ? pool.filter((m) => {
    const h = teamMatches(m.homeKey, team), a = teamMatches(m.awayKey, team);
    return f.venue === "home" ? h : f.venue === "away" ? a : h || a;
  }) : filterMatches(ds, { ...f, team });
  for (const m of ms) {
    const home = teamMatches(m.homeKey, team);
    accumulate(rec, home ? m.homeGoals : m.awayGoals, home ? m.awayGoals : m.homeGoals);
  }
  return rec;
}

const pct = (n: number, d: number) => (d ? ((100 * n) / d).toFixed(1) : "0.0") + "%";

export function teamRecord(ds: Dataset, team: string, f: Omit<MatchFilter, "team" | "opponent"> = {}): string {
  const r = teamRecordData(ds, team, f);
  if (!r.played) return `No matches found for ${team} with the given criteria.`;
  const venue = f.venue && f.venue !== "any" ? `${f.venue} ` : "";
  const ctx = [f.season, f.competition ? parseCompetition(f.competition) : "all competitions"].filter(Boolean).join(" ");
  return [
    `${r.team} ${venue}record (${ctx}):`,
    `- Matches: ${r.played}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.gf}, Goals Against: ${r.ga}, Goal Difference: ${r.gf - r.ga}`,
    `- Win rate: ${pct(r.wins, r.played)}`,
  ].join("\n");
}

/** Brasileirão matches for a season from a single authoritative source to avoid double counting. */
export function seasonMatches(ds: Dataset, season: number): Match[] {
  for (const src of ["Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv"]) {
    const ms = ds.allMatches.filter((m) => m.source === src && m.season === season && m.competition === "Brasileirão");
    if (ms.length) return ms;
  }
  return [];
}

export function standingsData(ds: Dataset, season: number, competition = "Brasileirão"): Record_[] {
  const comp = parseCompetition(competition)!;
  const ms = comp === "Brasileirão" ? seasonMatches(ds, season) : ds.matches.filter((m) => m.competition === comp && m.season === season);
  const table = new Map<string, Record_>();
  const get = (k: string, name: string) => {
    let r = table.get(k);
    if (!r) table.set(k, (r = { team: name, played: 0, wins: 0, draws: 0, losses: 0, gf: 0, ga: 0, points: 0 }));
    return r;
  };
  for (const m of ms) {
    accumulate(get(m.homeKey, m.home), m.homeGoals, m.awayGoals);
    accumulate(get(m.awayKey, m.away), m.awayGoals, m.homeGoals);
  }
  return [...table.values()].sort((a, b) => b.points - a.points || b.wins - a.wins || b.gf - b.ga - (a.gf - a.ga) || b.gf - a.gf || a.team.localeCompare(b.team));
}

export function standings(ds: Dataset, season: number, competition = "Brasileirão", top?: number): string {
  const t = standingsData(ds, season, competition);
  if (!t.length) return `No ${competition} data for ${season}.`;
  const comp = parseCompetition(competition);
  const isLeague = comp === "Brasileirão" || comp === "Serie B" || comp === "Serie C";
  const rows = t.slice(0, top ?? t.length).map((r, i) => {
    let tag = "";
    if (isLeague && i === 0) tag = " - Champion";
    if (comp === "Brasileirão" && t.length >= 20 && i >= t.length - 4) tag = " - Relegated";
    return `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GF ${r.gf} GA ${r.ga} GD ${r.gf - r.ga}${tag}`;
  });
  const played = t.reduce((n, r) => n + r.played, 0) / 2;
  const expected = (t.length * (t.length - 1));
  const note = isLeague && played < expected ? [`Note: dataset has ${played} of ${expected} matches for this season; table may be incomplete.`] : [];
  return [`${season} ${comp} ${isLeague ? "Final Standings" : "aggregate table"} (calculated from matches):`, ...rows, ...note].join("\n");
}

export function relegated(ds: Dataset, season: number): string {
  const t = standingsData(ds, season);
  if (t.length < 20) return `No complete Brasileirão data for ${season}.`;
  return `Teams relegated from the ${season} Brasileirão (bottom 4, calculated from matches):\n` +
    t.slice(-4).map((r, i) => `${t.length - 3 + i}. ${r.team} - ${r.points} pts`).join("\n");
}

export function champion(ds: Dataset, season: number): string {
  const t = standingsData(ds, season);
  if (!t.length) return `No Brasileirão data for ${season}.`;
  const [c, s] = t;
  return `${c.team} won the ${season} Brasileirão with ${c.points} points (${c.wins}W, ${c.draws}D, ${c.losses}L), ${c.points - (s?.points ?? 0)} points ahead of ${s?.team ?? "-"}.`;
}

export function competitionStats(ds: Dataset, competition?: string, season?: number): string {
  const ms = filterMatches(ds, { competition, season });
  if (!ms.length) return "No matches found.";
  let goals = 0, hw = 0, aw = 0, d = 0;
  for (const m of ms) {
    goals += m.homeGoals + m.awayGoals;
    if (m.homeGoals > m.awayGoals) hw++; else if (m.awayGoals > m.homeGoals) aw++; else d++;
  }
  const label = `${competition ? parseCompetition(competition) : "All competitions"}${season ? " " + season : ""}`;
  return [
    `Statistics for ${label} (${ms.length} matches):`,
    `- Total goals: ${goals}`,
    `- Average goals per match: ${(goals / ms.length).toFixed(2)}`,
    `- Home win rate: ${pct(hw, ms.length)}`,
    `- Away win rate: ${pct(aw, ms.length)}`,
    `- Draw rate: ${pct(d, ms.length)}`,
  ].join("\n");
}

export function compareSeasons(ds: Dataset, seasons: number[], competition = "Brasileirão"): string {
  return seasons.map((s) => {
    const t = standingsData(ds, s, competition);
    const base = competitionStats(ds, competition, s);
    return t.length ? `${base}\n- Champion/leader: ${t[0].team} (${t[0].points} pts)\n- Top scoring team: ${[...t].sort((a, b) => b.gf - a.gf)[0].team}` : base;
  }).join("\n\n");
}

export function biggestWins(ds: Dataset, f: Omit<MatchFilter, "opponent"> = {}, limit = 10): string {
  const ms = filterMatches(ds, f).sort((a, b) => Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals) || (b.homeGoals + b.awayGoals) - (a.homeGoals + a.awayGoals) || byDateDesc(a, b));
  if (!ms.length) return "No matches found.";
  return [`Biggest victories${f.competition ? ` in ${parseCompetition(f.competition)}` : ""}${f.season ? ` ${f.season}` : ""}${f.team ? ` involving ${f.team}` : ""}:`,
    ...ms.slice(0, limit).map((m, i) => `${i + 1}. ${fmtMatch(m)} (margin ${Math.abs(m.homeGoals - m.awayGoals)})`)].join("\n");
}

export function rankTeams(ds: Dataset, opts: { competition?: string; season?: number; venue?: "home" | "away" | "any"; sortBy?: "winRate" | "goalsFor" | "goalsAgainst" | "points"; minMatches?: number; limit?: number }): string {
  const venue = opts.venue ?? "any";
  const ms = opts.season && parseCompetition(opts.competition) === "Brasileirão" ? seasonMatches(ds, opts.season) : filterMatches(ds, { competition: opts.competition, season: opts.season });
  const t = new Map<string, Record_>();
  const get = (k: string, n: string) => t.get(k) ?? (t.set(k, { team: n, played: 0, wins: 0, draws: 0, losses: 0, gf: 0, ga: 0, points: 0 }), t.get(k)!);
  for (const m of ms) {
    if (venue !== "away") accumulate(get(m.homeKey, m.home), m.homeGoals, m.awayGoals);
    if (venue !== "home") accumulate(get(m.awayKey, m.away), m.awayGoals, m.homeGoals);
  }
  const min = opts.minMatches ?? (opts.season ? 1 : 10);
  const sortBy = opts.sortBy ?? "winRate";
  const key = (r: Record_) => sortBy === "goalsFor" ? r.gf : sortBy === "goalsAgainst" ? -r.ga : sortBy === "points" ? r.points : r.wins / r.played;
  const rows = [...t.values()].filter((r) => r.played >= min).sort((a, b) => key(b) - key(a) || b.played - a.played);
  const title = `Teams ranked by ${sortBy} (${venue === "any" ? "all" : venue} matches, ${opts.competition ? parseCompetition(opts.competition) : "all competitions"}${opts.season ? " " + opts.season : ""}, min ${min} matches):`;
  return [title, ...rows.slice(0, opts.limit ?? 10).map((r, i) =>
    `${i + 1}. ${r.team} - ${r.played} matches, ${r.wins}W ${r.draws}D ${r.losses}L, GF ${r.gf} GA ${r.ga}, win rate ${pct(r.wins, r.played)}`)].join("\n");
}

export function teamCompetitions(ds: Dataset, team: string): string {
  const ms = filterMatches(ds, { team });
  if (!ms.length) return `No matches found for ${team}.`;
  const by = new Map<string, Match[]>();
  for (const m of ms) by.set(m.competition, [...(by.get(m.competition) ?? []), m]);
  return [`Competitions played by ${teamLabel(ds, team)} in the dataset:`, ...[...by].map(([c, list]) => {
    const seasons = [...new Set(list.map((m) => m.season))].sort();
    return `- ${c}: ${list.length} matches (seasons ${seasons[0]}-${seasons[seasons.length - 1]})`;
  })].join("\n");
}

export const RIVALRIES: [string, string, string][] = [
  ["Flamengo", "Fluminense", "Fla-Flu"], ["Flamengo", "Vasco", "Clássico dos Milhões"], ["Flamengo", "Botafogo-RJ", "Clássico da Rivalidade"],
  ["Fluminense", "Vasco", "Clássico dos Gigantes"], ["Botafogo-RJ", "Vasco", "Clássico da Amizade"], ["Botafogo-RJ", "Fluminense", "Clássico Vovô"],
  ["Corinthians", "Palmeiras", "Derby Paulista"], ["Corinthians", "São Paulo", "Majestoso"], ["Palmeiras", "São Paulo", "Choque-Rei"],
  ["Santos", "Corinthians", "Clássico Alvinegro"], ["Santos", "Palmeiras", "Clássico da Saudade"], ["Santos", "São Paulo", "San-São"],
  ["Grêmio", "Internacional", "Grenal"], ["Atlético-MG", "Cruzeiro", "Clássico Mineiro"], ["Bahia", "Vitória", "Ba-Vi"],
  ["Athletico-PR", "Coritiba", "Atletiba"], ["Sport", "Náutico", "Clássico dos Clássicos"], ["Ceará", "Fortaleza", "Clássico-Rei"],
];

export function derbies(ds: Dataset, f: { season?: number; competition?: string; limit?: number } = {}): string {
  const lines: string[] = [];
  let total = 0;
  for (const [a, b, name] of RIVALRIES) {
    const h = headToHeadData(ds, a, b, f.competition);
    const ms = h.matches.filter((m) => !f.season || m.season === f.season);
    if (!ms.length) continue;
    total += ms.length;
    lines.push(`${name} (${a} vs ${b}) - ${ms.length} matches:`);
    for (const m of ms.slice(0, f.limit ?? 5)) lines.push("  - " + fmtMatch(m));
    if (ms.length > (f.limit ?? 5)) lines.push(`  - ... (${ms.length - (f.limit ?? 5)} more)`);
  }
  return total ? [`Derbies${f.season ? " in " + f.season : ""} (${total} matches):`, ...lines].join("\n") : "No derby matches found.";
}

// ---------------- Players ----------------

export interface PlayerFilter {
  name?: string; nationality?: string; club?: string; position?: string;
  minOverall?: number; maxAge?: number; sortBy?: "overall" | "potential" | "age" | "name"; limit?: number;
}

const fold = (s: string) => stripAccents(s).toLowerCase();

const POSITION_GROUPS: Record<string, string[]> = {
  forward: ["ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"], striker: ["ST", "CF", "LS", "RS"],
  midfielder: ["CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"],
  defender: ["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"], goalkeeper: ["GK"],
};

export function filterPlayers(ds: Dataset, f: PlayerFilter): Player[] {
  const pos = f.position ? (POSITION_GROUPS[fold(f.position).replace(/s$/, "")] ?? [f.position.toUpperCase()]) : undefined;
  const nm = f.name ? fold(f.name) : undefined;
  const sortBy = f.sortBy ?? "overall";
  // Club: prefer exact normalized match ("Santos" should not pull in "Santos Laguna").
  let clubOk: ((p: Player) => boolean) | undefined;
  if (f.club) {
    const ck = teamKey(f.club);
    const exact = ds.players.some((p) => p.clubKey === ck);
    clubOk = exact ? (p) => p.clubKey === ck : (p) => !!p.clubKey && (teamMatches(p.clubKey, f.club!) || fold(p.club).includes(fold(f.club!)));
  }
  return ds.players.filter((p) => {
    if (nm && !fold(p.name).includes(nm)) return false;
    if (f.nationality && fold(p.nationality) !== fold(f.nationality)) return false;
    if (clubOk && !clubOk(p)) return false;
    if (pos && !pos.includes(p.position)) return false;
    if (f.minOverall && p.overall < f.minOverall) return false;
    if (f.maxAge && p.age > f.maxAge) return false;
    return true;
  }).sort((a, b) => sortBy === "name" ? a.name.localeCompare(b.name) : sortBy === "age" ? a.age - b.age : (b[sortBy] - a[sortBy]) || b.overall - a.overall);
}

const fmtPlayer = (p: Player, i: number) => `${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club || "Free agent"}, Nationality: ${p.nationality}, Age: ${p.age}`;

export function searchPlayers(ds: Dataset, f: PlayerFilter): string {
  const ps = filterPlayers(ds, f);
  if (!ps.length) return "No players found for the given criteria.";
  const limit = f.limit ?? 20;
  const lines = [`Found ${ps.length} players:`, ...ps.slice(0, limit).map(fmtPlayer)];
  if (ps.length > limit) lines.push(`... (${ps.length - limit} more)`);
  return lines.join("\n");
}

export function playerDetails(ds: Dataset, name: string): string {
  let ps = filterPlayers(ds, { name });
  if (!ps.length) {
    // Fall back to any individual name token (e.g. "Gabriel Barbosa" -> "Barbosa", "Gabriel").
    const tokens = name.split(/\s+/).filter((t) => t.length > 2).reverse();
    const near = tokens.flatMap((t) => filterPlayers(ds, { name: t })).slice(0, 8);
    return near.length
      ? `No exact player named "${name}" in the FIFA data. Closest matches:\n${near.map(fmtPlayer).join("\n")}`
      : `No player found matching "${name}".`;
  }
  const p = ps[0];
  const top = Object.entries(p.skills).filter(([k]) => !k.startsWith("GK") || p.position === "GK").sort((a, b) => b[1] - a[1]).slice(0, 8);
  const out = [
    `${p.name} (FIFA ID ${p.id})`,
    `- Age: ${p.age}, Nationality: ${p.nationality}`,
    `- Club: ${p.club || "Free agent"}, Position: ${p.position}, Jersey: ${p.jersey || "-"}`,
    `- Overall: ${p.overall}, Potential: ${p.potential}`,
    `- Height: ${p.height}, Weight: ${p.weight}, Preferred foot: ${p.preferredFoot}`,
    `- Value: ${p.value}, Wage: ${p.wage}`,
    `- Top attributes: ${top.map(([k, v]) => `${k} ${v}`).join(", ")}`,
  ];
  if (ps.length > 1) out.push(`Other matches: ${ps.slice(1, 6).map((x) => `${x.name} (${x.club || "-"})`).join(", ")}`);
  return out.join("\n");
}

/** Clubs that appear in Brazilian match data (used to identify "Brazilian clubs" in FIFA data). */
export function brazilianClubKeys(ds: Dataset): Set<string> {
  const s = new Set<string>();
  for (const m of ds.matches) if (m.competition !== "Libertadores") { s.add(m.homeKey); s.add(m.awayKey); }
  return s;
}

export function brazilianClubsSummary(ds: Dataset, nationality = "Brazil"): string {
  const keys = brazilianClubKeys(ds);
  const by = new Map<string, Player[]>();
  for (const p of ds.players) {
    if (!p.clubKey || !keys.has(p.clubKey)) continue;
    if (nationality && fold(p.nationality) !== fold(nationality)) continue;
    by.set(p.club, [...(by.get(p.club) ?? []), p]);
  }
  if (!by.size) return "No players found at Brazilian clubs.";
  const rows = [...by].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]));
  return [`${nationality || "All"} players at Brazilian clubs:`, ...rows.map(([c, ps]) =>
    `- ${c}: ${ps.length} players (avg rating: ${Math.round(ps.reduce((s, p) => s + p.overall, 0) / ps.length)}, best: ${ps.sort((a, b) => b.overall - a.overall)[0].name})`)].join("\n");
}

/** Cross-file profile: match record + FIFA squad for a club. */
export function teamProfile(ds: Dataset, team: string): string {
  const parts = [teamRecord(ds, team), teamCompetitions(ds, team)];
  const squad = filterPlayers(ds, { club: team });
  parts.push(squad.length ? `FIFA squad (${squad.length} players, top 10):\n${squad.slice(0, 10).map(fmtPlayer).join("\n")}` : "No FIFA players listed for this club.");
  const last = filterMatches(ds, { team })[0];
  if (last) parts.push(`Most recent match in data: ${fmtMatch(last)}`);
  return parts.join("\n\n");
}

export function datasetInfo(ds: Dataset): string {
  const comps = new Map<string, number>();
  for (const m of ds.matches) comps.set(m.competition, (comps.get(m.competition) ?? 0) + 1);
  return ["Loaded files (rows):", ...Object.entries(ds.bySource).map(([k, v]) => `- ${k}: ${v}`),
    `Deduplicated matches: ${ds.matches.length}`, ...[...comps].map(([k, v]) => `- ${k}: ${v}`)].join("\n");
}
export { teamKey };
