import { join } from "node:path";
import { readCsv, type CsvRow } from "./csv.js";
import {
  MATCH_SOURCES,
  type DatasetSummary,
  type MatchMetrics,
  type MatchSource,
  type Player,
  type SoccerMatch,
} from "./types.js";
import {
  displayTeamName,
  foldText,
  normalizeCompetition,
  optionalNumber,
  parseDate,
  requiredNumber,
  teamKey,
} from "./normalize.js";

export interface SoccerData {
  matches: SoccerMatch[];
  players: Player[];
  summary: DatasetSummary;
}

interface MatchDraft extends Omit<SoccerMatch, "id" | "sources"> {
  source: MatchSource;
}

const PLAYER_ATTRIBUTES = [
  "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
  "Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed",
  "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength",
  "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
  "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
  "GKKicking", "GKPositioning", "GKReflexes",
] as const;

function compactMetrics(metrics: MatchMetrics): MatchMetrics | undefined {
  return Object.keys(metrics).length === 0 ? undefined : metrics;
}

function commonDraft(
  row: CsvRow,
  source: MatchSource,
  competition: string | undefined,
  dateValue: string | undefined,
  homeValue: string | undefined,
  awayValue: string | undefined,
  homeGoalsValue: string | undefined,
  awayGoalsValue: string | undefined,
  seasonValue?: string,
): MatchDraft | null {
  const date = parseDate(dateValue ?? "");
  const homeGoals = requiredNumber(homeGoalsValue);
  const awayGoals = requiredNumber(awayGoalsValue);
  if (!date || !homeValue || !awayValue || homeGoals === null || awayGoals === null) return null;

  const season = optionalNumber(seasonValue) ?? Number(date.slice(0, 4));
  if (!Number.isInteger(season)) return null;

  return {
    source,
    competition: normalizeCompetition(competition ?? "Unknown competition"),
    date,
    season,
    homeTeam: displayTeamName(homeValue),
    homeTeamKey: teamKey(homeValue),
    awayTeam: displayTeamName(awayValue),
    awayTeamKey: teamKey(awayValue),
    homeGoals,
    awayGoals,
  };
}

function loadBrasileirao(rows: CsvRow[]): MatchDraft[] {
  return rows.flatMap((row) => {
    const draft = commonDraft(
      row, "Brasileirao_Matches.csv", "Brasileirão Série A", row.datetime,
      row.home_team, row.away_team, row.home_goal, row.away_goal, row.season,
    );
    if (!draft) return [];
    return [{
      ...draft,
      ...(row.home_team_state ? { homeState: row.home_team_state } : {}),
      ...(row.away_team_state ? { awayState: row.away_team_state } : {}),
      ...(row.round ? { round: row.round } : {}),
    }];
  });
}

function loadBrazilianCup(rows: CsvRow[]): MatchDraft[] {
  return rows.flatMap((row) => {
    const draft = commonDraft(
      row, "Brazilian_Cup_Matches.csv", "Copa do Brasil", row.datetime,
      row.home_team, row.away_team, row.home_goal, row.away_goal, row.season,
    );
    return draft ? [{ ...draft, ...(row.round ? { round: row.round } : {}) }] : [];
  });
}

function loadLibertadores(rows: CsvRow[]): MatchDraft[] {
  return rows.flatMap((row) => {
    const draft = commonDraft(
      row, "Libertadores_Matches.csv", "Copa Libertadores", row.datetime,
      row.home_team, row.away_team, row.home_goal, row.away_goal, row.season,
    );
    return draft ? [{ ...draft, ...(row.stage ? { stage: row.stage } : {}) }] : [];
  });
}

function loadExtended(rows: CsvRow[]): MatchDraft[] {
  return rows.flatMap((row) => {
    const draft = commonDraft(
      row, "BR-Football-Dataset.csv", row.tournament, row.date,
      row.home, row.away, row.home_goal, row.away_goal,
    );
    if (!draft) return [];
    const metrics = compactMetrics({
      ...(optionalNumber(row.home_corner) !== undefined ? { homeCorners: optionalNumber(row.home_corner) } : {}),
      ...(optionalNumber(row.away_corner) !== undefined ? { awayCorners: optionalNumber(row.away_corner) } : {}),
      ...(optionalNumber(row.home_attack) !== undefined ? { homeAttacks: optionalNumber(row.home_attack) } : {}),
      ...(optionalNumber(row.away_attack) !== undefined ? { awayAttacks: optionalNumber(row.away_attack) } : {}),
      ...(optionalNumber(row.home_shots) !== undefined ? { homeShots: optionalNumber(row.home_shots) } : {}),
      ...(optionalNumber(row.away_shots) !== undefined ? { awayShots: optionalNumber(row.away_shots) } : {}),
      ...(optionalNumber(row.total_corners) !== undefined ? { totalCorners: optionalNumber(row.total_corners) } : {}),
    });
    return [{
      ...draft,
      ...(row.time ? { kickoff: row.time } : {}),
      ...(metrics ? { metrics } : {}),
    }];
  });
}

function loadHistorical(rows: CsvRow[]): MatchDraft[] {
  return rows.flatMap((row) => {
    const draft = commonDraft(
      row, "novo_campeonato_brasileiro.csv", "Brasileirão Série A", row.Data,
      row.Equipe_mandante, row.Equipe_visitante, row.Gols_mandante, row.Gols_visitante, row.Ano,
    );
    if (!draft) return [];
    return [{
      ...draft,
      ...(row.Rodada ? { round: row.Rodada } : {}),
      ...(row.Mandante_UF ? { homeState: row.Mandante_UF } : {}),
      ...(row.Visitante_UF ? { awayState: row.Visitante_UF } : {}),
      ...(row.Arena ? { stadium: row.Arena } : {}),
    }];
  });
}

function mergeMatches(drafts: MatchDraft[]): SoccerMatch[] {
  const unique = new Map<string, SoccerMatch>();
  const comparable = new Map<string, SoccerMatch[]>();
  for (const draft of drafts) {
    const comparisonKey = [
      foldText(draft.competition), draft.season, draft.homeTeamKey, draft.awayTeamKey,
      draft.homeGoals, draft.awayGoals,
    ].join("|");
    const candidates = comparable.get(comparisonKey) ?? [];
    const draftTime = Date.parse(`${draft.date}T00:00:00Z`);
    const existing = candidates.find((candidate) => Math.abs(Date.parse(`${candidate.date}T00:00:00Z`) - draftTime) <= 86_400_000);
    if (existing) {
      if (!existing.sources.includes(draft.source)) existing.sources.push(draft.source);
      existing.round ??= draft.round;
      existing.stage ??= draft.stage;
      existing.stadium ??= draft.stadium;
      existing.metrics ??= draft.metrics;
      existing.homeState ??= draft.homeState;
      existing.awayState ??= draft.awayState;
      continue;
    }
    const { source, ...match } = draft;
    const id = `match:${unique.size + 1}`;
    const created = { ...match, id, sources: [source] };
    unique.set(id, created);
    candidates.push(created);
    comparable.set(comparisonKey, candidates);
  }
  return [...unique.values()].sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));
}

function loadPlayers(rows: CsvRow[]): Player[] {
  return rows.flatMap((row) => {
    const id = requiredNumber(row.ID);
    if (id === null || !row.Name) return [];
    const attributes: Record<string, number> = {};
    for (const attribute of PLAYER_ATTRIBUTES) {
      const value = optionalNumber(row[attribute]);
      if (value !== undefined) attributes[attribute] = value;
    }
    return [{
      id,
      name: row.Name,
      nationality: row.Nationality || "Unknown",
      attributes,
      ...(optionalNumber(row.Age) !== undefined ? { age: optionalNumber(row.Age) } : {}),
      ...(optionalNumber(row.Overall) !== undefined ? { overall: optionalNumber(row.Overall) } : {}),
      ...(optionalNumber(row.Potential) !== undefined ? { potential: optionalNumber(row.Potential) } : {}),
      ...(row.Club ? { club: row.Club, clubKey: teamKey(row.Club) } : {}),
      ...(row.Position ? { position: row.Position } : {}),
      ...(optionalNumber(row["Jersey Number"]) !== undefined ? { jerseyNumber: optionalNumber(row["Jersey Number"]) } : {}),
      ...(row.Height ? { height: row.Height } : {}),
      ...(row.Weight ? { weight: row.Weight } : {}),
    }];
  });
}

export function loadSoccerData(dataDirectory = join(process.cwd(), "data", "kaggle")): SoccerData {
  const sourceRows: Record<string, number> = {};
  const read = (source: MatchSource): CsvRow[] => {
    const rows = readCsv(join(dataDirectory, source));
    sourceRows[source] = rows.length;
    return rows;
  };

  const drafts = [
    ...loadBrasileirao(read("Brasileirao_Matches.csv")),
    ...loadBrazilianCup(read("Brazilian_Cup_Matches.csv")),
    ...loadLibertadores(read("Libertadores_Matches.csv")),
    ...loadExtended(read("BR-Football-Dataset.csv")),
    ...loadHistorical(read("novo_campeonato_brasileiro.csv")),
  ];
  const playerRows = readCsv(join(dataDirectory, "fifa_data.csv"));
  sourceRows["fifa_data.csv"] = playerRows.length;
  const matches = mergeMatches(drafts);
  const players = loadPlayers(playerRows);
  const teamKeys = new Set(matches.flatMap((match) => [match.homeTeamKey, match.awayTeamKey]));
  const seasons = matches.map((match) => match.season);

  return {
    matches,
    players,
    summary: {
      rawMatchRows: MATCH_SOURCES.reduce((total, source) => total + (sourceRows[source] ?? 0), 0),
      uniqueMatches: matches.length,
      players: players.length,
      teams: teamKeys.size,
      competitions: new Set(matches.map((match) => foldText(match.competition))).size,
      seasons: seasons.length > 0 ? { first: Math.min(...seasons), last: Math.max(...seasons) } : null,
      sourceRows,
    },
  };
}
