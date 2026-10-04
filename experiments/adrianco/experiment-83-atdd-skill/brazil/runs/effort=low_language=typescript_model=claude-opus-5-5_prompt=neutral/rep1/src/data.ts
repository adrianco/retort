/** Loads all six Kaggle CSV files into normalized in-memory structures. */
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { parseCsv } from "./csv.js";
import { displayName, parseDate, teamKey } from "./normalize.js";

export type Competition = "Brasileirão" | "Copa do Brasil" | "Libertadores" | "Serie B" | "Serie C";

export interface Match {
  date: string; // ISO YYYY-MM-DD
  season: number;
  competition: Competition;
  home: string;
  away: string;
  homeKey: string;
  awayKey: string;
  homeGoals: number;
  awayGoals: number;
  round?: string;
  stage?: string;
  arena?: string;
  source: string;
  stats?: { homeCorners?: number; awayCorners?: number; homeShots?: number; awayShots?: number; homeAttacks?: number; awayAttacks?: number };
}

export interface Player {
  id: number;
  name: string;
  nameKey: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  clubKey: string;
  position: string;
  jersey: string;
  height: string;
  weight: string;
  value: string;
  wage: string;
  preferredFoot: string;
  skills: Record<string, number>;
}

export interface Dataset {
  matches: Match[]; // deduplicated across sources
  allMatches: Match[]; // every row from every file
  players: Player[];
  bySource: Record<string, number>;
}

const SKILLS = ["Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes"];

export function defaultDataDir(): string {
  if (process.env.SOCCER_DATA_DIR) return process.env.SOCCER_DATA_DIR;
  const here = dirname(fileURLToPath(import.meta.url));
  return join(here, "..", "..", "data", "kaggle"); // dist/src -> project root
}

const num = (s: string | undefined) => {
  const n = parseFloat(s ?? "");
  return Number.isFinite(n) ? n : NaN;
};

function mk(m: Omit<Match, "homeKey" | "awayKey" | "home" | "away"> & { home: string; away: string }): Match {
  return { ...m, home: displayName(m.home), away: displayName(m.away), homeKey: teamKey(m.home), awayKey: teamKey(m.away) };
}

export function loadDataset(dir = defaultDataDir()): Dataset {
  const read = (f: string) => parseCsv(readFileSync(join(dir, f), "utf8"));
  const bySource: Record<string, number> = {};
  const all: Match[] = [];
  const push = (src: string, m: Match) => {
    if (!m.date || isNaN(m.homeGoals) || isNaN(m.awayGoals)) return;
    all.push(m);
    bySource[src] = (bySource[src] ?? 0) + 1;
  };

  for (const r of read("Brasileirao_Matches.csv"))
    push("Brasileirao_Matches.csv", mk({ date: parseDate(r.datetime), season: +r.season, competition: "Brasileirão", home: r.home_team, away: r.away_team, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), round: r.round, source: "Brasileirao_Matches.csv" }));
  for (const r of read("novo_campeonato_brasileiro.csv"))
    push("novo_campeonato_brasileiro.csv", mk({ date: parseDate(r.Data), season: +r.Ano, competition: "Brasileirão", home: r.Equipe_mandante, away: r.Equipe_visitante, homeGoals: num(r.Gols_mandante), awayGoals: num(r.Gols_visitante), round: r.Rodada, arena: r.Arena || undefined, source: "novo_campeonato_brasileiro.csv" }));
  for (const r of read("Brazilian_Cup_Matches.csv"))
    push("Brazilian_Cup_Matches.csv", mk({ date: parseDate(r.datetime), season: +r.season, competition: "Copa do Brasil", home: r.home_team, away: r.away_team, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), round: r.round, source: "Brazilian_Cup_Matches.csv" }));
  for (const r of read("Libertadores_Matches.csv"))
    push("Libertadores_Matches.csv", mk({ date: parseDate(r.datetime), season: +r.season, competition: "Libertadores", home: r.home_team, away: r.away_team, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), stage: r.stage, source: "Libertadores_Matches.csv" }));
  const tmap: Record<string, Competition> = { "Serie A": "Brasileirão", "Serie B": "Serie B", "Serie C": "Serie C", "Copa do Brasil": "Copa do Brasil" };
  for (const r of read("BR-Football-Dataset.csv")) {
    const date = parseDate(r.date);
    push("BR-Football-Dataset.csv", mk({
      date, season: +date.slice(0, 4), competition: tmap[r.tournament] ?? (r.tournament as Competition), home: r.home, away: r.away,
      homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), source: "BR-Football-Dataset.csv",
      stats: { homeCorners: num(r.home_corner), awayCorners: num(r.away_corner), homeShots: num(r.home_shots), awayShots: num(r.away_shots), homeAttacks: num(r.home_attack), awayAttacks: num(r.away_attack) },
    }));
  }

  // Deduplicate overlapping sources (same competition, date, teams). Earlier sources win,
  // but extended stats from BR-Football are merged in.
  // Two rows are the same match if competition, date and score agree and at least one team key agrees
  // (handles spelling variants like "4 de Julho" vs "4 de Julho EC").
  const seen = new Map<string, Match[]>();
  const matches: Match[] = [];
  for (const m of all) {
    const k = `${m.competition}|${m.date}|${m.homeGoals}|${m.awayGoals}`;
    const list = seen.get(k) ?? [];
    const prev = list.find((p) => p.homeKey === m.homeKey || p.awayKey === m.awayKey);
    if (prev) {
      if (!prev.stats && m.stats) prev.stats = m.stats;
      continue;
    }
    const copy = { ...m };
    list.push(copy);
    seen.set(k, list);
    matches.push(copy);
  }
  // Copa do Brasil rounds are numeric; label the last round of each season as the final.
  const lastRound = new Map<number, number>();
  for (const m of matches) if (m.source === "Brazilian_Cup_Matches.csv") lastRound.set(m.season, Math.max(lastRound.get(m.season) ?? 0, +m.round!));
  const count = new Map<string, number>();
  for (const m of matches) if (m.source === "Brazilian_Cup_Matches.csv") count.set(`${m.season}|${m.round}`, (count.get(`${m.season}|${m.round}`) ?? 0) + 1);
  for (const m of matches)
    if (m.source === "Brazilian_Cup_Matches.csv" && +m.round! === lastRound.get(m.season) && (count.get(`${m.season}|${m.round}`) ?? 0) <= 2) m.stage = "final";
  // Seasons are sometimes covered by multiple Serie A sources with different dates (e.g. rescheduled
  // rows); for standings we pick one authoritative source per season (see seasonMatches()).

  const players: Player[] = read("fifa_data.csv").map((r) => {
    const skills: Record<string, number> = {};
    for (const s of SKILLS) if (r[s]) skills[s] = num(r[s]);
    return {
      id: +r.ID, name: r.Name, nameKey: teamKey(r.Name), age: +r.Age, nationality: r.Nationality,
      overall: +r.Overall, potential: +r.Potential, club: r.Club, clubKey: r.Club ? teamKey(r.Club) : "",
      position: r.Position, jersey: r["Jersey Number"], height: r.Height, weight: r.Weight,
      value: r.Value, wage: r.Wage, preferredFoot: r["Preferred Foot"], skills,
    };
  });
  bySource["fifa_data.csv"] = players.length;
  return { matches, allMatches: all, players, bySource };
}

let cached: Dataset | undefined;
export function getDataset(): Dataset {
  return (cached ??= loadDataset());
}
