/**
 * ============================================================================
 * File: src/loader.ts
 * Project: Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * Context:
 *   Loads the six provided Kaggle CSV files from data/kaggle/ and converts
 *   each row into the normalized Match / Player shapes defined in types.ts.
 *   Each source has a slightly different schema, so there is one parser per
 *   file. All parsers route raw names/dates/numbers through src/normalize.ts
 *   so that downstream code sees a single consistent representation.
 *
 *   CSV parsing uses `csv-parse` (sync) with BOM handling enabled, which is
 *   required for fifa_data.csv (UTF-8 BOM + an unnamed leading index column).
 * ============================================================================
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "csv-parse/sync";
import type { Match, Player } from "./types.js";
import {
  extractState,
  parseDate,
  parseInteger,
  parseNumber,
  parseYear,
  teamDisplayName,
  teamKey,
} from "./normalize.js";

type Row = Record<string, string>;

function readCsv(path: string): Row[] {
  const content = readFileSync(path, "utf-8");
  return parse(content, {
    columns: true,
    bom: true,
    skip_empty_lines: true,
    relax_quotes: true,
    relax_column_count: true,
    trim: true,
  }) as Row[];
}

function makeMatch(
  competition: string,
  source: string,
  rawHome: string,
  rawAway: string,
  homeGoals: number | null,
  awayGoals: number | null,
  date: string | null,
  season: number | null,
  round: string | null,
  stage: string | null,
  extra?: Partial<Match> & { homeState?: string; awayState?: string },
): Match {
  const homeState = extra?.homeState || extractState(rawHome);
  const awayState = extra?.awayState || extractState(rawAway);
  return {
    competition,
    source,
    date,
    season,
    round,
    stage,
    homeTeam: teamDisplayName(rawHome),
    awayTeam: teamDisplayName(rawAway),
    homeTeamKey: teamKey(rawHome, homeState),
    awayTeamKey: teamKey(rawAway, awayState),
    homeGoals,
    awayGoals,
    ...extra,
    homeState,
    awayState,
  };
}

function loadBrasileirao(dir: string): Match[] {
  const file = "Brasileirao_Matches.csv";
  return readCsv(join(dir, file)).map((r) => {
    const date = parseDate(r.datetime);
    return makeMatch(
      "Brasileirão Série A",
      file,
      r.home_team,
      r.away_team,
      parseInteger(r.home_goal),
      parseInteger(r.away_goal),
      date,
      parseYear(date, r.season),
      r.round ? `${r.round}` : null,
      null,
      { homeState: r.home_team_state || undefined, awayState: r.away_team_state || undefined },
    );
  });
}

function loadCup(dir: string): Match[] {
  const file = "Brazilian_Cup_Matches.csv";
  return readCsv(join(dir, file)).map((r) => {
    const date = parseDate(r.datetime);
    return makeMatch(
      "Copa do Brasil",
      file,
      r.home_team,
      r.away_team,
      parseInteger(r.home_goal),
      parseInteger(r.away_goal),
      date,
      parseYear(date, r.season),
      r.round ? `${r.round}` : null,
      null,
    );
  });
}

function loadLibertadores(dir: string): Match[] {
  const file = "Libertadores_Matches.csv";
  return readCsv(join(dir, file)).map((r) => {
    const date = parseDate(r.datetime);
    return makeMatch(
      "Copa Libertadores",
      file,
      r.home_team,
      r.away_team,
      parseInteger(r.home_goal),
      parseInteger(r.away_goal),
      date,
      parseYear(date, r.season),
      null,
      r.stage || null,
    );
  });
}

/** Map the BR-Football-Dataset tournament column to a canonical competition. */
function canonicalTournament(raw: string): string {
  const t = (raw || "").toLowerCase();
  if (t.includes("copa do brasil")) return "Copa do Brasil";
  if (t.includes("libertadores")) return "Copa Libertadores";
  if (t.includes("serie a")) return "Brasileirão Série A";
  if (t.includes("serie b")) return "Brasileirão Série B";
  if (t.includes("serie c")) return "Brasileirão Série C";
  return raw || "Unknown";
}

function loadExtended(dir: string): Match[] {
  const file = "BR-Football-Dataset.csv";
  return readCsv(join(dir, file))
    .map((r) => {
      const date = parseDate(r.date);
      const competition = canonicalTournament(r.tournament);
      return makeMatch(
      competition,
      file,
      r.home,
      r.away,
      parseInteger(r.home_goal),
      parseInteger(r.away_goal),
      date,
      parseYear(date, null),
      null,
      null,
      {
        stats: {
          homeCorners: parseNumber(r.home_corner) ?? undefined,
          awayCorners: parseNumber(r.away_corner) ?? undefined,
          totalCorners: parseNumber(r.total_corners) ?? undefined,
          homeAttacks: parseNumber(r.home_attack) ?? undefined,
          awayAttacks: parseNumber(r.away_attack) ?? undefined,
          homeShots: parseNumber(r.home_shots) ?? undefined,
          awayShots: parseNumber(r.away_shots) ?? undefined,
          halfTimeHomeResult: r.ht_result || undefined,
          halfTimeAwayResult: r.at_result || undefined,
        },
      },
    );
    })
    // Série A and Copa do Brasil are already provided by the dedicated, more
    // consistently-named files; this dataset's looser naming would double-count
    // those fixtures, so keep only the competitions unique to it (Série B/C).
    .filter((m) => m.competition === "Brasileirão Série B" || m.competition === "Brasileirão Série C");
}

function loadHistorical(dir: string): Match[] {
  const file = "novo_campeonato_brasileiro.csv";
  return readCsv(join(dir, file)).map((r) => {
    const date = parseDate(r.Data);
    return makeMatch(
      "Brasileirão Série A",
      file,
      r.Equipe_mandante,
      r.Equipe_visitante,
      parseInteger(r.Gols_mandante),
      parseInteger(r.Gols_visitante),
      date,
      parseYear(date, r.Ano),
      r.Rodada ? `${r.Rodada}` : null,
      null,
      {
        homeState: r.Mandante_UF || undefined,
        awayState: r.Visitante_UF || undefined,
        venue: r.Arena || undefined,
      },
    );
  });
}

function loadPlayers(dir: string): Player[] {
  const file = "fifa_data.csv";
  return readCsv(join(dir, file))
    .map((r): Player | null => {
      const id = parseInteger(r.ID);
      if (id === null || !r.Name) return null;
      const club = r.Club || "";
      return {
        id,
        name: r.Name,
        age: parseInteger(r.Age),
        nationality: r.Nationality || "",
        overall: parseInteger(r.Overall),
        potential: parseInteger(r.Potential),
        club,
        clubKey: club ? teamKey(club) : "",
        position: r.Position || "",
        jerseyNumber: parseInteger(r["Jersey Number"]),
        height: r.Height || "",
        weight: r.Weight || "",
        preferredFoot: r["Preferred Foot"] || "",
      };
    })
    .filter((p): p is Player => p !== null);
}

export interface LoadedData {
  matches: Match[];
  players: Player[];
}

/**
 * The five match files overlap heavily (e.g. 2019 Brasileirão appears in the
 * historical file, the Brasileirão file AND the extended-stats file). Counting
 * those copies would treble league points and head-to-head tallies, so we
 * collapse records describing the same fixture into one, keeping the most
 * complete fields (round/stage/venue/stats) across the duplicates.
 */
function dedupeKey(m: Match): string {
  // A given fixture is identified by competition + season + the ordered team
  // pair + stage. Date is deliberately excluded because the same match carries
  // slightly different dates across sources; round is excluded because some
  // sources omit it (which would defeat the merge). Stage is included so a
  // group-stage meeting is not merged with a knockout leg between the same
  // teams in the same season (relevant for Libertadores).
  return [
    m.competition,
    m.season ?? "",
    m.homeTeamKey,
    m.awayTeamKey,
    m.stage ?? "",
  ].join("|");
}

function mergeMatch(into: Match, from: Match): void {
  into.round ??= from.round;
  into.stage ??= from.stage;
  into.season ??= from.season;
  into.venue ??= from.venue;
  into.homeState ??= from.homeState;
  into.awayState ??= from.awayState;
  if (!into.stats && from.stats) into.stats = from.stats;
}

function dedupeMatches(matches: Match[]): Match[] {
  const byKey = new Map<string, Match>();
  const unkeyed: Match[] = [];
  for (const m of matches) {
    // Without a season we can't reliably identify the fixture, so keep as-is.
    if (m.season === null) {
      unkeyed.push(m);
      continue;
    }
    const key = dedupeKey(m);
    const existing = byKey.get(key);
    if (existing) {
      mergeMatch(existing, m);
      // Prefer a record that actually has a date.
      if (!existing.date && m.date) existing.date = m.date;
    } else {
      byKey.set(key, m);
    }
  }
  return [...byKey.values(), ...unkeyed];
}

/** Load every dataset from the given data/kaggle directory. */
export function loadAll(dataDir: string): LoadedData {
  const matches = dedupeMatches([
    ...loadBrasileirao(dataDir),
    ...loadCup(dataDir),
    ...loadLibertadores(dataDir),
    ...loadExtended(dataDir),
    ...loadHistorical(dataDir),
  ]);
  const players = loadPlayers(dataDir);
  return { matches, players };
}
