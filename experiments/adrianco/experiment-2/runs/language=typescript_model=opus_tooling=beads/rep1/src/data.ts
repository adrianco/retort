import { readCSV } from "./csv.js";
import { join } from "node:path";

export type Match = {
  date: string; // ISO date
  season: number | null;
  round: string | null;
  competition: string;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number | null;
  awayGoal: number | null;
  stage?: string | null;
  arena?: string | null;
  extra?: Record<string, string>;
};

export type Player = {
  id: string;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  position: string;
  jerseyNumber: string;
  height: string;
  weight: string;
};

export function normalizeTeam(name: string): string {
  if (!name) return "";
  // Remove state suffix "-XX", trim, collapse spaces
  let s = name.trim();
  s = s.replace(/-[A-Z]{2}$/, "");
  s = s.replace(/\s+/g, " ");
  return s;
}

export function teamKey(name: string): string {
  return normalizeTeam(name)
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]/g, "");
}

export function teamMatches(query: string, name: string): boolean {
  if (!query || !name) return false;
  const q = teamKey(query);
  const n = teamKey(name);
  if (!q || !n) return false;
  return n.includes(q) || q.includes(n);
}

function parseDate(s: string): string {
  if (!s) return "";
  const trimmed = s.trim();
  // ISO "2012-05-19 18:30:00" or "2012-05-19"
  const isoMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) return `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`;
  // Brazilian DD/MM/YYYY
  const brMatch = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (brMatch) {
    const d = brMatch[1].padStart(2, "0");
    const m = brMatch[2].padStart(2, "0");
    return `${brMatch[3]}-${m}-${d}`;
  }
  return trimmed;
}

function num(s: string): number | null {
  if (s === undefined || s === null || s === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export class SoccerData {
  matches: Match[] = [];
  players: Player[] = [];
  loaded = false;

  load(dataDir: string): void {
    if (this.loaded) return;

    const brasileirao = readCSV(join(dataDir, "Brasileirao_Matches.csv"));
    for (const r of brasileirao) {
      this.matches.push({
        date: parseDate(r.datetime),
        season: num(r.season),
        round: r.round || null,
        competition: "Brasileirão Serie A",
        homeTeam: normalizeTeam(r.home_team),
        awayTeam: normalizeTeam(r.away_team),
        homeGoal: num(r.home_goal),
        awayGoal: num(r.away_goal),
      });
    }

    const cup = readCSV(join(dataDir, "Brazilian_Cup_Matches.csv"));
    for (const r of cup) {
      this.matches.push({
        date: parseDate(r.datetime),
        season: num(r.season),
        round: r.round || null,
        competition: "Copa do Brasil",
        homeTeam: normalizeTeam(r.home_team),
        awayTeam: normalizeTeam(r.away_team),
        homeGoal: num(r.home_goal),
        awayGoal: num(r.away_goal),
      });
    }

    const lib = readCSV(join(dataDir, "Libertadores_Matches.csv"));
    for (const r of lib) {
      this.matches.push({
        date: parseDate(r.datetime),
        season: num(r.season),
        round: null,
        stage: r.stage || null,
        competition: "Copa Libertadores",
        homeTeam: normalizeTeam(r.home_team),
        awayTeam: normalizeTeam(r.away_team),
        homeGoal: num(r.home_goal),
        awayGoal: num(r.away_goal),
      });
    }

    const br = readCSV(join(dataDir, "BR-Football-Dataset.csv"));
    for (const r of br) {
      const season = r.date ? num(r.date.slice(0, 4)) : null;
      this.matches.push({
        date: parseDate(r.date),
        season,
        round: null,
        competition: r.tournament || "Unknown",
        homeTeam: normalizeTeam(r.home),
        awayTeam: normalizeTeam(r.away),
        homeGoal: num(r.home_goal),
        awayGoal: num(r.away_goal),
        extra: {
          home_corner: r.home_corner,
          away_corner: r.away_corner,
          home_shots: r.home_shots,
          away_shots: r.away_shots,
        },
      });
    }

    const novo = readCSV(join(dataDir, "novo_campeonato_brasileiro.csv"));
    for (const r of novo) {
      this.matches.push({
        date: parseDate(r.Data),
        season: num(r.Ano),
        round: r.Rodada || null,
        competition: "Brasileirão Serie A (Historical)",
        homeTeam: normalizeTeam(r.Equipe_mandante),
        awayTeam: normalizeTeam(r.Equipe_visitante),
        homeGoal: num(r.Gols_mandante),
        awayGoal: num(r.Gols_visitante),
        arena: r.Arena || null,
      });
    }

    const fifa = readCSV(join(dataDir, "fifa_data.csv"));
    for (const r of fifa) {
      if (!r.Name) continue;
      this.players.push({
        id: r.ID,
        name: r.Name,
        age: num(r.Age),
        nationality: r.Nationality || "",
        overall: num(r.Overall),
        potential: num(r.Potential),
        club: r.Club || "",
        position: r.Position || "",
        jerseyNumber: r["Jersey Number"] || "",
        height: r.Height || "",
        weight: r.Weight || "",
      });
    }

    this.loaded = true;
  }
}

let instance: SoccerData | null = null;

export function getData(dataDir: string): SoccerData {
  if (!instance) {
    instance = new SoccerData();
    instance.load(dataDir);
  }
  return instance;
}

export function resetData(): void {
  instance = null;
}
