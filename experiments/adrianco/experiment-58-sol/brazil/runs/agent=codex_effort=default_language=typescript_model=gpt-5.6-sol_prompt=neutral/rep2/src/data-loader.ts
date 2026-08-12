import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  displayTeamName,
  normalizeCompetition,
  normalizeTeamName,
  normalizeText,
  parseNumber,
  parseRequiredNumber,
  parseSoccerDate,
} from "./normalize.js";
import { COMPETITIONS, type MatchSource, type Player, type SoccerMatch } from "./types.js";

type CsvRow = Record<string, string>;

const ATTRIBUTE_COLUMNS = [
  "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
  "Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed",
  "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength",
  "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
  "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
  "GKKicking", "GKPositioning", "GKReflexes",
] as const;

export interface LoadedSoccerData {
  matches: SoccerMatch[];
  players: Player[];
}

export function defaultDataDirectory(): string {
  const moduleDirectory = path.dirname(fileURLToPath(import.meta.url));
  const candidates = [
    process.env.SOCCER_DATA_DIR,
    path.resolve(process.cwd(), "data/kaggle"),
    path.resolve(moduleDirectory, "../data/kaggle"),
    path.resolve(moduleDirectory, "../../data/kaggle"),
  ].filter((candidate): candidate is string => Boolean(candidate));
  const found = candidates.find((candidate) => existsSync(candidate));
  if (!found) throw new Error(`Soccer data directory not found. Checked: ${candidates.join(", ")}`);
  return found;
}

function readCsv(directory: string, fileName: string): CsvRow[] {
  const csv = readFileSync(path.join(directory, fileName), "utf8");
  return parseCsv(csv);
}

/** RFC 4180-style parser kept local so dataset ingestion has no runtime dependency beyond Node. */
function parseCsv(csv: string): CsvRow[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < csv.length; index += 1) {
    const character = csv[index]!;
    if (quoted) {
      if (character === '"') {
        if (csv[index + 1] === '"') {
          field += '"';
          index += 1;
        } else quoted = false;
      } else field += character;
      continue;
    }
    if (character === '"' && field.length === 0) quoted = true;
    else if (character === ",") {
      row.push(field.trim());
      field = "";
    } else if (character === "\n") {
      row.push(field.trim());
      if (row.some((value) => value.length > 0)) rows.push(row);
      row = [];
      field = "";
    } else if (character !== "\r") field += character;
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field.trim());
    if (row.some((value) => value.length > 0)) rows.push(row);
  }
  const headerRow = rows.shift();
  if (!headerRow) return [];
  const headers = headerRow.map((header) => header.replace(/^\uFEFF/, "").trim());
  return rows.map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])));
}

function competitionDisplayName(value: string): string {
  const normalized = normalizeCompetition(value);
  if (normalized === "brasileirao") return COMPETITIONS.brasileirao;
  if (normalized === "copa do brasil") return COMPETITIONS.copaDoBrasil;
  if (normalized === "libertadores") return COMPETITIONS.libertadores;
  return value.trim() || "Unknown competition";
}

function createMatch(
  source: MatchSource,
  sourceRow: number,
  values: {
    competition: string;
    season: number;
    date: string;
    homeTeam: string;
    awayTeam: string;
    homeGoals: number;
    awayGoals: number;
    time?: string;
    round?: string;
    stage?: string;
    homeState?: string;
    awayState?: string;
    venue?: string;
    statistics?: SoccerMatch["statistics"];
  },
): SoccerMatch {
  const parsedDate = parseSoccerDate(values.date);
  const homeTeam = displayTeamName(values.homeTeam);
  const awayTeam = displayTeamName(values.awayTeam);
  return {
    id: `${source}:${sourceRow}`,
    source,
    sourceRow,
    competition: competitionDisplayName(values.competition),
    season: values.season,
    ...parsedDate,
    time: values.time,
    round: values.round,
    stage: values.stage,
    homeTeam,
    homeTeamKey: normalizeTeamName(values.homeTeam),
    homeState: values.homeState,
    awayTeam,
    awayTeamKey: normalizeTeamName(values.awayTeam),
    awayState: values.awayState,
    homeGoals: values.homeGoals,
    awayGoals: values.awayGoals,
    venue: values.venue,
    statistics: values.statistics,
  };
}

function loadBrasileirao(directory: string): SoccerMatch[] {
  return readCsv(directory, "Brasileirao_Matches.csv").flatMap((row, index) => {
    const homeGoals = parseNumber(row.home_goal);
    const awayGoals = parseNumber(row.away_goal);
    if (homeGoals === undefined || awayGoals === undefined) return [];
    return [createMatch("brasileirao", index + 2, {
      competition: COMPETITIONS.brasileirao,
      season: parseRequiredNumber(row.season, "season"),
      date: row.datetime ?? "",
      homeTeam: row.home_team ?? "",
      awayTeam: row.away_team ?? "",
      homeGoals,
      awayGoals,
      round: row.round,
      homeState: row.home_team_state,
      awayState: row.away_team_state,
    })];
  });
}

function loadBrazilianCup(directory: string): SoccerMatch[] {
  return readCsv(directory, "Brazilian_Cup_Matches.csv").flatMap((row, index) => {
    const homeGoals = parseNumber(row.home_goal);
    const awayGoals = parseNumber(row.away_goal);
    if (homeGoals === undefined || awayGoals === undefined) return [];
    return [createMatch("copa-do-brasil", index + 2, {
      competition: COMPETITIONS.copaDoBrasil,
      season: parseRequiredNumber(row.season, "season"),
      date: row.datetime ?? "",
      homeTeam: row.home_team ?? "",
      awayTeam: row.away_team ?? "",
      homeGoals,
      awayGoals,
      round: row.round,
    })];
  });
}

function loadLibertadores(directory: string): SoccerMatch[] {
  return readCsv(directory, "Libertadores_Matches.csv").flatMap((row, index) => {
    const homeGoals = parseNumber(row.home_goal);
    const awayGoals = parseNumber(row.away_goal);
    if (homeGoals === undefined || awayGoals === undefined) return [];
    return [createMatch("libertadores", index + 2, {
      competition: COMPETITIONS.libertadores,
      season: parseRequiredNumber(row.season, "season"),
      date: row.datetime ?? "",
      homeTeam: row.home_team ?? "",
      awayTeam: row.away_team ?? "",
      homeGoals,
      awayGoals,
      stage: row.stage,
    })];
  });
}

function loadExtended(directory: string): SoccerMatch[] {
  return readCsv(directory, "BR-Football-Dataset.csv").flatMap((row, index) => {
    const homeGoals = parseNumber(row.home_goal);
    const awayGoals = parseNumber(row.away_goal);
    if (homeGoals === undefined || awayGoals === undefined || !row.date) return [];
    const parsedDate = parseSoccerDate(row.date);
    return [
      createMatch("extended", index + 2, {
        competition: row.tournament ?? "Unknown competition",
        season: Number(parsedDate.date.slice(0, 4)),
        date: row.date,
        time: row.time,
        homeTeam: row.home ?? "",
        awayTeam: row.away ?? "",
        homeGoals,
        awayGoals,
        statistics: {
          homeCorners: parseNumber(row.home_corner),
          awayCorners: parseNumber(row.away_corner),
          homeAttacks: parseNumber(row.home_attack),
          awayAttacks: parseNumber(row.away_attack),
          homeShots: parseNumber(row.home_shots),
          awayShots: parseNumber(row.away_shots),
          totalCorners: parseNumber(row.total_corners),
        },
      }),
    ];
  });
}

function loadHistoricalBrasileirao(directory: string): SoccerMatch[] {
  return readCsv(directory, "novo_campeonato_brasileiro.csv").flatMap((row, index) => {
    const homeGoals = parseNumber(row.Gols_mandante);
    const awayGoals = parseNumber(row.Gols_visitante);
    if (homeGoals === undefined || awayGoals === undefined) return [];
    return [createMatch("historical-brasileirao", index + 2, {
      competition: COMPETITIONS.brasileirao,
      season: parseRequiredNumber(row.Ano, "Ano"),
      date: row.Data ?? "",
      homeTeam: row.Equipe_mandante ?? "",
      awayTeam: row.Equipe_visitante ?? "",
      homeGoals,
      awayGoals,
      round: row.Rodada,
      homeState: row.Mandante_UF,
      awayState: row.Visitante_UF,
      venue: row.Arena,
    })];
  });
}

function loadPlayers(directory: string): Player[] {
  return readCsv(directory, "fifa_data.csv").flatMap((row) => {
    const id = parseNumber(row.ID);
    const name = row.Name?.trim();
    if (id === undefined || !name) return [];
    const attributes: Record<string, number> = {};
    for (const column of ATTRIBUTE_COLUMNS) {
      const value = parseNumber(row[column]);
      if (value !== undefined) attributes[column] = value;
    }
    const club = row.Club?.trim() || undefined;
    return [{
      id,
      name,
      nameKey: normalizeText(name),
      age: parseNumber(row.Age),
      nationality: row.Nationality?.trim() || "Unknown",
      nationalityKey: normalizeText(row.Nationality ?? ""),
      overall: parseNumber(row.Overall),
      potential: parseNumber(row.Potential),
      club,
      clubKey: club ? normalizeTeamName(club) : undefined,
      position: row.Position?.trim() || undefined,
      jerseyNumber: parseNumber(row["Jersey Number"]),
      height: row.Height?.trim() || undefined,
      weight: row.Weight?.trim() || undefined,
      preferredFoot: row["Preferred Foot"]?.trim() || undefined,
      attributes,
    }];
  });
}

export function loadSoccerData(directory = defaultDataDirectory()): LoadedSoccerData {
  const matches = [
    ...loadBrasileirao(directory),
    ...loadBrazilianCup(directory),
    ...loadLibertadores(directory),
    ...loadExtended(directory),
    ...loadHistoricalBrasileirao(directory),
  ];
  return { matches, players: loadPlayers(directory) };
}
