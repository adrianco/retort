import { Dataset, Match, Player, Competition, displayName, teamMatches, normalizeTeam, stripAccents } from "./data.js";

export interface MatchFilter {
  team?: string;
  opponent?: string;
  venue?: "home" | "away" | "any";
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  stage?: string;
}

const COMP_ALIASES: Record<string, Competition> = {
  brasileirao: "Brasileirão", "serie a": "Brasileirão", "campeonato brasileiro": "Brasileirão", brasileiro: "Brasileirão",
  "copa do brasil": "Copa do Brasil", "brazilian cup": "Copa do Brasil", cup: "Copa do Brasil",
  libertadores: "Libertadores", "copa libertadores": "Libertadores",
  "serie b": "Serie B", "serie c": "Serie C",
};

export function normalizeCompetition(c?: string): Competition | undefined {
  if (!c) return undefined;
  const k = stripAccents(c).toLowerCase().trim();
  return COMP_ALIASES[k] ?? (Object.entries(COMP_ALIASES).find(([a]) => k.includes(a))?.[1]);
}

/** Deduplicate the same fixture reported by multiple files (same date + teams). */
export function dedupe(ms: Match[]): Match[] {
  const seen = new Map<string, Match>();
  for (const m of ms) {
    const k = `${m.date}|${m.homeKey}|${m.awayKey}`;
    const prev = seen.get(k);
    if (!prev || (!prev.round && !prev.stage && (m.round || m.stage))) seen.set(k, m);
  }
  return [...seen.values()];
}

export class SoccerService {
  constructor(public ds: Dataset) {}

  filterMatches(f: MatchFilter): Match[] {
    const comp = normalizeCompetition(f.competition);
    if (f.competition && !comp) return [];
    const out = this.ds.matches.filter((m) => {
      if (comp && m.competition !== comp) return false;
      if (f.season && m.season !== f.season) return false;
      if (f.dateFrom && m.date < f.dateFrom) return false;
      if (f.dateTo && m.date > f.dateTo) return false;
      if (f.stage) {
        const s = f.stage.toLowerCase();
        if (!(m.stage ?? "").toLowerCase().startsWith(s) && (m.round ?? "") !== f.stage) return false;
      }
      if (f.team) {
        const h = teamMatches(m.homeKey, f.team), a = teamMatches(m.awayKey, f.team);
        const venue = f.venue ?? "any";
        if (venue === "home" ? !h : venue === "away" ? !a : !(h || a)) return false;
        if (f.opponent) {
          const other = h ? m.awayKey : m.homeKey;
          if (!teamMatches(other, f.opponent) && !(a && teamMatches(m.homeKey, f.opponent))) return false;
        }
      } else if (f.opponent && !teamMatches(m.homeKey, f.opponent) && !teamMatches(m.awayKey, f.opponent)) return false;
      return true;
    });
    return dedupe(out).sort((a, b) => b.date.localeCompare(a.date));
  }

  /** Preferred single source for league-table calculations, avoiding double counting. */
  leagueMatches(season: number, competition: Competition = "Brasileirão"): Match[] {
    const all = this.ds.matches.filter((m) => m.season === season && m.competition === competition);
    if (competition !== "Brasileirão") return dedupe(all);
    // Use one primary source per season; fill fixtures missing from it (e.g. rows with NA scores)
    // from the other files, matching by home/away pair (each pair meets once per venue per season).
    const sources = ["Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv"];
    const primary = sources.find((src) => all.some((m) => m.source === src));
    if (!primary) return [];
    const out = all.filter((m) => m.source === primary);
    const teams = new Set(out.flatMap((m) => [m.homeKey, m.awayKey]));
    const pairs = new Set(out.map((m) => `${m.homeKey}|${m.awayKey}`));
    for (const m of all) {
      const k = `${m.homeKey}|${m.awayKey}`;
      if (m.source !== primary && teams.has(m.homeKey) && teams.has(m.awayKey) && !pairs.has(k)) { pairs.add(k); out.push(m); }
    }
    return out;
  }

  standings(season: number, competition: Competition = "Brasileirão"): Row[] {
    return table(this.leagueMatches(season, competition));
  }

  teamRecord(team: string, f: MatchFilter = {}): Record_ {
    const ms = f.season && normalizeCompetition(f.competition) === "Brasileirão" && !f.dateFrom && !f.dateTo
      ? this.leagueMatches(f.season).filter((m) => {
          const h = teamMatches(m.homeKey, team), a = teamMatches(m.awayKey, team);
          return f.venue === "home" ? h : f.venue === "away" ? a : h || a;
        })
      : this.filterMatches({ ...f, team });
    return record(ms, team);
  }

  headToHead(a: string, b: string, f: MatchFilter = {}) {
    const ms = this.filterMatches({ ...f, team: a, opponent: b });
    let aw = 0, bw = 0, d = 0, ag = 0, bg = 0;
    for (const m of ms) {
      const aHome = teamMatches(m.homeKey, a);
      const [ga, gb] = aHome ? [m.homeGoals, m.awayGoals] : [m.awayGoals, m.homeGoals];
      ag += ga; bg += gb;
      if (ga > gb) aw++; else if (gb > ga) bw++; else d++;
    }
    return { matches: ms, aWins: aw, bWins: bw, draws: d, aGoals: ag, bGoals: bg };
  }

  biggestWins(f: MatchFilter = {}, limit = 10): Match[] {
    return this.filterMatches(f)
      .sort((x, y) => Math.abs(y.homeGoals - y.awayGoals) - Math.abs(x.homeGoals - x.awayGoals) || (y.homeGoals + y.awayGoals) - (x.homeGoals + x.awayGoals))
      .slice(0, limit);
  }

  aggregateStats(f: MatchFilter = {}) {
    const ms = this.filterMatches(f);
    const n = ms.length;
    const goals = ms.reduce((s, m) => s + m.homeGoals + m.awayGoals, 0);
    const hw = ms.filter((m) => m.homeGoals > m.awayGoals).length;
    const aw = ms.filter((m) => m.homeGoals < m.awayGoals).length;
    return {
      matches: n, totalGoals: goals, avgGoals: n ? goals / n : 0,
      homeWinRate: n ? hw / n : 0, awayWinRate: n ? aw / n : 0, drawRate: n ? (n - hw - aw) / n : 0,
    };
  }

  /** Rank teams by win rate at a venue (home/away/any) over a filtered set of matches. */
  bestRecords(venue: "home" | "away" | "any", f: MatchFilter = {}, minMatches = 10, limit = 10) {
    const ms = this.filterMatches(f);
    const keys = new Set<string>();
    for (const m of ms) { keys.add(m.homeKey); keys.add(m.awayKey); }
    const rows = [...keys].map((k) => {
      const sub = ms.filter((m) => venue === "home" ? m.homeKey === k : venue === "away" ? m.awayKey === k : m.homeKey === k || m.awayKey === k);
      return recordByKey(sub, k);
    }).filter((r) => r.played >= minMatches);
    return rows.sort((a, b) => b.winRate - a.winRate || b.played - a.played).slice(0, limit);
  }

  teamCompetitions(team: string) {
    const ms = this.filterMatches({ team });
    const by: Record<string, { matches: number; seasons: Set<number> }> = {};
    for (const m of ms) {
      by[m.competition] ??= { matches: 0, seasons: new Set() };
      by[m.competition].matches++;
      by[m.competition].seasons.add(m.season);
    }
    return Object.entries(by).map(([competition, v]) => ({ competition, matches: v.matches, seasons: [...v.seasons].sort() }));
  }

  derbies(f: MatchFilter = {}): Match[] {
    return this.filterMatches(f).filter((m) => derbyName(m.homeKey, m.awayKey));
  }

  searchPlayers(q: { name?: string; nationality?: string; club?: string; position?: string; minOverall?: number; maxAge?: number; limit?: number; sortBy?: "overall" | "potential" | "age" }): { total: number; players: Player[] } {
    const norm = (s: string) => stripAccents(s).toLowerCase();
    const posGroups: Record<string, string[]> = {
      forward: ["ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"],
      striker: ["ST", "CF", "LS", "RS"],
      midfielder: ["CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"],
      defender: ["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"],
      goalkeeper: ["GK"],
    };
    let positions: string[] | undefined;
    if (q.position) {
      const p = q.position.toLowerCase().replace(/s$/, "");
      positions = posGroups[p] ?? q.position.toUpperCase().split(/[,\s]+/);
    }
    const clubQ = q.club ? normalizeTeam(q.club) : undefined;
    const res = this.ds.players.filter((p) => {
      if (q.name) {
        const n = norm(p.name), qq = norm(q.name);
        if (!n.includes(qq) && !qq.split(/\s+/).every((t) => n.includes(t))) return false;
      }
      if (q.nationality && norm(p.nationality) !== norm(q.nationality)) return false;
      if (clubQ !== undefined) {
        if (!p.club) return false;
        const pk = normalizeTeam(p.club);
        if (pk !== clubQ && !norm(p.club).includes(norm(q.club!)) && pk.split("-")[0] !== clubQ) return false;
      }
      if (positions && !positions.includes(p.position)) return false;
      if (q.minOverall && p.overall < q.minOverall) return false;
      if (q.maxAge && p.age > q.maxAge) return false;
      return true;
    });
    const key = q.sortBy ?? "overall";
    res.sort((a, b) => key === "age" ? a.age - b.age : (b[key] - a[key]) || a.name.localeCompare(b.name));
    return { total: res.length, players: res.slice(0, q.limit ?? 20) };
  }

  /** Clubs with the most players of a nationality, with average rating. */
  playersByClub(nationality = "Brazil", limit = 15) {
    const by = new Map<string, Player[]>();
    for (const p of this.ds.players) if (p.nationality === nationality && p.club) {
      if (!by.has(p.club)) by.set(p.club, []);
      by.get(p.club)!.push(p);
    }
    return [...by.entries()]
      .map(([club, ps]) => ({ club, count: ps.length, avgOverall: ps.reduce((s, p) => s + p.overall, 0) / ps.length }))
      .sort((a, b) => b.count - a.count || b.avgOverall - a.avgOverall)
      .slice(0, limit);
  }

  listTeams(query?: string) {
    const counts = new Map<string, number>();
    for (const m of dedupe(this.ds.matches)) for (const k of [m.homeKey, m.awayKey]) counts.set(k, (counts.get(k) ?? 0) + 1);
    const q = query ? stripAccents(query).toLowerCase() : undefined;
    return [...counts.entries()]
      .filter(([k]) => !q || k.includes(q) || stripAccents(displayName(k)).toLowerCase().includes(q))
      .map(([key, matches]) => ({ key, name: displayName(key), matches }))
      .sort((a, b) => b.matches - a.matches);
  }
}

export interface Row { team: string; key: string; played: number; wins: number; draws: number; losses: number; gf: number; ga: number; gd: number; points: number }
export interface Record_ extends Row { winRate: number; matches: Match[] }

export function table(ms: Match[]): Row[] {
  const rows = new Map<string, Row>();
  const get = (k: string) => {
    if (!rows.has(k)) rows.set(k, { team: displayName(k), key: k, played: 0, wins: 0, draws: 0, losses: 0, gf: 0, ga: 0, gd: 0, points: 0 });
    return rows.get(k)!;
  };
  for (const m of ms) {
    const h = get(m.homeKey), a = get(m.awayKey);
    h.played++; a.played++;
    h.gf += m.homeGoals; h.ga += m.awayGoals; a.gf += m.awayGoals; a.ga += m.homeGoals;
    if (m.homeGoals > m.awayGoals) { h.wins++; a.losses++; h.points += 3; }
    else if (m.homeGoals < m.awayGoals) { a.wins++; h.losses++; a.points += 3; }
    else { h.draws++; a.draws++; h.points++; a.points++; }
  }
  for (const r of rows.values()) r.gd = r.gf - r.ga;
  return [...rows.values()].sort((a, b) => b.points - a.points || b.wins - a.wins || b.gd - a.gd || b.gf - a.gf);
}

function recordByKey(ms: Match[], key: string): Record_ {
  return record(ms, key, (k) => k === key);
}

function record(ms: Match[], team: string, is: (k: string) => boolean = (k) => teamMatches(k, team)): Record_ {
  const r: Record_ = { team: displayName(normalizeTeam(team)), key: normalizeTeam(team), played: 0, wins: 0, draws: 0, losses: 0, gf: 0, ga: 0, gd: 0, points: 0, winRate: 0, matches: ms };
  if (ms.length) {
    const k = is(ms[0].homeKey) ? ms[0].homeKey : ms[0].awayKey;
    r.key = k; r.team = displayName(k);
  }
  for (const m of ms) {
    const home = is(m.homeKey);
    const [f, a] = home ? [m.homeGoals, m.awayGoals] : [m.awayGoals, m.homeGoals];
    r.played++; r.gf += f; r.ga += a;
    if (f > a) { r.wins++; r.points += 3; } else if (f < a) r.losses++; else { r.draws++; r.points++; }
  }
  r.gd = r.gf - r.ga;
  r.winRate = r.played ? r.wins / r.played : 0;
  return r;
}

const DERBIES: [string, string, string][] = [
  ["flamengo", "fluminense", "Fla-Flu"],
  ["flamengo", "vasco", "Clássico dos Milhões"],
  ["flamengo", "botafogo-rj", "Clássico da Rivalidade"],
  ["fluminense", "vasco", "Clássico dos Gigantes"],
  ["botafogo-rj", "fluminense", "Clássico Vovô"],
  ["botafogo-rj", "vasco", "Clássico da Amizade"],
  ["corinthians", "palmeiras", "Derby Paulista"],
  ["corinthians", "sao paulo", "Majestoso"],
  ["palmeiras", "sao paulo", "Choque-Rei"],
  ["santos", "corinthians", "Clássico Alvinegro"],
  ["santos", "palmeiras", "Clássico da Saudade"],
  ["santos", "sao paulo", "San-São"],
  ["gremio", "internacional-rs", "Gre-Nal"],
  ["atletico-mg", "cruzeiro", "Clássico Mineiro"],
  ["bahia", "vitoria", "Ba-Vi"],
  ["athletico-pr", "coritiba", "Atletiba"],
  ["ceara", "fortaleza", "Clássico-Rei"],
  ["sport", "nautico", "Clássico dos Clássicos"],
  ["sport", "santa cruz", "Clássico das Multidões"],
  ["goias", "vila nova", "Clássico Goiano"],
];

export function derbyName(a: string, b: string): string | undefined {
  return DERBIES.find(([x, y]) => (x === a && y === b) || (x === b && y === a))?.[2];
}

// ---------- Formatting ----------

export function fmtMatch(m: Match): string {
  const ctx = [m.competition, m.round && m.competition !== "Libertadores" ? `Round ${m.round}` : undefined, m.stage].filter(Boolean).join(" ");
  return `${m.date}: ${displayName(m.homeKey)} ${m.homeGoals}-${m.awayGoals} ${displayName(m.awayKey)} (${ctx}${m.season ? ", " + m.season : ""})`;
}

export function fmtMatches(ms: Match[], limit = 20): string {
  if (!ms.length) return "No matches found.";
  const lines = ms.slice(0, limit).map((m) => "- " + fmtMatch(m));
  if (ms.length > limit) lines.push(`- ... (${ms.length - limit} more matches in dataset)`);
  return lines.join("\n");
}

export function fmtRecord(title: string, r: Row & { winRate?: number }): string {
  const wr = r.played ? (r.wins / r.played) * 100 : 0;
  return [
    `${title}:`,
    `- Matches: ${r.played}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.gf}, Goals Against: ${r.ga}`,
    `- Points: ${r.points}`,
    `- Win rate: ${wr.toFixed(1)}%`,
  ].join("\n");
}

export function fmtStandings(title: string, rows: Row[], limit = 40): string {
  const lines = rows.slice(0, limit).map((r, i) =>
    `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, GF ${r.gf}, GA ${r.ga}, GD ${r.gd >= 0 ? "+" : ""}${r.gd})${i === 0 ? " - Champion" : ""}`);
  return `${title}\n${lines.join("\n")}`;
}

export function fmtPlayer(p: Player, i?: number): string {
  return `${i !== undefined ? `${i + 1}. ` : "- "}${p.name} - Overall: ${p.overall}, Potential: ${p.potential}, Position: ${p.position || "?"}, Age: ${p.age}, Nationality: ${p.nationality}, Club: ${p.club || "Free agent"}`;
}
