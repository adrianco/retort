import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export type Match = { source: string; competition: string; date: string; season?: number; round?: string; stage?: string; home: string; away: string; homeGoals: number; awayGoals: number; extras: Record<string, string> };
export type Player = { id: string; name: string; age?: number; nationality: string; overall?: number; potential?: number; club: string; position: string; attributes: Record<string, string> };

/** Small RFC4180 parser; quoted commas and escaped quotes in the source data are preserved. */
export function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = []; let row: string[] = [], value = "", quote = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') { if (quote && text[i + 1] === '"') { value += '"'; i++; } else quote = !quote; }
    else if (c === "," && !quote) { row.push(value); value = ""; }
    else if ((c === "\n" || c === "\r") && !quote) { if (c === "\r" && text[i + 1] === "\n") i++; row.push(value); if (row.some(Boolean)) rows.push(row); row = []; value = ""; }
    else value += c;
  }
  if (value || row.length) { row.push(value); rows.push(row); }
  const [header, ...body] = rows;
  return body.map(values => Object.fromEntries(header.map((name, i) => [name.replace(/^\uFEFF/, ""), values[i] ?? ""])));
}

export function normalize(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/\s*-\s*(ac|al|am|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to)\b/g, "")
    .replace(/[^a-z0-9]+/g, " ").trim();
}
export function matchesName(candidate: string, query: string): boolean { const c = normalize(candidate), q = normalize(query); return c === q || c.includes(q) || q.includes(c); }
export function isoDate(raw: string): string {
  const dmy = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})/); if (dmy) return `${dmy[3]}-${dmy[2]}-${dmy[1]}`;
  const iso = raw.match(/^\d{4}-\d{2}-\d{2}/); return iso ? iso[0] : raw;
}
const num = (v: string | undefined) => { const n = Number(v); return Number.isFinite(n) ? n : 0; };

export class SoccerData {
  readonly matches: Match[]; readonly players: Player[];
  constructor(dataDir = resolve(process.cwd(), "data/kaggle")) {
    const csv = (file: string) => parseCsv(readFileSync(resolve(dataDir, file), "utf8"));
    const make = (file: string, source: string, competition: string, fields: { date: string; season: string; home: string; away: string; hg: string; ag: string; round?: string; stage?: string }) => csv(file).map(r => ({ source, competition: r.tournament || competition, date: isoDate(r[fields.date]), season: r[fields.season] ? Number.parseInt(r[fields.season], 10) : undefined, round: fields.round ? r[fields.round] : undefined, stage: fields.stage ? r[fields.stage] : undefined, home: r[fields.home], away: r[fields.away], homeGoals: num(r[fields.hg]), awayGoals: num(r[fields.ag]), extras: r }));
    this.matches = [
      ...make("Brasileirao_Matches.csv", "brasileirao", "Brasileirão", { date: "datetime", season: "season", home: "home_team", away: "away_team", hg: "home_goal", ag: "away_goal", round: "round" }),
      ...make("Brazilian_Cup_Matches.csv", "brazilian-cup", "Copa do Brasil", { date: "datetime", season: "season", home: "home_team", away: "away_team", hg: "home_goal", ag: "away_goal", round: "round" }),
      ...make("Libertadores_Matches.csv", "libertadores", "Libertadores", { date: "datetime", season: "season", home: "home_team", away: "away_team", hg: "home_goal", ag: "away_goal", stage: "stage" }),
      ...make("BR-Football-Dataset.csv", "extended", "Extended statistics", { date: "date", season: "date", home: "home", away: "away", hg: "home_goal", ag: "away_goal" }),
      ...make("novo_campeonato_brasileiro.csv", "historical", "Brasileirão historical", { date: "Data", season: "Ano", home: "Equipe_mandante", away: "Equipe_visitante", hg: "Gols_mandante", ag: "Gols_visitante", round: "Rodada" })
    ];
    this.players = csv("fifa_data.csv").map(r => ({ id: r.ID, name: r.Name, age: r.Age ? num(r.Age) : undefined, nationality: r.Nationality, overall: r.Overall ? num(r.Overall) : undefined, potential: r.Potential ? num(r.Potential) : undefined, club: r.Club, position: r.Position, attributes: r }));
  }
}
