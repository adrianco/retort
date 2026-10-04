import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "csv-parse/sync";
import { registerDisplay } from "./teams.js";

export type Competition = "Brasileirão" | "Copa do Brasil" | "Libertadores" | "Serie B" | "Serie C";

export interface Match {
  date: string; // ISO yyyy-mm-dd
  home: string; // canonical key
  away: string;
  homeGoals: number;
  awayGoals: number;
  competition: Competition;
  season: number;
  round?: string;
  stage?: string;
  arena?: string;
  corners?: [number, number];
  shots?: [number, number];
  source: string;
}

export interface Player {
  id: number; name: string; age: number; nationality: string; overall: number;
  potential: number; club: string; clubKey: string; position: string;
  jerseyNumber: string; height: string; weight: string; value: string;
  skills: Record<string, number>;
}

export function parseDate(s: string): string {
  s = s.trim();
  const br = s.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (br) return `${br[3]}-${br[2]}-${br[1]}`;
  const iso = s.match(/^(\d{4}-\d{2}-\d{2})/);
  return iso ? iso[1] : s;
}

function read(dir: string, file: string): Record<string, string>[] {
  const text = readFileSync(join(dir, file), "utf8").replace(/^﻿/, "");
  return parse(text, { columns: true, skip_empty_lines: true, relax_quotes: true, relax_column_count: true });
}

const num = (s: string) => Math.round(Number(s));

export interface Dataset { matches: Match[]; players: Player[]; }

export function loadDataset(dir: string): Dataset {
  const all: Match[] = [];
  const add = (m: Omit<Match, "home" | "away"> & { homeRaw: string; awayRaw: string }) => {
    const { homeRaw, awayRaw, ...rest } = m;
    if (!homeRaw || !awayRaw || Number.isNaN(m.homeGoals) || Number.isNaN(m.awayGoals)) return;
    all.push({ ...rest, home: registerDisplay(homeRaw), away: registerDisplay(awayRaw) });
  };

  for (const r of read(dir, "Brasileirao_Matches.csv"))
    add({ date: parseDate(r.datetime), homeRaw: r.home_team, awayRaw: r.away_team, homeGoals: num(r.home_goal),
      awayGoals: num(r.away_goal), competition: "Brasileirão", season: num(r.season), round: r.round, source: "Brasileirao_Matches.csv" });
  for (const r of read(dir, "Brazilian_Cup_Matches.csv"))
    add({ date: parseDate(r.datetime), homeRaw: r.home_team, awayRaw: r.away_team, homeGoals: num(r.home_goal),
      awayGoals: num(r.away_goal), competition: "Copa do Brasil", season: num(r.season), round: r.round,
      stage: r.round === "8" ? "final" : r.round === "7" ? "semifinals" : `round ${r.round}`, source: "Brazilian_Cup_Matches.csv" });
  for (const r of read(dir, "Libertadores_Matches.csv"))
    add({ date: parseDate(r.datetime), homeRaw: r.home_team, awayRaw: r.away_team, homeGoals: num(r.home_goal),
      awayGoals: num(r.away_goal), competition: "Libertadores", season: num(r.season), stage: r.stage, source: "Libertadores_Matches.csv" });
  for (const r of read(dir, "novo_campeonato_brasileiro.csv"))
    add({ date: parseDate(r.Data), homeRaw: r.Equipe_mandante, awayRaw: r.Equipe_visitante, homeGoals: num(r.Gols_mandante),
      awayGoals: num(r.Gols_visitante), competition: "Brasileirão", season: num(r.Ano), round: r.Rodada, arena: r.Arena,
      source: "novo_campeonato_brasileiro.csv" });
  const tmap: Record<string, Competition> = { "Serie A": "Brasileirão", "Copa do Brasil": "Copa do Brasil", "Serie B": "Serie B", "Serie C": "Serie C" };
  for (const r of read(dir, "BR-Football-Dataset.csv")) {
    const date = parseDate(r.date);
    add({ date, homeRaw: r.home, awayRaw: r.away, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal),
      competition: tmap[r.tournament] ?? (r.tournament as Competition), season: Number(date.slice(0, 4)),
      corners: [num(r.home_corner), num(r.away_corner)], shots: [num(r.home_shots), num(r.away_shots)], source: "BR-Football-Dataset.csv" });
  }

  // De-duplicate matches present in more than one file, merging extra stats.
  const byKey = new Map<string, Match>();
  for (const m of all) {
    // League fixtures occur once per season per venue; sources disagree on exact dates.
    const k = m.competition === "Brasileirão" ? `${m.competition}|${m.season}|${m.home}|${m.away}` : `${m.date}|${m.home}|${m.away}`;
    const prev = byKey.get(k);
    if (!prev) byKey.set(k, m);
    else byKey.set(k, { ...m, ...prev, corners: prev.corners ?? m.corners, shots: prev.shots ?? m.shots, arena: prev.arena ?? m.arena });
  }
  const matches = [...byKey.values()].sort((a, b) => b.date.localeCompare(a.date));

  const skillCols = ["Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling", "Acceleration",
    "SprintSpeed", "Stamina", "Strength", "Vision", "Composure", "StandingTackle"];
  const players: Player[] = read(dir, "fifa_data.csv").filter((r) => r.Name).map((r) => ({
    id: num(r.ID), name: r.Name, age: num(r.Age), nationality: r.Nationality, overall: num(r.Overall),
    potential: num(r.Potential), club: r.Club ?? "", clubKey: r.Club ? registerDisplay(r.Club) : "",
    position: r.Position ?? "", jerseyNumber: r["Jersey Number"] ?? "", height: r.Height ?? "", weight: r.Weight ?? "",
    value: r.Value ?? "", skills: Object.fromEntries(skillCols.filter((c) => r[c]).map((c) => [c, num(r[c])])),
  })).sort((a, b) => b.overall - a.overall);

  return { matches, players };
}
