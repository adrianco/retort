/**
 * ============================================================================
 * Context Block
 * ----------------------------------------------------------------------------
 * File:    src/types.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: Shared domain types for the in-memory knowledge graph that backs the
 *          MCP server. Defines the unified `Match` shape (normalized across the
 *          six heterogeneous Kaggle CSVs) and the `Player` shape (FIFA data),
 *          plus the small result/aggregate types used by the query layer.
 *
 * Design notes:
 *   - Each source CSV has different columns/encodings, so loaders project every
 *     row into the single `Match` interface below. Display names are preserved
 *     verbatim; `homeKey`/`awayKey` hold the normalized key used for matching.
 *   - Goals are stored as numbers (some sources encode them as "1.0" floats).
 *   - `date` is normalized to ISO `YYYY-MM-DD`; `season` is the numeric year.
 * ============================================================================
 */

/** Canonical competition identifiers used across the loaded datasets. */
export type Competition =
  | 'Brasileirão'
  | 'Copa do Brasil'
  | 'Copa Libertadores'
  | 'Serie B'
  | 'Serie C'
  | string;

/** A single match, normalized from any of the source CSV files. */
export interface Match {
  /** Competition / tournament display name. */
  competition: Competition;
  /** Season year (e.g. 2019). */
  season: number;
  /** Match date as ISO `YYYY-MM-DD`, or null when the source has no usable date. */
  date: string | null;
  /** Round number (league) when available. */
  round: number | null;
  /** Tournament stage (cup/knockout) when available, e.g. "final". */
  stage: string | null;
  /** Home team display name, as it appears in the source. */
  homeTeam: string;
  /** Away team display name, as it appears in the source. */
  awayTeam: string;
  /** Normalized lookup key for the home team. */
  homeKey: string;
  /** Normalized lookup key for the away team. */
  awayKey: string;
  /** Goals scored by the home team. */
  homeGoal: number;
  /** Goals scored by the away team. */
  awayGoal: number;
  /** State abbreviation of the home team, when provided. */
  homeState: string | null;
  /** State abbreviation of the away team, when provided. */
  awayState: string | null;
  /** Stadium / arena name, when provided. */
  arena: string | null;
  /** Source CSV file the match came from. */
  source: string;
}

/** A FIFA player record. */
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
  height: string | null;
  weight: string | null;
  /** Normalized key for the player's club, for cross-dataset joins. */
  clubKey: string;
}

/** Win / draw / loss / goals aggregate for a team (or a slice thereof). */
export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
  winRate: number;
}

/** A single row in a computed league table. */
export interface StandingRow extends TeamRecord {
  position: number;
  goalDifference: number;
}
