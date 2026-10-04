import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

export type Competition = "Brasileirão" | "Copa do Brasil" | "Libertadores" | "Serie B" | "Serie C";

export interface Match {
  date: string; // ISO YYYY-MM-DD
  home: string; // display name
  away: string;
  homeKey: string; // normalized key
  awayKey: string;
  homeGoals: number;
  awayGoals: number;
  season: number;
  competition: Competition;
  round?: string;
  stage?: string;
  arena?: string;
  source: string;
  stats?: { homeCorners?: number; awayCorners?: number; homeShots?: number; awayShots?: number; homeAttacks?: number; awayAttacks?: number };
}

export interface Player {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jersey: string;
  height: string;
  weight: string;
  value: string;
  preferredFoot: string;
  skills: Record<string, number>;
}

/** RFC4180-ish CSV parser supporting quoted fields, escaped quotes and BOM. */
export function parseCsv(text: string): Record<string, string>[] {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); field = "";
      rows.push(row); row = [];
    } else field += c;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  const header = rows.shift() ?? [];
  return rows
    .filter((r) => r.length > 1 || r[0] !== "")
    .map((r) => Object.fromEntries(header.map((h, i) => [h.trim(), (r[i] ?? "").trim()])));
}

/** Parse ISO, ISO+time, or Brazilian DD/MM/YYYY dates into YYYY-MM-DD. */
export function parseDate(s: string): string {
  s = s.trim();
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  return s;
}

const STATES = new Set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split(" "));

export function stripAccents(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

// Clubs whose base name is ambiguous without a state.
const AMBIGUOUS = new Set(["atletico", "america", "botafogo", "athletico", "nacional", "operario", "guarani", "internacional"]);
const DEFAULT_STATE: Record<string, string> = { atletico: "mg", america: "mg", botafogo: "rj", athletico: "pr", guarani: "sp", internacional: "rs", operario: "pr", nacional: "am" };

const ALIASES: Record<string, string> = {
  "athletico paranaense": "athletico-pr",
  "atletico paranaense": "athletico-pr",
  "atletico-pr": "athletico-pr",
  "atletico mineiro": "atletico-mg",
  "atletico goianiense": "atletico-go",
  "atletico go": "atletico-go",
  "vasco da gama": "vasco",
  "sport recife": "sport",
  "gremio porto alegre": "gremio",
  "sc corinthians paulista": "corinthians",
  "corinthians paulista": "corinthians",
  "sao paulo fc": "sao paulo",
  "spfc": "sao paulo",
  "fla": "flamengo",
  "flu": "fluminense",
  "verdao": "palmeiras",
  "timao": "corinthians",
  "internacional porto alegre": "internacional-rs",
  "bragantino": "red bull bragantino",
  "rb bragantino": "red bull bragantino",
  "cuiaba esporte": "cuiaba",
  "america mineiro": "america-mg",
  "botafogo fr": "botafogo-rj",
};

const NOISE = new Set(["fc", "ec", "sc", "ac", "cr", "fr", "clube", "club", "futebol", "esporte", "sport club", "de", "regatas", "do", "da", "esporte clube", "s.a.f", "saf", "and"]);

/**
 * Normalize a team name to a canonical key so that "Palmeiras-SP", "Palmeiras",
 * "Sociedade Esportiva Palmeiras" etc. resolve to the same team where possible.
 */
export function normalizeTeam(raw: string): string {
  let s = stripAccents(raw).replace(/\(.*?\)/g, " ").trim();
  let state: string | undefined;
  const sm = s.match(/^(.*?)(?:\s*-\s*|\s+)([A-Za-z]{2})$/);
  if (sm && STATES.has(sm[2].toUpperCase()) && sm[1].trim().length > 2) {
    state = sm[2].toLowerCase();
    s = sm[1];
  }
  s = s.toLowerCase().replace(/[.']/g, "").replace(/\s+/g, " ").trim();
  if (ALIASES[s]) return ALIASES[s];
  const full: Record<string, string> = {
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "fluminense football club": "fluminense",
    "santos futebol clube": "santos",
    "sao paulo futebol clube": "sao paulo",
    "gremio foot-ball porto alegrense": "gremio",
    "sport club internacional": "internacional-rs",
    "cruzeiro esporte clube": "cruzeiro",
    "fortaleza esporte clube": "fortaleza",
    "club athletico paranaense": "athletico-pr",
    "clube atletico mineiro": "atletico-mg",
  };
  if (full[s]) return full[s];
  const words = s.split(" ").filter((w) => !NOISE.has(w));
  s = words.join(" ") || s;
  if (ALIASES[s]) return ALIASES[s];
  if (AMBIGUOUS.has(s)) {
    const k = `${s}-${state ?? DEFAULT_STATE[s]}`;
    return ALIASES[k] ?? k;
  }
  return s;
}

/** Does a normalized team key match the user's query string? */
export function teamMatches(key: string, query: string): boolean {
  const q = normalizeTeam(query);
  if (key === q) return true;
  const base = key.split("-")[0];
  if (!q.includes("-") && base === q) return true;
  return false;
}

const DISPLAY: Record<string, string> = {};
function remember(key: string, raw: string) {
  // Prefer the shortest accented name without state suffix as the display name.
  const clean = raw.replace(/\s*-\s*[A-Z]{2}$/, "").replace(/\s*\(.*?\)/g, "").trim();
  const cur = DISPLAY[key];
  const score = (x: string) => (x !== stripAccents(x) ? 1 : 0) + (x.replace(/[^A-Z]/g, "").length > 1 ? 0.5 : 0);
  if (!cur || (clean.length < cur.length && clean.length > 2) || (clean.length === cur.length && score(clean) > score(cur))) DISPLAY[key] = clean;
}
export function displayName(key: string): string {
  const d = DISPLAY[key] ?? key;
  const st = key.match(/-([a-z]{2})$/);
  return st && !d.toLowerCase().endsWith(st[1]) ? `${d}-${st[1].toUpperCase()}` : d;
}

const num = (s: string) => {
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : NaN;
};

function mk(m: Omit<Match, "homeKey" | "awayKey">): Match {
  const homeKey = normalizeTeam(m.home);
  const awayKey = normalizeTeam(m.away);
  remember(homeKey, m.home);
  remember(awayKey, m.away);
  return { ...m, homeKey, awayKey };
}

export class Dataset {
  matches: Match[] = [];
  players: Player[] = [];
  bySource: Record<string, number> = {};

  static load(dir = defaultDataDir()): Dataset {
    const ds = new Dataset();
    const read = (f: string) => parseCsv(readFileSync(join(dir, f), "utf8"));
    const add = (src: string, ms: Match[]) => {
      const ok = ms.filter((m) => !Number.isNaN(m.homeGoals) && !Number.isNaN(m.awayGoals) && m.home && m.away);
      ds.bySource[src] = ok.length;
      ds.matches.push(...ok);
    };

    add("Brasileirao_Matches.csv", read("Brasileirao_Matches.csv").map((r) => mk({
      date: parseDate(r.datetime), home: r.home_team, away: r.away_team,
      homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), season: +r.season,
      competition: "Brasileirão", round: r.round, source: "Brasileirao_Matches.csv",
    })));
    add("Brazilian_Cup_Matches.csv", read("Brazilian_Cup_Matches.csv").map((r) => mk({
      date: parseDate(r.datetime), home: r.home_team, away: r.away_team,
      homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), season: +r.season,
      competition: "Copa do Brasil", round: r.round, source: "Brazilian_Cup_Matches.csv",
    })));
    add("Libertadores_Matches.csv", read("Libertadores_Matches.csv").map((r) => mk({
      date: parseDate(r.datetime), home: r.home_team, away: r.away_team,
      homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), season: +r.season,
      competition: "Libertadores", stage: r.stage, source: "Libertadores_Matches.csv",
    })));
    const tour: Record<string, Competition> = { "Serie A": "Brasileirão", "Copa do Brasil": "Copa do Brasil", "Serie B": "Serie B", "Serie C": "Serie C" };
    add("BR-Football-Dataset.csv", read("BR-Football-Dataset.csv").map((r) => {
      const date = parseDate(r.date);
      return mk({
        date, home: r.home, away: r.away, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal),
        season: +date.slice(0, 4), competition: tour[r.tournament] ?? (r.tournament as Competition),
        source: "BR-Football-Dataset.csv",
        stats: {
          homeCorners: num(r.home_corner), awayCorners: num(r.away_corner),
          homeShots: num(r.home_shots), awayShots: num(r.away_shots),
          homeAttacks: num(r.home_attack), awayAttacks: num(r.away_attack),
        },
      });
    }));
    add("novo_campeonato_brasileiro.csv", read("novo_campeonato_brasileiro.csv").map((r) => mk({
      date: parseDate(r.Data), home: r.Equipe_mandante, away: r.Equipe_visitante,
      homeGoals: num(r.Gols_mandante), awayGoals: num(r.Gols_visitante), season: +r.Ano,
      competition: "Brasileirão", round: r.Rodada, arena: r.Arena, source: "novo_campeonato_brasileiro.csv",
    })));

    const SKILLS = ["Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes"];
    ds.players = read("fifa_data.csv").map((r) => ({
      id: +r.ID, name: r.Name, age: +r.Age, nationality: r.Nationality, overall: +r.Overall,
      potential: +r.Potential, club: r.Club, position: r.Position, jersey: r["Jersey Number"],
      height: r.Height, weight: r.Weight, value: r.Value, preferredFoot: r["Preferred Foot"],
      skills: Object.fromEntries(SKILLS.filter((k) => r[k] !== undefined && r[k] !== "").map((k) => [k, +r[k]])),
    }));
    ds.bySource["fifa_data.csv"] = ds.players.length;
    return ds;
  }
}

export function defaultDataDir(): string {
  if (process.env.SOCCER_DATA_DIR) return process.env.SOCCER_DATA_DIR;
  const here = dirname(fileURLToPath(import.meta.url));
  return join(here, "..", "data", "kaggle");
}
