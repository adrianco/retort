import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseCsv, type CsvRow } from "./csv.js";
import { normalizeTeamName, parseDate } from "./normalize.js";
import type { Dataset, Match, Player } from "./model.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));

/** Default location of the bundled Kaggle CSVs (works from src/ and dist/). */
export const DEFAULT_DATA_DIR = path.resolve(HERE, "..", "data", "kaggle");

const SERIE_A = "Brasileirão Série A";
const COPA_DO_BRASIL = "Copa do Brasil";
const LIBERTADORES = "Copa Libertadores";

/** Competition labels used by the BR-Football tournament column. */
const BR_FOOTBALL_TOURNAMENTS: Record<string, string> = {
  "Serie A": SERIE_A,
  "Serie B": "Brasileirão Série B",
  "Serie C": "Brasileirão Série C",
  "Copa do Brasil": COPA_DO_BRASIL,
};

interface RawMatch {
  date: string;
  home: string;
  away: string;
  homeGoals: string;
  awayGoals: string;
  competition: string;
  round: string;
}

interface MatchSource {
  file: string;
  read: (row: CsvRow) => RawMatch;
}

/**
 * Column mapping for each match file. Order matters: when the same fixture
 * appears in more than one file the first source wins during de-duplication.
 */
const MATCH_SOURCES: MatchSource[] = [
  {
    file: "Brasileirao_Matches.csv",
    read: (r) => ({
      date: r.datetime,
      home: r.home_team,
      away: r.away_team,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
      competition: SERIE_A,
      round: r.round ? `Round ${r.round}` : "",
    }),
  },
  {
    file: "novo_campeonato_brasileiro.csv",
    read: (r) => ({
      date: r.Data,
      home: r.Equipe_mandante,
      away: r.Equipe_visitante,
      homeGoals: r.Gols_mandante,
      awayGoals: r.Gols_visitante,
      competition: SERIE_A,
      round: r.Rodada ? `Round ${r.Rodada}` : "",
    }),
  },
  {
    file: "Brazilian_Cup_Matches.csv",
    read: (r) => ({
      date: r.datetime,
      home: r.home_team,
      away: r.away_team,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
      competition: COPA_DO_BRASIL,
      round: r.round,
    }),
  },
  {
    file: "Libertadores_Matches.csv",
    read: (r) => ({
      date: r.datetime,
      home: r.home_team,
      away: r.away_team,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
      competition: LIBERTADORES,
      round: r.stage,
    }),
  },
  {
    file: "BR-Football-Dataset.csv",
    read: (r) => ({
      date: r.date,
      home: r.home,
      away: r.away,
      homeGoals: r.home_goal,
      awayGoals: r.away_goal,
      competition: BR_FOOTBALL_TOURNAMENTS[r.tournament] ?? r.tournament,
      round: "",
    }),
  },
];

// Files spell the same club differently ("Sao Paulo", "São Paulo-SP", "Athletico-PR" vs
// "Athletico Paranaense"), so the de-duplication key uses the leading word of each name.
function leadingWord(team: string): string {
  return normalizeTeamName(team).split(" ")[0] ?? "";
}

function readCsv(dir: string, file: string): CsvRow[] {
  return parseCsv(readFileSync(path.join(dir, file), "utf8"));
}

function toMatch(raw: RawMatch, source: string, index: number): Match | undefined {
  const date = parseDate(raw.date);
  const homeGoals = Number(raw.homeGoals);
  const awayGoals = Number(raw.awayGoals);
  if (!date || !raw.home.trim() || !raw.away.trim()) return undefined;
  if (!Number.isInteger(homeGoals) || !Number.isInteger(awayGoals)) return undefined;
  return {
    id: `${source}#${index}`,
    date,
    season: Number(date.slice(0, 4)),
    competition: raw.competition,
    round: raw.round.trim(),
    home: raw.home.trim(),
    away: raw.away.trim(),
    homeGoals,
    awayGoals,
    source,
  };
}

/**
 * Load all match files into one list, sorted by date. Fixtures present in
 * several files (the Brasileirão appears in three, with different team
 * spellings) are counted once.
 */
/** The date and the days either side of it: some sources record evening kick-offs a day late. */
function nearbyDates(date: string): string[] {
  const t = Date.parse(`${date}T00:00:00Z`);
  return [-1, 0, 1].map((offset) => new Date(t + offset * 86_400_000).toISOString().slice(0, 10));
}

export function loadMatches(dir: string): Match[] {
  const matches: Match[] = [];
  // date|competition|score -> leading words of the home and away names already kept.
  const kept = new Map<string, { home: string; away: string }[]>();
  for (const source of MATCH_SOURCES) {
    const rows = readCsv(dir, source.file);
    rows.forEach((row, index) => {
      const match = toMatch(source.read(row), source.file, index);
      if (!match) return;
      const home = leadingWord(match.home);
      const away = leadingWord(match.away);
      const keyFor = (date: string) => `${date}|${match.competition}|${match.homeGoals}-${match.awayGoals}`;
      // A club plays at most once a day in a competition, so a fixture with the
      // same score on a nearby date sharing either club is the same match.
      const duplicate = nearbyDates(match.date).some((d) =>
        (kept.get(keyFor(d)) ?? []).some((e) => e.home === home || e.away === away),
      );
      if (duplicate) return;
      const key = keyFor(match.date);
      kept.set(key, [...(kept.get(key) ?? []), { home, away }]);
      matches.push(match);
    });
  }
  return matches.sort((a, b) => a.date.localeCompare(b.date));
}

function optionalNumber(value: string | undefined): number | undefined {
  if (value === undefined || value.trim() === "") return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

/** Load the FIFA player file. */
export function loadPlayers(dir: string): Player[] {
  const players: Player[] = [];
  readCsv(dir, "fifa_data.csv").forEach((r, index) => {
    const overall = optionalNumber(r.Overall);
    if (overall === undefined) return;
    players.push({
      id: optionalNumber(r.ID) ?? index,
      name: r.Name,
      age: optionalNumber(r.Age) ?? 0,
      nationality: r.Nationality,
      overall,
      potential: optionalNumber(r.Potential) ?? overall,
      club: r.Club,
      position: r.Position,
      jerseyNumber: optionalNumber(r["Jersey Number"]),
      height: r.Height,
      weight: r.Weight,
      preferredFoot: r["Preferred Foot"],
      value: r.Value,
    });
  });
  return players;
}

/** Load every dataset file from `dir`. */
export function loadDataset(dir: string = DEFAULT_DATA_DIR): Dataset {
  return { matches: loadMatches(dir), players: loadPlayers(dir) };
}
