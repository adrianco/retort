/**
 * types.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   Shared domain types for the Brazilian Soccer MCP server.
 *
 *   The six provided Kaggle CSVs use different column layouts and naming
 *   conventions. The loader (`data/loader.ts`) normalises all of them into the
 *   two unified shapes defined here — `Match` and `Player` — so that every
 *   query service can operate over a single, consistent in-memory model.
 *
 *   Goals encoded here are always nullable: some historical rows have missing
 *   or unparseable scores, and consumers must handle that explicitly rather
 *   than silently treating a missing score as 0-0.
 * -----------------------------------------------------------------------------
 */

/** Canonical competition labels used across the unified dataset. */
export type Competition =
  | "Brasileirão"
  | "Copa do Brasil"
  | "Libertadores"
  | string; // BR-Football-Dataset contributes other tournament labels verbatim

/** A single match, unified across all match CSV sources. */
export interface Match {
  /** Competition / tournament label. */
  competition: Competition;
  /** Match date as ISO `YYYY-MM-DD`, or null when not parseable. */
  date: string | null;
  /** Season year (e.g. 2019), or null when unknown. */
  season: number | null;
  /** Round label (league round number or cup round name), or null. */
  round: string | null;
  /** Tournament stage (Libertadores), e.g. "group stage", or null. */
  stage: string | null;

  /** Normalised display name of the home team. */
  homeTeam: string;
  /** Normalised display name of the away team. */
  awayTeam: string;
  /** Original, un-normalised home team string from the source file. */
  homeTeamRaw: string;
  /** Original, un-normalised away team string from the source file. */
  awayTeamRaw: string;

  /** Home goals, or null when missing/unparseable. */
  homeGoals: number | null;
  /** Away goals, or null when missing/unparseable. */
  awayGoals: number | null;

  /** Home team state (UF) where available. */
  homeState: string | null;
  /** Away team state (UF) where available. */
  awayState: string | null;
  /** Stadium / arena where available. */
  arena: string | null;

  /** Source CSV file the row came from. */
  source: string;

  /** Optional extended statistics (BR-Football-Dataset only). */
  stats?: MatchStats;
}

/** Extended per-match statistics available only in BR-Football-Dataset.csv. */
export interface MatchStats {
  homeCorners: number | null;
  awayCorners: number | null;
  homeAttacks: number | null;
  awayAttacks: number | null;
  homeShots: number | null;
  awayShots: number | null;
  totalCorners: number | null;
  htResult: string | null;
  atResult: string | null;
}

/** A FIFA player record (subset of the most useful columns). */
export interface Player {
  id: number | null;
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

/** The fully loaded, in-memory dataset. */
export interface Dataset {
  matches: Match[];
  players: Player[];
}
