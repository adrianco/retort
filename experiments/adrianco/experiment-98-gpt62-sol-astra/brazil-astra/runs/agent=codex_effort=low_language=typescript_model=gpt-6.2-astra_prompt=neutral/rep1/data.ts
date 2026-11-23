import { readFileSync } from "node:fs";
import { join } from "node:path";

export type Row = Record<string, string>;
function readCsv(path: string): Row[] {
  const input = readFileSync(path, "utf8").replace(/^\uFEFF/, "");
  let header: string[] = [],
    fields: string[] = [],
    field = "",
    quoted = false;
  const rows: Row[] = [];
  function finish() {
    fields.push(field);
    if (!header.length) header = fields;
    else if (fields.length > 1)
      rows.push(
        Object.fromEntries(header.map((key, i) => [key, fields[i] ?? ""])),
      );
    fields = [];
    field = "";
  }
  for (let i = 0; i < input.length; i++) {
    const c = input[i];
    if (c === '"') {
      if (quoted && input[i + 1] === '"') {
        field += '"';
        i++;
      } else quoted = !quoted;
    } else if (!quoted && c === ",") {
      fields.push(field);
      field = "";
    } else if (!quoted && c === "\n") finish();
    else if (quoted || c !== "\r") field += c;
  }
  if (field || fields.length) finish();
  return rows;
}
export const fold = (s: string) =>
  s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase().trim();
const aliases: Row = {
  "sport club corinthians paulista": "corinthians",
  "clube de regatas do flamengo": "flamengo",
  "sao paulo futebol clube": "sao paulo",
  "sociedade esportiva palmeiras": "palmeiras",
  "atletico mineiro": "atletico mg",
  athletico: "atletico pr",
  "athletico pr": "atletico pr",
  "atletico paranaense": "atletico pr",
  "athletico paranaense": "atletico pr",
  "atletico goianiense": "atletico go",
  "america mineiro": "america mg",
  america: "america mg",
  "botafogo rj": "botafogo",
  vasco: "vasco da gama",
  "sport recife": "sport",
  "ec bahia": "bahia",
  "ec juventude": "juventude",
  "nautico capibaribe": "nautico",
  "red bull bragantino": "bragantino",
  "rb bragantino": "bragantino",
  "fortaleza esporte clube": "fortaleza",
};
const qualified = new Set([
  "atletico",
  "athletico",
  "america",
  "operario",
  "nacional",
  "botafogo",
  "fluminense",
  "portuguesa",
  "santa cruz",
  "guarani",
  "vitoria",
]);
export function club(s: string): string {
  let n = fold(s)
    .replace(/\s*-\s*/g, " ")
    .replace(/\s+/g, " ");
  const m = n.match(
    /^(.*) (ac|al|ap|am|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to)$/,
  );
  if (
    m &&
    (!qualified.has(m[1]) ||
      [
        "fluminense rj",
        "portuguesa sp",
        "santa cruz pe",
        "guarani sp",
        "vitoria ba",
      ].includes(n))
  )
    n = m[1];
  n = n.replace(/ fc$/, "");
  return Object.hasOwn(aliases, n) ? aliases[n] : n;
}
export function day(s: string) {
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(s)) return s.split("/").reverse().join("-");
  return /^\d{4}-\d{2}-\d{2}/.test(s) ? s.slice(0, 10) : "";
}
export const files = [
  "Brasileirao_Matches.csv",
  "novo_campeonato_brasileiro.csv",
  "Brazilian_Cup_Matches.csv",
  "Libertadores_Matches.csv",
  "BR-Football-Dataset.csv",
];
export interface Match {
  id: string;
  date: string;
  season: number;
  competition: string;
  home: string;
  away: string;
  homeGoals: number | null;
  awayGoals: number | null;
  round: string;
  stage: string;
  sources: string[];
  details: Row;
}
export function league(s: string) {
  return [
    "brasileirao",
    "brasileirao serie a",
    "campeonato brasileiro",
    "serie a",
  ].includes(fold(s))
    ? "Serie A"
    : fold(s).includes("libertadores")
      ? "Copa Libertadores"
      : s.trim();
}
function goal(s: string) {
  return /^\d+(\.0+)?$/.test(s) ? Number(s) : null;
}
export class Graph {
  players: Row[];
  matches: Match[] = [];
  sourceMatches = new Map<string, Match[]>();
  constructor(dir: string) {
    this.players = readCsv(join(dir, "fifa_data.csv")).sort(
      (a, b) => +b.Overall - +a.Overall,
    );
    const fixtures = new Map<string, Match[]>();
    for (const [i, file] of files.entries()) {
      const rows = readCsv(join(dir, file)),
        originals: Match[] = [];
      const cupRounds = new Map<number, number>();
      if (i === 2)
        for (const r of rows)
          cupRounds.set(
            +r.season,
            Math.max(+r.round, cupRounds.get(+r.season) ?? 0),
          );
      for (const [index, r] of rows.entries()) {
        const date = day(r.datetime ?? r.Data ?? r.date);
        const competition = [
          "Serie A",
          "Serie A",
          "Copa do Brasil",
          "Copa Libertadores",
          r.tournament,
        ][i];
        let season = Number(r.season ?? r.Ano ?? date.slice(0, 4));
        if (i === 4 && date >= "2021-01-01" && date < "2021-03-08")
          season = 2020;
        const round = r.round ?? r.Rodada ?? "";
        const match: Match = {
          id: file + "#" + (index + 1),
          date,
          season,
          competition,
          home: club(r.home_team ?? r.Equipe_mandante ?? r.home),
          away: club(r.away_team ?? r.Equipe_visitante ?? r.away),
          homeGoals: goal(r.home_goal ?? r.Gols_mandante),
          awayGoals: goal(r.away_goal ?? r.Gols_visitante),
          round,
          stage: r.stage ?? "",
          sources: [file],
          details: r,
        };
        if (i === 2 && season <= 2020) {
          const distance = cupRounds.get(season)! - Number(round);
          match.stage =
            ["final", "semifinals", "quarterfinals"][distance] ?? "";
        }
        originals.push(match);
        const key = [competition, season, match.home, match.away].join("|");
        const bucket = fixtures.get(key) ?? [];
        const existing = bucket.find(
          (m) =>
            !m.sources.includes(file) &&
            (competition === "Serie A" ||
              (date &&
                Math.abs(Date.parse(date) - Date.parse(m.date)) <= 86400000)),
        );
        if (existing) {
          existing.sources.push(file);
          existing.details = { ...r, ...existing.details };
          if (!existing.date) existing.date = date;
          if (existing.homeGoals === null || existing.awayGoals === null) {
            existing.homeGoals = match.homeGoals;
            existing.awayGoals = match.awayGoals;
          }
        } else {
          const canonical = { ...match, sources: [file] };
          bucket.push(canonical);
          fixtures.set(key, bucket);
          this.matches.push(canonical);
        }
      }
      this.sourceMatches.set(file, originals);
    }
  }
}
