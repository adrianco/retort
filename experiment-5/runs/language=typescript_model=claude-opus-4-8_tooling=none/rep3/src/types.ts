/**
 * ============================================================================
 * Context: Brazilian Soccer MCP Server — Domain Types
 * ----------------------------------------------------------------------------
 * Purpose : Defines the unified, source-agnostic data models used across the
 *           server. The six provided CSV files use different column names,
 *           encodings and date formats; the loader (dataLoader.ts) normalizes
 *           every match row into the `Match` shape below and every FIFA row
 *           into the `Player` shape, so that the query layer (queries.ts) and
 *           the MCP tools (server.ts) operate on one consistent model.
 * Consumers: dataLoader.ts (produces), queries.ts (consumes), server.ts.
 * ============================================================================
 */

/** A canonical competition label, derived from the source file / tournament column. */
export type Competition =
  | "Brasileirão Série A"
  | "Brasileirão Série B"
  | "Brasileirão Série C"
  | "Copa do Brasil"
  | "Copa Libertadores"
  | "Brasileirão (Histórico)";

/** A single match, unified across all five match datasets. */
export interface Match {
  /** Canonical competition name. */
  competition: string;
  /** Source CSV filename the row came from (provenance / debugging). */
  source: string;
  /** Match date as ISO `YYYY-MM-DD`, or null when the source had no usable date. */
  date: string | null;
  /** Season year (e.g. 2019), or null when unknown. */
  season: number | null;
  /** Round / matchday label, or null. */
  round: string | null;
  /** Tournament stage (e.g. "group stage", "final"), or null. */
  stage: string | null;
  /** Display name of the home team, with state/country suffix stripped. */
  homeTeam: string;
  /** Display name of the away team, with state/country suffix stripped. */
  awayTeam: string;
  /** Home goals, or null if the score is unknown. */
  homeGoals: number | null;
  /** Away goals, or null if the score is unknown. */
  awayGoals: number | null;
  /** Home team state/country abbreviation when available. */
  homeState: string | null;
  /** Away team state/country abbreviation when available. */
  awayState: string | null;
  /** Stadium / arena when available. */
  venue: string | null;
}

/** A FIFA player record (subset of the many available columns). */
export interface Player {
  id: number | null;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  position: string;
  jerseyNumber: string | null;
  height: string | null;
  weight: string | null;
  value: string | null;
  wage: string | null;
  preferredFoot: string | null;
}

/** Win/draw/loss + goal aggregation for a team over a slice of matches. */
export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
  winRate: number; // 0..1
}

/** A row in a calculated league table. */
export interface StandingRow extends TeamRecord {
  position: number;
  goalDifference: number;
}
