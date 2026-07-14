/**
 * Domain types for the Brazilian Soccer MCP server.
 *
 * All match records loaded from the various CSV files are normalized into a
 * single {@link Match} shape so that queries can operate uniformly across
 * datasets. Player records from the FIFA dataset become {@link Player}.
 */

/** Canonical competition identifiers used across the datasets. */
export type Competition =
  | "Brasileirão Série A"
  | "Copa do Brasil"
  | "Copa Libertadores"
  | "Serie A"
  | "Serie B"
  | "Serie C";

/** A single soccer match, normalized from any of the source CSV files. */
export interface Match {
  /** Canonical competition name. */
  competition: string;
  /** Source CSV file the record came from (provenance / de-duplication). */
  source: string;
  /** Parsed match date, or null when the source has no usable date. */
  date: Date | null;
  /** Original date string as found in the source file. */
  dateRaw: string | null;
  /** Season / year of the competition, or null when unknown. */
  season: number | null;
  /** League round (e.g. "22"), or null. */
  round: string | null;
  /** Knockout stage (e.g. "final", "group stage"), or null. */
  stage: string | null;
  /** Display name of the home team (with any state/country suffix removed). */
  homeTeam: string;
  /** Display name of the away team. */
  awayTeam: string;
  /** Raw home team string exactly as it appears in the source. */
  homeTeamRaw: string;
  /** Raw away team string exactly as it appears in the source. */
  awayTeamRaw: string;
  /** Goals scored by the home team, or null when the match has no result. */
  homeGoals: number | null;
  /** Goals scored by the away team, or null. */
  awayGoals: number | null;
}

/** A player from the FIFA dataset (subset of the ~90 available columns). */
export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  position: string;
  jerseyNumber: number | null;
  height: string;
  weight: string;
  preferredFoot: string;
  value: string;
  wage: string;
}

/** Aggregated win/draw/loss record for a team. */
export interface TeamRecord {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

/** A single row in a calculated league standings table. */
export interface StandingsRow extends TeamRecord {
  position: number;
  goalDifference: number;
}
