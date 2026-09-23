import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { parseCsv } from "./csv.js";
import { displayTeam, normalizeTeam, parseDate } from "./normalize.js";

export type Competition = "Brasileirão Série A" | "Brasileirão Série B" | "Brasileirão Série C" | "Copa do Brasil" | "Copa Libertadores";

export interface Match {
  date: string; // YYYY-MM-DD
  season: number;
  competition: Competition;
  round?: string; // round number or stage
  home: string; away: string; // display names
  homeKey: string; awayKey: string; // normalized
  homeGoals: number; awayGoals: number;
  arena?: string;
  stats?: { homeCorners?: number; awayCorners?: number; homeShots?: number; awayShots?: number; homeAttacks?: number; awayAttacks?: number };
  source: string;
}

export interface Player {
  id: string; name: string; age: number; nationality: string; overall: number; potential: number;
  club: string; position: string; jerseyNumber: string; height: string; weight: string;
  preferredFoot: string; value: string; wage: string;
  skills: Record<string, number>;
}

export interface Dataset {
  matches: Match[];
  players: Player[];
  /** One authoritative list of Série A matches per season (avoids double counting overlapping files). */
  serieA: Map<number, Match[]>;
  fileCounts: Record<string, number>;
}

const num = (s: string | undefined) => { const n = Number(s); return Number.isFinite(n) ? n : NaN; };
const opt = (s: string | undefined) => { const n = parseFloat(s ?? ""); return Number.isFinite(n) ? n : undefined; };

function mk(p: Omit<Match, "homeKey" | "awayKey" | "home" | "away"> & { homeRaw: string; awayRaw: string }): Match {
  const { homeRaw, awayRaw, ...rest } = p;
  const homeKey = normalizeTeam(homeRaw), awayKey = normalizeTeam(awayRaw);
  return { ...rest, home: label(homeRaw, homeKey), away: label(awayRaw, awayKey), homeKey, awayKey };
}

/** Display name; ambiguous clubs (e.g. Atlético-MG vs Atlético-GO) keep a state suffix. */
function label(raw: string, key: string): string {
  const d = displayTeam(raw);
  const st = key.match(/-([a-z]{2,3})$/);
  if (!st || /(mineiro|paranaense|goianiense|natal)/i.test(d)) return d;
  return `${d}-${st[1].toUpperCase()}`;
}

const SKILLS = ["Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes"];

export function defaultDataDir(): string {
  return join(dirname(fileURLToPath(import.meta.url)), "..", "data", "kaggle");
}

export function loadDataset(dir = defaultDataDir()): Dataset {
  const read = (f: string) => parseCsv(readFileSync(join(dir, f), "utf8"));
  const fileCounts: Record<string, number> = {};
  const matches: Match[] = [];
  const valid = (m: Match) => m.date !== "" && !Number.isNaN(m.homeGoals) && !Number.isNaN(m.awayGoals);
  const push = (file: string, list: Match[]) => {
    const ok = list.filter(valid);
    fileCounts[file] = ok.length;
    matches.push(...ok);
    return ok;
  };

  const bra = push("Brasileirao_Matches.csv", read("Brasileirao_Matches.csv").map((r) => mk({
    date: parseDate(r.datetime), season: num(r.season), competition: "Brasileirão Série A", round: r.round,
    homeRaw: r.home_team, awayRaw: r.away_team, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), source: "Brasileirao_Matches.csv",
  })));
  push("Brazilian_Cup_Matches.csv", read("Brazilian_Cup_Matches.csv").map((r) => mk({
    date: parseDate(r.datetime), season: num(r.season), competition: "Copa do Brasil", round: r.round,
    homeRaw: r.home_team, awayRaw: r.away_team, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), source: "Brazilian_Cup_Matches.csv",
  })));
  push("Libertadores_Matches.csv", read("Libertadores_Matches.csv").map((r) => {
    const date = parseDate(r.datetime);
    return mk({
      date, season: Number.isFinite(num(r.season)) && r.season !== "" ? num(r.season) : Number(date.slice(0, 4)),
      competition: "Copa Libertadores", round: r.stage,
      homeRaw: r.home_team, awayRaw: r.away_team, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), source: "Libertadores_Matches.csv",
    });
  }));
  const tour: Record<string, Competition> = { "Serie A": "Brasileirão Série A", "Serie B": "Brasileirão Série B", "Serie C": "Brasileirão Série C", "Copa do Brasil": "Copa do Brasil" };
  push("BR-Football-Dataset.csv", read("BR-Football-Dataset.csv").filter((r) => tour[r.tournament]).map((r) => {
    const date = parseDate(r.date);
    return mk({
      date, season: Number(date.slice(0, 4)), competition: tour[r.tournament],
      homeRaw: r.home, awayRaw: r.away, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), source: "BR-Football-Dataset.csv",
      stats: { homeCorners: opt(r.home_corner), awayCorners: opt(r.away_corner), homeShots: opt(r.home_shots), awayShots: opt(r.away_shots), homeAttacks: opt(r.home_attack), awayAttacks: opt(r.away_attack) },
    });
  }));
  const hist = push("novo_campeonato_brasileiro.csv", read("novo_campeonato_brasileiro.csv").map((r) => mk({
    date: parseDate(r.Data), season: num(r.Ano), competition: "Brasileirão Série A", round: r.Rodada,
    homeRaw: r.Equipe_mandante, awayRaw: r.Equipe_visitante, homeGoals: num(r.Gols_mandante), awayGoals: num(r.Gols_visitante),
    arena: r.Arena || undefined, source: "novo_campeonato_brasileiro.csv",
  })));

  // Authoritative Série A per season: the most complete file (ties: Brasileirao_Matches > historical > BR-Football)
  const serieA = new Map<number, Match[]>();
  const add = (list: Match[]) => {
    const bySeason = new Map<number, Match[]>();
    for (const m of list) (bySeason.get(m.season) ?? bySeason.set(m.season, []).get(m.season)!).push(m);
    for (const [s, l] of bySeason) if (l.length > (serieA.get(s)?.length ?? 0)) serieA.set(s, l);
  };
  add(bra); add(hist);
  add(matches.filter((m) => m.source === "BR-Football-Dataset.csv" && m.competition === "Brasileirão Série A"));

  const players: Player[] = read("fifa_data.csv").filter((r) => r.Name).map((r) => ({
    id: r.ID, name: r.Name, age: num(r.Age), nationality: r.Nationality, overall: num(r.Overall), potential: num(r.Potential),
    club: r.Club, position: r.Position, jerseyNumber: r["Jersey Number"], height: r.Height, weight: r.Weight,
    preferredFoot: r["Preferred Foot"], value: r.Value, wage: r.Wage,
    skills: Object.fromEntries(SKILLS.filter((k) => r[k] !== undefined && r[k] !== "").map((k) => [k, num(r[k])])),
  }));
  fileCounts["fifa_data.csv"] = players.length;

  return { matches, players, serieA, fileCounts };
}
