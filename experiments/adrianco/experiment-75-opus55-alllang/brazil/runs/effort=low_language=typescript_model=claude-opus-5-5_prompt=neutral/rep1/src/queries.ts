import type { Competition, Dataset, Match, Player } from "./data.js";
import { normalizeTeam, stripAccents, teamMatches } from "./normalize.js";

// ---------- helpers ----------

export function parseCompetition(q?: string): Competition | undefined {
  if (!q) return undefined;
  const s = stripAccents(q).toLowerCase();
  if (s.includes("liberta")) return "Copa Libertadores";
  if (s.includes("copa do brasil") || s.includes("cup") || s.includes("copa")) return "Copa do Brasil";
  if (/serie b\b/.test(s)) return "Brasileirão Série B";
  if (/serie c\b/.test(s)) return "Brasileirão Série C";
  if (s.includes("brasileir") || /serie a\b/.test(s)) return "Brasileirão Série A";
  throw new Error(`Unknown competition "${q}". Use Brasileirão (Série A/B/C), Copa do Brasil or Libertadores.`);
}

const dayNum = (d: string) => Date.parse(d) / 86400000;

/** Remove the same fixture reported by several files (same teams, competition and score, dates within a day). */
export function dedupe(list: Match[]): Match[] {
  const seen = new Map<string, number[]>();
  return list.filter((m) => {
    const k = `${m.homeKey}|${m.awayKey}|${m.competition}|${m.homeGoals}-${m.awayGoals}`;
    const d = dayNum(m.date);
    const dates = seen.get(k) ?? seen.set(k, []).get(k)!;
    if (dates.some((x) => Math.abs(x - d) <= 1)) return false;
    dates.push(d);
    return true;
  });
}

export function formatMatch(m: Match): string {
  const rd = m.round ? (/^\d+$/.test(m.round) ? ` Round ${m.round}` : ` – ${m.round}`) : "";
  return `${m.date}: ${m.home} ${m.homeGoals}-${m.awayGoals} ${m.away} (${m.competition} ${m.season}${rd})`;
}

/** Matches in a season/competition that are a final. Libertadores has a "final" stage; Copa do Brasil's final is its last round. */
function isFinal(m: Match, ds: Dataset): boolean {
  if (m.competition === "Copa Libertadores") return (m.round ?? "").toLowerCase() === "final";
  if (m.competition === "Copa do Brasil" && m.source === "Brazilian_Cup_Matches.csv") {
    const max = Math.max(...ds.matches.filter((x) => x.source === m.source && x.season === m.season).map((x) => Number(x.round) || 0));
    return max >= 6 && Number(m.round) === max; // incomplete seasons in the file have no final
  }
  return false;
}

// ---------- match search ----------

export interface MatchQuery {
  team?: string; opponent?: string; venue?: "home" | "away" | "any";
  competition?: string; season?: number; dateFrom?: string; dateTo?: string; stage?: string; limit?: number;
}

export function findMatches(ds: Dataset, q: MatchQuery): Match[] {
  const comp = parseCompetition(q.competition);
  const t = q.team ? normalizeTeam(q.team) : undefined;
  const o = q.opponent ? normalizeTeam(q.opponent) : undefined;
  const venue = q.venue ?? "any";
  const stage = q.stage?.toLowerCase();
  // Série A fixtures come from one authoritative file per season; other files overlap and would duplicate them.
  const pool = [...[...ds.serieA.values()].flat(), ...ds.matches.filter((m) => m.competition !== "Brasileirão Série A")];
  let res = pool.filter((m) => {
    if (comp && m.competition !== comp) return false;
    if (q.season !== undefined && m.season !== q.season) return false;
    if (q.dateFrom && m.date < q.dateFrom) return false;
    if (q.dateTo && m.date > q.dateTo) return false;
    if (t) {
      const home = teamMatches(m.homeKey, t) && (!o || teamMatches(m.awayKey, o));
      const away = teamMatches(m.awayKey, t) && (!o || teamMatches(m.homeKey, o));
      if (venue === "home" ? !home : venue === "away" ? !away : !(home || away)) return false;
    } else if (o && !teamMatches(m.homeKey, o) && !teamMatches(m.awayKey, o)) return false;
    if (stage) {
      if (stage === "final") { if (!isFinal(m, ds)) return false; }
      else if (!(m.round ?? "").toLowerCase().includes(stage)) return false;
    }
    return true;
  });
  res = dedupe(res).sort((a, b) => b.date.localeCompare(a.date));
  return res;
}

// ---------- team records ----------

export interface Record_ {
  team: string; matches: number; wins: number; draws: number; losses: number;
  goalsFor: number; goalsAgainst: number; points: number;
}

function emptyRec(team: string): Record_ {
  return { team, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0 };
}

function addResult(r: Record_, gf: number, ga: number) {
  r.matches++; r.goalsFor += gf; r.goalsAgainst += ga;
  if (gf > ga) { r.wins++; r.points += 3; } else if (gf === ga) { r.draws++; r.points++; } else r.losses++;
}

/** Série A matches with no cross-file double counting; other competitions deduped. */
function statMatches(ds: Dataset, comp?: Competition, season?: number): Match[] {
  const serieA = [...ds.serieA.entries()].filter(([s]) => season === undefined || s === season).flatMap(([, l]) => l);
  if (comp === "Brasileirão Série A") return serieA;
  const others = dedupe(ds.matches.filter((m) => m.competition !== "Brasileirão Série A" && (!comp || m.competition === comp) && (season === undefined || m.season === season)));
  return comp ? others : [...serieA, ...others];
}

export function teamRecord(ds: Dataset, team: string, opts: { season?: number; competition?: string; venue?: "home" | "away" | "any" } = {}) {
  const key = normalizeTeam(team);
  const comp = parseCompetition(opts.competition);
  const venue = opts.venue ?? "any";
  const rec = emptyRec(team);
  const byComp = new Map<string, Record_>();
  let name = team;
  const matchedKeys = new Set<string>();
  for (const m of statMatches(ds, comp, opts.season)) {
    const isHome = teamMatches(m.homeKey, key), isAway = teamMatches(m.awayKey, key);
    if (isHome) matchedKeys.add(m.homeKey); if (isAway) matchedKeys.add(m.awayKey);
    if (isHome && venue !== "away") { name = m.home; addResult(rec, m.homeGoals, m.awayGoals); addResult(byComp.get(m.competition) ?? byComp.set(m.competition, emptyRec(m.competition)).get(m.competition)!, m.homeGoals, m.awayGoals); }
    else if (isAway && venue !== "home") { name = m.away; addResult(rec, m.awayGoals, m.homeGoals); addResult(byComp.get(m.competition) ?? byComp.set(m.competition, emptyRec(m.competition)).get(m.competition)!, m.awayGoals, m.homeGoals); }
  }
  rec.team = matchedKeys.size > 1 ? team : name;
  return { record: rec, byCompetition: [...byComp.values()], ambiguous: matchedKeys.size > 1 ? [...matchedKeys] : undefined };
}

const pct = (a: number, b: number) => (b ? ((100 * a) / b).toFixed(1) : "0.0");

export function formatRecord(r: Record_, title: string): string {
  return [
    `${title}:`,
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst}`,
    `- Win rate: ${pct(r.wins, r.matches)}%`,
  ].join("\n");
}

// ---------- head to head ----------

export function headToHead(ds: Dataset, a: string, b: string, competition?: string) {
  const ms = findMatches(ds, { team: a, opponent: b, competition });
  const ka = normalizeTeam(a);
  let aw = 0, bw = 0, d = 0, ag = 0, bg = 0;
  let nameA = a, nameB = b;
  for (const m of ms) {
    const aHome = teamMatches(m.homeKey, ka);
    const [ga, gb] = aHome ? [m.homeGoals, m.awayGoals] : [m.awayGoals, m.homeGoals];
    if (aHome) { nameA = m.home; nameB = m.away; } else { nameA = m.away; nameB = m.home; }
    ag += ga; bg += gb;
    if (ga > gb) aw++; else if (gb > ga) bw++; else d++;
  }
  return { teamA: nameA, teamB: nameB, matches: ms, winsA: aw, winsB: bw, draws: d, goalsA: ag, goalsB: bg };
}

// ---------- standings ----------

export function standings(ds: Dataset, season: number, competition = "Brasileirão") {
  const comp = parseCompetition(competition)!;
  const ms = statMatches(ds, comp, season);
  const table = new Map<string, Record_>();
  for (const m of ms) {
    addResult(table.get(m.homeKey) ?? table.set(m.homeKey, emptyRec(m.home)).get(m.homeKey)!, m.homeGoals, m.awayGoals);
    addResult(table.get(m.awayKey) ?? table.set(m.awayKey, emptyRec(m.away)).get(m.awayKey)!, m.awayGoals, m.homeGoals);
  }
  return [...table.values()].sort((x, y) => y.points - x.points || y.wins - x.wins
    || (y.goalsFor - y.goalsAgainst) - (x.goalsFor - x.goalsAgainst) || y.goalsFor - x.goalsFor || x.team.localeCompare(y.team));
}

export function formatStandings(rows: Record_[], season: number, comp: string): string {
  if (!rows.length) return `No ${comp} matches found for ${season}.`;
  const relegation = comp === "Brasileirão Série A" && rows.length >= 20 ? rows.length - 4 : Infinity;
  const lines = rows.map((r, i) => `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, GF ${r.goalsFor}, GA ${r.goalsAgainst}, GD ${r.goalsFor - r.goalsAgainst})${i === 0 ? " - Champion" : i >= relegation ? " - Relegated" : ""}`);
  return [`${season} ${comp} Final Standings (calculated from matches):`, ...lines].join("\n");
}

// ---------- aggregate statistics ----------

export function competitionStats(ds: Dataset, opts: { competition?: string; season?: number } = {}) {
  const comp = parseCompetition(opts.competition);
  const ms = statMatches(ds, comp, opts.season);
  const goals = ms.reduce((s, m) => s + m.homeGoals + m.awayGoals, 0);
  const hw = ms.filter((m) => m.homeGoals > m.awayGoals).length;
  const aw = ms.filter((m) => m.homeGoals < m.awayGoals).length;
  const scorers = new Map<string, { team: string; goals: number }>();
  for (const m of ms) {
    for (const [k, n, g] of [[m.homeKey, m.home, m.homeGoals], [m.awayKey, m.away, m.awayGoals]] as const) {
      const e = scorers.get(k) ?? scorers.set(k, { team: n, goals: 0 }).get(k)!;
      e.goals += g;
    }
  }
  const topScoringTeams = [...scorers.values()].sort((a, b) => b.goals - a.goals).slice(0, 5);
  return {
    competition: comp ?? "All competitions", season: opts.season, matches: ms.length, goals,
    avgGoals: ms.length ? goals / ms.length : 0,
    homeWinRate: ms.length ? hw / ms.length : 0, awayWinRate: ms.length ? aw / ms.length : 0,
    drawRate: ms.length ? (ms.length - hw - aw) / ms.length : 0, topScoringTeams,
  };
}

export function biggestWins(ds: Dataset, opts: { competition?: string; season?: number; team?: string; limit?: number } = {}) {
  const ms = findMatches(ds, { competition: opts.competition, season: opts.season, team: opts.team });
  return ms.sort((a, b) => Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals)
    || (b.homeGoals + b.awayGoals) - (a.homeGoals + a.awayGoals) || a.date.localeCompare(b.date)).slice(0, opts.limit ?? 10);
}

/** Rank teams by home or away record (min matches filter to avoid tiny samples). */
export function bestRecords(ds: Dataset, opts: { venue: "home" | "away"; competition?: string; season?: number; minMatches?: number; limit?: number }) {
  const comp = parseCompetition(opts.competition);
  const table = new Map<string, Record_>();
  for (const m of statMatches(ds, comp, opts.season)) {
    const [k, n, gf, ga] = opts.venue === "home" ? [m.homeKey, m.home, m.homeGoals, m.awayGoals] : [m.awayKey, m.away, m.awayGoals, m.homeGoals];
    addResult(table.get(k) ?? table.set(k, emptyRec(n)).get(k)!, gf, ga);
  }
  const min = opts.minMatches ?? 10;
  return [...table.values()].filter((r) => r.matches >= min)
    .sort((a, b) => b.points / b.matches - a.points / a.matches || b.wins - a.wins).slice(0, opts.limit ?? 10);
}

export function teamCompetitions(ds: Dataset, team: string) {
  const key = normalizeTeam(team);
  const out = new Map<string, Set<number>>();
  for (const m of ds.matches) {
    if (teamMatches(m.homeKey, key) || teamMatches(m.awayKey, key)) {
      (out.get(m.competition) ?? out.set(m.competition, new Set()).get(m.competition)!).add(m.season);
    }
  }
  return [...out.entries()].map(([competition, s]) => ({ competition, seasons: [...s].sort() }));
}

// ---------- derbies ----------

export const RIVALRIES: { name: string; teams: [string, string] }[] = [
  { name: "Fla-Flu", teams: ["flamengo", "fluminense"] },
  { name: "Clássico dos Milhões", teams: ["flamengo", "vasco"] },
  { name: "Clássico da Rivalidade", teams: ["flamengo", "botafogo"] },
  { name: "Clássico dos Gigantes", teams: ["fluminense", "vasco"] },
  { name: "Clássico Vovô", teams: ["fluminense", "botafogo"] },
  { name: "Clássico da Amizade", teams: ["botafogo", "vasco"] },
  { name: "Derby Paulista", teams: ["corinthians", "palmeiras"] },
  { name: "Choque-Rei", teams: ["palmeiras", "sao paulo"] },
  { name: "Majestoso", teams: ["corinthians", "sao paulo"] },
  { name: "San-São", teams: ["santos", "sao paulo"] },
  { name: "Clássico Alvinegro", teams: ["santos", "corinthians"] },
  { name: "Clássico da Saudade", teams: ["santos", "palmeiras"] },
  { name: "Grenal", teams: ["gremio", "internacional"] },
  { name: "Clássico Mineiro", teams: ["atletico-mg", "cruzeiro"] },
  { name: "Ba-Vi", teams: ["bahia", "vitoria"] },
  { name: "Atletiba", teams: ["atletico-pr", "coritiba"] },
  { name: "Clássico-Rei", teams: ["ceara", "fortaleza"] },
];

export function derbies(ds: Dataset, opts: { season?: number; competition?: string } = {}) {
  const comp = parseCompetition(opts.competition);
  const out: { derby: string; match: Match }[] = [];
  for (const m of statMatches(ds)) {
    if (opts.season !== undefined && m.season !== opts.season) continue;
    if (comp && m.competition !== comp) continue;
    const r = RIVALRIES.find(({ teams: [a, b] }) => (m.homeKey === a && m.awayKey === b) || (m.homeKey === b && m.awayKey === a));
    if (r) out.push({ derby: r.name, match: m });
  }
  return out.sort((a, b) => b.match.date.localeCompare(a.match.date));
}

// ---------- players ----------

export interface PlayerQuery { name?: string; nationality?: string; club?: string; position?: string; minOverall?: number; limit?: number }

const fold = (s: string) => stripAccents(s).toLowerCase();

export function searchPlayers(ds: Dataset, q: PlayerQuery): Player[] {
  const name = q.name ? fold(q.name) : undefined;
  const nat = q.nationality ? fold(q.nationality) : undefined;
  const club = q.club ? normalizeTeam(q.club) : undefined;
  const pos = q.position?.toUpperCase();
  const POS_GROUPS: Record<string, string[]> = {
    FORWARD: ["ST", "CF", "LF", "RF", "LS", "RS", "LW", "RW"], STRIKER: ["ST", "CF", "LS", "RS"],
    MIDFIELDER: ["CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"],
    DEFENDER: ["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"], GOALKEEPER: ["GK"],
  };
  const posKey = pos?.replace(/S$/, "");
  const posSet = pos ? (POS_GROUPS[posKey!]?.length ? POS_GROUPS[posKey!] : [pos]) : undefined;
  return ds.players.filter((p) => {
    if (name && !fold(p.name).includes(name)) return false;
    if (nat && fold(p.nationality) !== nat && !(nat === "brazilian" && p.nationality === "Brazil")) return false;
    if (club && !(p.club && teamMatches(normalizeTeam(p.club), club))) return false;
    if (posSet && !posSet.includes(p.position)) return false;
    if (q.minOverall !== undefined && !(p.overall >= q.minOverall)) return false;
    return true;
  }).sort((a, b) => b.overall - a.overall || a.name.localeCompare(b.name)).slice(0, q.limit ?? 25);
}

export function formatPlayer(p: Player, i?: number): string {
  return `${i !== undefined ? `${i + 1}. ` : "- "}${p.name} - Overall: ${p.overall}, Position: ${p.position || "N/A"}, Club: ${p.club || "Free agent"}, Nationality: ${p.nationality}, Age: ${p.age}`;
}

export function playerDetail(p: Player): string {
  const top = Object.entries(p.skills).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, v]) => `${k} ${v}`).join(", ");
  return [
    `${p.name} (FIFA ID ${p.id})`,
    `- Age: ${p.age}, Nationality: ${p.nationality}`,
    `- Club: ${p.club || "Free agent"}, Position: ${p.position}, Jersey: ${p.jerseyNumber}`,
    `- Overall: ${p.overall}, Potential: ${p.potential}`,
    `- Height: ${p.height}, Weight: ${p.weight}, Preferred foot: ${p.preferredFoot}`,
    `- Value: ${p.value}, Wage: ${p.wage}`,
    `- Top attributes: ${top}`,
  ].join("\n");
}

/** Brazilian clubs = teams appearing in Brasileirão data. Summarize FIFA players at those clubs (cross-file query). */
export function brazilianClubPlayers(ds: Dataset, opts: { brazilianOnly?: boolean } = {}) {
  const clubs = new Set<string>();
  for (const l of ds.serieA.values()) for (const m of l) { clubs.add(m.homeKey); clubs.add(m.awayKey); }
  const byClub = new Map<string, Player[]>();
  for (const p of ds.players) {
    if (!p.club || !clubs.has(normalizeTeam(p.club))) continue;
    if (opts.brazilianOnly && p.nationality !== "Brazil") continue;
    (byClub.get(p.club) ?? byClub.set(p.club, []).get(p.club)!).push(p);
  }
  return [...byClub.entries()].map(([club, ps]) => ({
    club, count: ps.length, avgOverall: Math.round(ps.reduce((s, p) => s + p.overall, 0) / ps.length),
    best: ps.sort((a, b) => b.overall - a.overall)[0],
  })).sort((a, b) => b.avgOverall - a.avgOverall || b.count - a.count);
}
