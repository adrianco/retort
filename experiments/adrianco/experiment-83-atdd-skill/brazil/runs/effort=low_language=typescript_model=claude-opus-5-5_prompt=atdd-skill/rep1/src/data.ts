import fs from "node:fs";
import path from "node:path";
import { parse } from "csv-parse/sync";
import { registerDisplay } from "./teams.js";

export interface Match {
  date: string; // ISO yyyy-mm-dd
  time?: string;
  season: number;
  competition: string; // Brasileirão | Serie B | Serie C | Copa do Brasil | Libertadores
  round?: string;
  stage?: string;
  home: string; // canonical team key
  away: string;
  homeGoals: number;
  awayGoals: number;
  arena?: string;
  source: string;
  stats?: { homeCorners?: number; awayCorners?: number; homeShots?: number; awayShots?: number; homeAttacks?: number; awayAttacks?: number };
}

export interface Player {
  id: string; name: string; age: number; nationality: string; overall: number; potential: number;
  club: string; position: string; jersey: string; height: string; weight: string; foot: string; value: string;
  skills: Record<string, number>;
}

export interface Dataset { matches: Match[]; players: Player[]; files: Record<string, number>; league: Match[]; seasonSources: Map<number, string> }

export function parseDate(raw: string): { date: string; time?: string } | undefined {
  const s = (raw ?? "").trim();
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2}))?/);
  if (m) return { date: `${m[1]}-${m[2]}-${m[3]}`, time: m[4] };
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return { date: `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}` };
  return undefined;
}

const num = (v: string) => { const n = parseFloat(v); return Number.isFinite(n) ? n : NaN; };

function read(dir: string, file: string): Record<string, string>[] {
  const text = fs.readFileSync(path.join(dir, file), "utf8").replace(/^﻿/, "");
  return parse(text, { columns: true, skip_empty_lines: true, relax_column_count: true });
}

const SKILLS = ["Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve", "FKAccuracy",
  "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance", "ShotPower", "Jumping",
  "Stamina", "Strength", "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
  "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes"];

export function loadDataset(dir = path.resolve(import.meta.dirname, "../data/kaggle")): Dataset {
  const files: Record<string, number> = {};
  const raw: Match[] = [];
  const push = (m: Partial<Match> & { rawHome: string; rawAway: string; rawDate: string }) => {
    const d = parseDate(m.rawDate);
    const hg = num(String(m.homeGoals)), ag = num(String(m.awayGoals));
    if (!d || Number.isNaN(hg) || Number.isNaN(ag) || !m.rawHome || !m.rawAway) return;
    const { rawHome, rawAway, rawDate, ...rest } = m;
    raw.push({ ...rest, date: d.date, time: m.time ?? d.time, season: m.season && !Number.isNaN(m.season) ? m.season : +d.date.slice(0, 4),
      home: registerDisplay(rawHome), away: registerDisplay(rawAway), homeGoals: hg, awayGoals: ag } as Match);
  };

  let rows = read(dir, "Brasileirao_Matches.csv"); files["Brasileirao_Matches.csv"] = rows.length;
  for (const r of rows) push({ rawDate: r.datetime, rawHome: r.home_team, rawAway: r.away_team, homeGoals: +r.home_goal, awayGoals: +r.away_goal,
    season: +r.season, round: r.round, competition: "Brasileirão", source: "Brasileirao_Matches.csv" });

  rows = read(dir, "novo_campeonato_brasileiro.csv"); files["novo_campeonato_brasileiro.csv"] = rows.length;
  for (const r of rows) push({ rawDate: r.Data, rawHome: r.Equipe_mandante, rawAway: r.Equipe_visitante, homeGoals: +r.Gols_mandante,
    awayGoals: +r.Gols_visitante, season: +r.Ano, round: r.Rodada, arena: r.Arena || undefined, competition: "Brasileirão", source: "novo_campeonato_brasileiro.csv" });

  rows = read(dir, "Brazilian_Cup_Matches.csv"); files["Brazilian_Cup_Matches.csv"] = rows.length;
  const maxCupRound = new Map<number, number>();
  for (const r of rows) maxCupRound.set(+r.season, Math.max(maxCupRound.get(+r.season) ?? 0, +r.round || 0));
  for (const r of rows) push({ rawDate: r.datetime, rawHome: r.home_team, rawAway: r.away_team, homeGoals: +r.home_goal, awayGoals: +r.away_goal,
    season: +r.season, round: r.round, stage: +r.round === maxCupRound.get(+r.season) ? "final" : `round ${r.round}`,
    competition: "Copa do Brasil", source: "Brazilian_Cup_Matches.csv" });

  rows = read(dir, "Libertadores_Matches.csv"); files["Libertadores_Matches.csv"] = rows.length;
  for (const r of rows) push({ rawDate: r.datetime, rawHome: r.home_team, rawAway: r.away_team, homeGoals: +r.home_goal, awayGoals: +r.away_goal,
    season: +r.season, stage: r.stage, competition: "Libertadores", source: "Libertadores_Matches.csv" });

  rows = read(dir, "BR-Football-Dataset.csv"); files["BR-Football-Dataset.csv"] = rows.length;
  for (const r of rows) push({ rawDate: r.date, rawHome: r.home, rawAway: r.away, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal),
    time: r.time?.slice(0, 5), competition: r.tournament === "Serie A" ? "Brasileirão" : r.tournament, source: "BR-Football-Dataset.csv",
    stats: { homeCorners: num(r.home_corner), awayCorners: num(r.away_corner), homeShots: num(r.home_shots), awayShots: num(r.away_shots),
      homeAttacks: num(r.home_attack), awayAttacks: num(r.away_attack) } });

  // Deduplicate overlapping sources: same date + same teams = same match (first source wins, extra stats merged).
  const byKey = new Map<string, Match>();
  for (const m of raw) {
    const key = `${m.date}|${m.home}|${m.away}`;
    const prev = byKey.get(key);
    if (!prev) byKey.set(key, m);
    else if (m.stats && !prev.stats) prev.stats = m.stats;
  }
  const matches = [...byKey.values()].sort((a, b) => b.date.localeCompare(a.date));

  // Which single source to trust for complete league tables per season.
  const seasonSources = new Map<number, string>();
  for (const src of ["Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv"])
    for (const m of raw) if (m.competition === "Brasileirão" && m.source === src && !seasonSources.has(m.season)) seasonSources.set(m.season, src);
  const fullBySeason = raw.filter(m => m.competition === "Brasileirão" && seasonSources.get(m.season) === m.source);
  // Fill fixtures the preferred source lacks (e.g. NA scores) from other sources: each pairing occurs once per season.
  const seen = new Set(fullBySeason.map(m => `${m.season}|${m.home}|${m.away}`));
  const seasonTeams = new Set(fullBySeason.flatMap(m => [`${m.season}|${m.home}`, `${m.season}|${m.away}`]));
  for (const m of raw) {
    const key = `${m.season}|${m.home}|${m.away}`;
    if (m.competition === "Brasileirão" && seasonSources.get(m.season) !== m.source && !seen.has(key) && seasonTeams.has(`${m.season}|${m.home}`) && seasonTeams.has(`${m.season}|${m.away}`)) {
      seen.add(key); fullBySeason.push(m);
    }
  }

  const prow = read(dir, "fifa_data.csv"); files["fifa_data.csv"] = prow.length;
  const players: Player[] = prow.filter(r => r.Name).map(r => ({
    id: r.ID, name: r.Name, age: +r.Age, nationality: r.Nationality, overall: +r.Overall, potential: +r.Potential,
    club: r.Club ?? "", position: r.Position ?? "", jersey: r["Jersey Number"] ?? "", height: r.Height ?? "", weight: r.Weight ?? "",
    foot: r["Preferred Foot"] ?? "", value: r.Value ?? "",
    skills: Object.fromEntries(SKILLS.filter(k => r[k] !== undefined && r[k] !== "").map(k => [k, +r[k]])),
  }));

  return { matches, league: fullBySeason, players, files, seasonSources };
}

