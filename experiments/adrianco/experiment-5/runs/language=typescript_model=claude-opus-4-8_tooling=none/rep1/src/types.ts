/**
 * Context
 * -------
 * Core domain types for the Brazilian Soccer MCP server.
 *
 * The six source CSV files use different schemas, naming conventions and date
 * formats. To make them queryable in a uniform way, every match row is mapped
 * into a single `Match` shape and every FIFA row into a single `Player` shape.
 * Normalization (team names, dates) happens at load time in `dataStore.ts` so
 * that the query layer can operate on clean, consistent data.
 */

/** Canonical competition identifiers used across the unified dataset. */
export type Competition =
  | "Brasileirão Série A"
  | "Brasileirão Série B"
  | "Brasileirão Série C"
  | "Copa do Brasil"
  | "Copa Libertadores";

/** A single match, normalized from any of the source match CSVs. */
export interface Match {
  /** Competition this match belongs to. */
  competition: Competition;
  /** Display name of the home team (state/country suffix stripped). */
  homeTeam: string;
  /** Display name of the away team. */
  awayTeam: string;
  /** Original (raw) home team string from the source file. */
  homeTeamRaw: string;
  /** Original (raw) away team string from the source file. */
  awayTeamRaw: string;
  /** Goals scored by the home team, or null if unknown. */
  homeGoal: number | null;
  /** Goals scored by the away team, or null if unknown. */
  awayGoal: number | null;
  /** Season year (e.g. 2019). */
  season: number | null;
  /** ISO date string (YYYY-MM-DD) when known. */
  date: string | null;
  /** Round number (league) when applicable. */
  round: number | null;
  /** Stage / phase text (cup & continental competitions). */
  stage: string | null;
  /** Stadium / arena, when available. */
  arena: string | null;
  /** Which source file the row came from. */
  source: string;
}

/** A FIFA player record, normalized from `fifa_data.csv`. */
export interface Player {
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
  value: string;
  wage: string;
  preferredFoot: string;
}

/** Win / draw / loss + goals aggregate used by team & competition stats. */
export interface Record {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}
