import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { normalizeCompetition, normalizeTeamName, optionalNumber, parseDate, requiredNumber } from "./normalize.js";
import type { DatasetSummary, Match, MatchSource, MatchStats, Player } from "./types.js";

type CsvRow = Record<string, string>;

export interface DataStoreOptions {
  dataDirectory?: string;
  deduplicate?: boolean;
}

function defaultDataDirectory(): string {
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.resolve(here, "../data/kaggle");
}

async function readCsv(file: string): Promise<CsvRow[]> {
  const contents = await readFile(file, "utf8");
  const records: string[][] = [];
  let record: string[] = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < contents.length; index++) {
    const character = contents[index]!;
    if (quoted) {
      if (character === '"' && contents[index + 1] === '"') {
        field += '"';
        index++;
      } else if (character === '"') {
        quoted = false;
      } else {
        field += character;
      }
    } else if (character === '"') {
      quoted = true;
    } else if (character === ",") {
      record.push(field.trim());
      field = "";
    } else if (character === "\n") {
      record.push(field.replace(/\r$/, "").trim());
      if (record.some(Boolean)) records.push(record);
      record = [];
      field = "";
    } else {
      field += character;
    }
  }
  if (field || record.length) {
    record.push(field.replace(/\r$/, "").trim());
    if (record.some(Boolean)) records.push(record);
  }
  const [headerRow, ...dataRows] = records;
  if (!headerRow) return [];
  const headers = headerRow.map((header) => header.replace(/^\uFEFF/, ""));
  return dataRows.map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])));
}

function matchId(match: Omit<Match, "id" | "sources">): string {
  return createHash("sha1")
    .update([match.date, match.competition, match.homeTeamKey, match.awayTeamKey, match.homeGoals, match.awayGoals].join("|"))
    .digest("hex")
    .slice(0, 16);
}

function createMatch(
  fields: Omit<Match, "id" | "sources">,
  source: MatchSource
): Match {
  return { ...fields, id: matchId(fields), sources: [source] };
}

function commonMatch(
  row: CsvRow,
  source: MatchSource,
  competition: string,
  columns: { date: string; home: string; away: string; homeGoals: string; awayGoals: string; season?: string; round?: string; stage?: string }
): Match | null {
  const date = parseDate(row[columns.date] ?? "");
  const homeGoals = requiredNumber(row[columns.homeGoals]);
  const awayGoals = requiredNumber(row[columns.awayGoals]);
  const homeTeam = row[columns.home]?.trim();
  const awayTeam = row[columns.away]?.trim();
  if (!date || homeGoals === null || awayGoals === null || !homeTeam || !awayTeam) return null;
  const season = optionalNumber(columns.season ? row[columns.season] : undefined) ?? Number(date.slice(0, 4));
  return createMatch({
    date,
    season,
    competition: normalizeCompetition(competition),
    round: columns.round ? row[columns.round]?.trim() || undefined : undefined,
    stage: columns.stage ? row[columns.stage]?.trim() || undefined : undefined,
    homeTeam,
    homeTeamKey: normalizeTeamName(homeTeam),
    awayTeam,
    awayTeamKey: normalizeTeamName(awayTeam),
    homeGoals,
    awayGoals
  }, source);
}

const PLAYER_ATTRIBUTES = [
  "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
  "Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed",
  "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength",
  "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
  "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
  "GKKicking", "GKPositioning", "GKReflexes"
];

export class SoccerDataStore {
  readonly matches: Match[];
  readonly players: Player[];
  readonly summary: DatasetSummary;

  private constructor(matches: Match[], players: Player[]) {
    this.matches = matches;
    this.players = players;
    const seasons = matches.map((match) => match.season).filter(Number.isFinite);
    const sources: Record<string, number> = {};
    for (const match of matches) {
      for (const source of match.sources) sources[source.file] = (sources[source.file] ?? 0) + 1;
    }
    this.summary = {
      matches: matches.length,
      players: players.length,
      sources,
      seasons: seasons.length ? { earliest: Math.min(...seasons), latest: Math.max(...seasons) } : null,
      competitions: [...new Set(matches.map((match) => match.competition))].sort()
    };
  }

  static async load(options: DataStoreOptions = {}): Promise<SoccerDataStore> {
    const directory = options.dataDirectory ?? defaultDataDirectory();
    const matches: Match[] = [];

    const standardFiles = [
      { file: "Brasileirao_Matches.csv", competition: "Brasileirão Serie A", columns: { date: "datetime", home: "home_team", away: "away_team", homeGoals: "home_goal", awayGoals: "away_goal", season: "season", round: "round" } },
      { file: "Brazilian_Cup_Matches.csv", competition: "Copa do Brasil", columns: { date: "datetime", home: "home_team", away: "away_team", homeGoals: "home_goal", awayGoals: "away_goal", season: "season", round: "round" } },
      { file: "Libertadores_Matches.csv", competition: "Copa Libertadores", columns: { date: "datetime", home: "home_team", away: "away_team", homeGoals: "home_goal", awayGoals: "away_goal", season: "season", stage: "stage" } }
    ];
    for (const spec of standardFiles) {
      const rows = await readCsv(path.join(directory, spec.file));
      rows.forEach((row, index) => {
        const match = commonMatch(row, { file: spec.file, row: index + 2 }, spec.competition, spec.columns);
        if (match) matches.push(match);
      });
    }

    const extendedFile = "BR-Football-Dataset.csv";
    const extendedRows = await readCsv(path.join(directory, extendedFile));
    extendedRows.forEach((row, index) => {
      const match = commonMatch(row, { file: extendedFile, row: index + 2 }, row.tournament, {
        date: "date", home: "home", away: "away", homeGoals: "home_goal", awayGoals: "away_goal"
      });
      if (!match) return;
      match.kickoff = row.time || undefined;
      const stats: MatchStats = {
        homeCorners: optionalNumber(row.home_corner), awayCorners: optionalNumber(row.away_corner),
        homeAttacks: optionalNumber(row.home_attack), awayAttacks: optionalNumber(row.away_attack),
        homeShots: optionalNumber(row.home_shots), awayShots: optionalNumber(row.away_shots),
        totalCorners: optionalNumber(row.total_corners)
      };
      match.stats = stats;
      matches.push(match);
    });

    const historicalFile = "novo_campeonato_brasileiro.csv";
    const historicalRows = await readCsv(path.join(directory, historicalFile));
    historicalRows.forEach((row, index) => {
      const match = commonMatch(row, { file: historicalFile, row: index + 2 }, "Brasileirão Serie A", {
        date: "Data", home: "Equipe_mandante", away: "Equipe_visitante", homeGoals: "Gols_mandante",
        awayGoals: "Gols_visitante", season: "Ano", round: "Rodada"
      });
      if (match) {
        match.stats = { stadium: row.Arena || undefined };
        matches.push(match);
      }
    });

    const playerFile = "fifa_data.csv";
    const playerRows = await readCsv(path.join(directory, playerFile));
    const players = playerRows.filter((row) => row.ID && row.Name).map((row): Player => {
      const attributes: Record<string, number> = {};
      for (const field of PLAYER_ATTRIBUTES) {
        const value = optionalNumber(row[field]);
        if (value !== undefined) attributes[field] = value;
      }
      return {
        id: row.ID, name: row.Name, age: optionalNumber(row.Age), nationality: row.Nationality ?? "",
        overall: optionalNumber(row.Overall), potential: optionalNumber(row.Potential), club: row.Club ?? "",
        position: row.Position ?? "", jerseyNumber: optionalNumber(row["Jersey Number"]),
        height: row.Height || undefined, weight: row.Weight || undefined, attributes
      };
    });

    const finalMatches = options.deduplicate === false ? matches : SoccerDataStore.deduplicate(matches);
    finalMatches.sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));
    return new SoccerDataStore(finalMatches, players);
  }

  private static deduplicate(matches: Match[]): Match[] {
    const unique = new Map<string, Match>();
    for (const match of matches) {
      const existing = unique.get(match.id);
      if (!existing) {
        unique.set(match.id, match);
        continue;
      }
      existing.sources.push(...match.sources);
      existing.stats = { ...existing.stats, ...match.stats };
      existing.round ??= match.round;
      existing.stage ??= match.stage;
      existing.kickoff ??= match.kickoff;
    }
    return [...unique.values()];
  }
}
