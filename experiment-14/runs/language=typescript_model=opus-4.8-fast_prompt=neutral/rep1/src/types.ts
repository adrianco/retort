/**
 * Brazilian Soccer MCP — Core domain types
 * ----------------------------------------
 * Context: This module defines the in-memory data model shared across the
 * loader, the query store, and the MCP tool layer. Every CSV row from the
 * provided Kaggle datasets is normalized into one of these shapes so that the
 * rest of the system can query matches and players uniformly regardless of the
 * source file's original column names, language, or formatting conventions.
 *
 * Two top-level entities exist:
 *   - `Match`  : a single game from any of the five match datasets.
 *   - `Player` : a single footballer row from the FIFA player dataset.
 */

/** Canonical competition identifiers used across the system. */
export type Competition =
  | "Brasileirão Série A"
  | "Brasileirão Série B"
  | "Brasileirão Série C"
  | "Copa do Brasil"
  | "Copa Libertadores";

/** Result of a match from the home team's perspective. */
export type Outcome = "home" | "away" | "draw";

/**
 * A normalized football match. Optional fields are only populated when the
 * source dataset provides them (e.g. shot/corner stats only exist in the
 * extended BR-Football dataset, `stage` only in Libertadores, etc.).
 */
export interface Match {
  /** Canonical competition name. */
  competition: Competition;
  /** ISO date `YYYY-MM-DD`, or null when the source had no parseable date. */
  date: string | null;
  /** Season / year of the competition. */
  season: number | null;
  /** Round label, when available (e.g. "1", "Final", "Quarterfinals"). */
  round: string | null;
  /** Tournament stage for knockout competitions, when available. */
  stage: string | null;

  /** Canonical home team display name. */
  homeTeam: string;
  /** Canonical home team id (used for matching/indexing). */
  homeTeamId: string;
  /** Canonical away team display name. */
  awayTeam: string;
  /** Canonical away team id. */
  awayTeamId: string;

  /** Goals scored by the home team, or null if unknown. */
  homeGoals: number | null;
  /** Goals scored by the away team, or null if unknown. */
  awayGoals: number | null;

  /** Stadium / arena, when provided. */
  venue: string | null;
  /** Which CSV file this record originated from. */
  source: string;

  /** Extended statistics (BR-Football dataset only). */
  stats?: MatchStats;
}

/** Extended per-match statistics available in the BR-Football dataset. */
export interface MatchStats {
  homeCorners: number | null;
  awayCorners: number | null;
  homeShots: number | null;
  awayShots: number | null;
  homeAttacks: number | null;
  awayAttacks: number | null;
  totalCorners: number | null;
}

/** A normalized FIFA player record. */
export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  /** Canonical id of the club, for cross-referencing with match teams. */
  clubId: string;
  position: string;
  jerseyNumber: number | null;
  height: string;
  weight: string;
  preferredFoot: string;
  value: string;
  wage: string;
}
