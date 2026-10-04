import type { Dataset, Match, Player } from "./data.js";
import { displayName, teamMatches, teamKey, stripAccents } from "./teams.js";

export interface MatchFilter {
  team?: string; opponent?: string; venue?: "home" | "away" | "any";
  competition?: string; season?: number; from?: string; to?: string; stage?: string;
}

const compKey = (c: string) => stripAccents(c).toLowerCase().replace(/[^a-z]/g, "");
function competitionMatches(m: Match, q: string): boolean {
  const k = compKey(q);
  const c = compKey(m.competition);
  if (["seriea", "brasileiro", "brasileirao", "campeonatobrasileiro"].includes(k)) return c === "brasileirao";
  if (k.includes("copa") && k.includes("brasil") || k === "brazilcup" || k === "cup") return c === "copadobrasil";
  if (k.includes("libertadores")) return c === "libertadores";
  return c === k;
}

export const matchView = (m: Match) => ({
  date: m.date, home: displayName(m.home), away: displayName(m.away), homeGoals: m.homeGoals, awayGoals: m.awayGoals,
  competition: m.competition, season: m.season, round: m.round, stage: m.stage, arena: m.arena,
  corners: m.corners, shots: m.shots,
});
export type MatchView = ReturnType<typeof matchView>;

export function filterMatches(ds: Dataset, f: MatchFilter): Match[] {
  return ds.matches.filter((m) => {
    if (f.competition && !competitionMatches(m, f.competition)) return false;
    if (f.season && m.season !== f.season) return false;
    if (f.from && m.date < f.from) return false;
    if (f.to && m.date > f.to) return false;
    if (f.stage && !(m.stage ?? "").toLowerCase().includes(f.stage.toLowerCase())) return false;
    if (f.team) {
      const venue = f.venue ?? "any";
      const h = teamMatches(m.home, f.team), a = teamMatches(m.away, f.team);
      if (venue === "home" ? !h : venue === "away" ? !a : !(h || a)) return false;
      if (f.opponent) {
        const oh = teamMatches(m.home, f.opponent), oa = teamMatches(m.away, f.opponent);
        if (!((h && oa) || (a && oh))) return false;
      }
    } else if (f.opponent && !(teamMatches(m.home, f.opponent) || teamMatches(m.away, f.opponent))) return false;
    return true;
  });
}

export interface Record_ {
  team: string; matches: number; wins: number; draws: number; losses: number;
  goalsFor: number; goalsAgainst: number; points: number; winRate: number;
}

export function recordFor(team: string, matches: Match[]): Record_ {
  const r = { team, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0, winRate: 0 };
  for (const m of matches) {
    const home = teamMatches(m.home, team);
    const gf = home ? m.homeGoals : m.awayGoals, ga = home ? m.awayGoals : m.homeGoals;
    r.matches++; r.goalsFor += gf; r.goalsAgainst += ga;
    if (gf > ga) r.wins++; else if (gf === ga) r.draws++; else r.losses++;
  }
  r.points = r.wins * 3 + r.draws;
  r.winRate = r.matches ? +(100 * r.wins / r.matches).toFixed(1) : 0;
  return r;
}

export function resolveTeamName(ds: Dataset, team: string): string {
  const m = ds.matches.find((x) => teamMatches(x.home, team) || teamMatches(x.away, team));
  if (m) return displayName(teamMatches(m.home, team) ? m.home : m.away);
  const p = ds.players.find((x) => x.clubKey && teamMatches(x.clubKey, team));
  return p ? p.club : team;
}

export function headToHead(ds: Dataset, team: string, opponent: string, f: MatchFilter = {}) {
  const ms = filterMatches(ds, { ...f, team, opponent });
  let w = 0, l = 0, d = 0, gf = 0, ga = 0;
  for (const m of ms) {
    const home = teamMatches(m.home, team);
    const a = home ? m.homeGoals : m.awayGoals, b = home ? m.awayGoals : m.homeGoals;
    gf += a; ga += b;
    if (a > b) w++; else if (a < b) l++; else d++;
  }
  return { team: resolveTeamName(ds, team), opponent: resolveTeamName(ds, opponent), matches: ms.length,
    teamWins: w, opponentWins: l, draws: d, teamGoals: gf, opponentGoals: ga, recent: ms.slice(0, 10).map(matchView) };
}

export function standings(ds: Dataset, season: number, competition = "Brasileirão") {
  const ms = filterMatches(ds, { season, competition });
  const table = new Map<string, Record_>();
  const get = (k: string) => {
    if (!table.has(k)) table.set(k, { team: displayName(k), matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0, winRate: 0 });
    return table.get(k)!;
  };
  for (const m of ms) {
    const h = get(m.home), a = get(m.away);
    h.matches++; a.matches++;
    h.goalsFor += m.homeGoals; h.goalsAgainst += m.awayGoals; a.goalsFor += m.awayGoals; a.goalsAgainst += m.homeGoals;
    if (m.homeGoals > m.awayGoals) { h.wins++; a.losses++; } else if (m.homeGoals < m.awayGoals) { a.wins++; h.losses++; } else { h.draws++; a.draws++; }
  }
  const rows = [...table.values()].map((r) => ({ ...r, points: r.wins * 3 + r.draws, winRate: r.matches ? +(100 * r.wins / r.matches).toFixed(1) : 0 }))
    .sort((a, b) => b.points - a.points || b.wins - a.wins || (b.goalsFor - b.goalsAgainst) - (a.goalsFor - a.goalsAgainst) || b.goalsFor - a.goalsFor);
  const relegated = rows.length >= 16 ? rows.slice(-4).map((r) => r.team) : [];
  return { season, competition, matches: ms.length, champion: rows[0]?.team, table: rows, relegated };
}

export function bracket(ds: Dataset, season: number) {
  const ms = filterMatches(ds, { season, competition: "Libertadores" }).filter((m) => m.stage && m.stage !== "group stage");
  const order = ["round of 16", "quarterfinals", "semifinals", "final"];
  const stages = order.map((s) => ({ stage: s, matches: ms.filter((m) => m.stage === s).sort((a, b) => a.date.localeCompare(b.date)).map(matchView) }))
    .filter((s) => s.matches.length);
  return { season, stages };
}

export function overview(ds: Dataset, f: MatchFilter) {
  const ms = filterMatches(ds, f);
  const goals = ms.reduce((s, m) => s + m.homeGoals + m.awayGoals, 0);
  const hw = ms.filter((m) => m.homeGoals > m.awayGoals).length, aw = ms.filter((m) => m.homeGoals < m.awayGoals).length;
  const pct = (n: number) => ms.length ? +(100 * n / ms.length).toFixed(1) : 0;
  return { filter: f, matches: ms.length, totalGoals: goals, averageGoals: ms.length ? +(goals / ms.length).toFixed(2) : 0,
    homeWinRate: pct(hw), awayWinRate: pct(aw), drawRate: pct(ms.length - hw - aw) };
}

export function biggestWins(ds: Dataset, f: MatchFilter, limit = 10) {
  return filterMatches(ds, f).slice().sort((a, b) => Math.abs(b.awayGoals - b.homeGoals) - Math.abs(a.awayGoals - a.homeGoals)
    || (b.homeGoals + b.awayGoals) - (a.homeGoals + a.awayGoals) || b.date.localeCompare(a.date)).slice(0, limit).map(matchView);
}

export function bestRecords(ds: Dataset, venue: "home" | "away" | "any", f: MatchFilter, minMatches = 10, limit = 10) {
  const ms = filterMatches(ds, { ...f, team: undefined, opponent: undefined });
  const byTeam = new Map<string, Match[]>();
  for (const m of ms) {
    if (venue !== "away") (byTeam.get(m.home) ?? byTeam.set(m.home, []).get(m.home)!).push(m);
    if (venue !== "home") (byTeam.get(m.away) ?? byTeam.set(m.away, []).get(m.away)!).push(m);
  }
  return [...byTeam.entries()].map(([k, list]) => recordForKey(k, list)).filter((r) => r.matches >= minMatches)
    .sort((a, b) => b.winRate - a.winRate || b.matches - a.matches).slice(0, limit);
}

function recordForKey(key: string, ms: Match[]): Record_ {
  const r = recordFor(key, ms.map((m) => m));
  // recordFor resolves by query match; keys are canonical so this is exact
  return { ...r, team: displayName(key) };
}

export function teamCompetitions(ds: Dataset, team: string) {
  const ms = filterMatches(ds, { team });
  const comps = new Map<string, Set<number>>();
  for (const m of ms) (comps.get(m.competition) ?? comps.set(m.competition, new Set()).get(m.competition)!).add(m.season);
  return { team: resolveTeamName(ds, team), competitions: [...comps.entries()].map(([competition, s]) => ({
    competition, matches: ms.filter((m) => m.competition === competition).length, seasons: [...s].sort() })) };
}

export interface PlayerFilter { name?: string; nationality?: string; club?: string; position?: string; minOverall?: number; }

export function searchPlayers(ds: Dataset, f: PlayerFilter): Player[] {
  const norm = (s: string) => stripAccents(s).toLowerCase();
  return ds.players.filter((p) => {
    if (f.name && !norm(p.name).includes(norm(f.name))) return false;
    if (f.nationality && norm(p.nationality) !== norm(f.nationality)) return false;
    if (f.club && !(p.clubKey && (teamMatches(p.clubKey, f.club) || norm(p.club).includes(norm(f.club))))) return false;
    if (f.position) {
      const pos = f.position.toUpperCase();
      const groups: Record<string, string[]> = {
        FORWARD: ["ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"], FORWARDS: ["ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"],
        MIDFIELDER: ["CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"],
        DEFENDER: ["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"], GOALKEEPER: ["GK"],
      };
      const allowed = groups[pos] ?? groups[pos.replace(/S$/, "")] ?? [pos];
      if (!allowed.includes(p.position)) return false;
    }
    if (f.minOverall && p.overall < f.minOverall) return false;
    return true;
  });
}

export function playersByClub(ds: Dataset, nationality: string, limit = 20) {
  const groups = new Map<string, Player[]>();
  for (const p of searchPlayers(ds, { nationality })) if (p.club) (groups.get(p.club) ?? groups.set(p.club, []).get(p.club)!).push(p);
  return [...groups.entries()].map(([club, ps]) => ({ club, players: ps.length,
    averageOverall: Math.round(ps.reduce((s, p) => s + p.overall, 0) / ps.length) }))
    .sort((a, b) => b.players - a.players || b.averageOverall - a.averageOverall).slice(0, limit);
}

export function teamProfile(ds: Dataset, team: string) {
  const ms = filterMatches(ds, { team });
  const players = searchPlayers(ds, { club: team });
  return { team: resolveTeamName(ds, team), record: recordFor(team, ms), competitions: teamCompetitions(ds, team).competitions,
    recentMatches: ms.slice(0, 5).map(matchView), players: players.slice(0, 15).map(playerView) };
}

export const playerView = (p: Player) => ({ name: p.name, age: p.age, nationality: p.nationality, overall: p.overall,
  potential: p.potential, club: p.club, position: p.position, jerseyNumber: p.jerseyNumber, height: p.height,
  weight: p.weight, value: p.value, skills: p.skills });

export { teamKey };
