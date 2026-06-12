/**
 * Core domain types for the Brazilian Soccer knowledge base.
 *
 * A `Match` is the normalized representation of a single game drawn from any of
 * the provided CSV datasets. A `Player` is a single row from the FIFA dataset.
 * Both keep the original ("raw") names alongside normalized lookup keys so that
 * team-name variations across datasets ("Palmeiras-SP" vs "Palmeiras") can be
 * matched while still displaying the friendliest available name.
 */

/** Canonical competition identifiers used across all datasets. */
export type Competition =
  | "Brasileirão Série A"
  | "Brasileirão Série B"
  | "Brasileirão Série C"
  | "Copa do Brasil"
  | "Copa Libertadores";

export interface MatchStats {
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
  totalCorners?: number;
  halfTimeHomeResult?: string;
  halfTimeAwayResult?: string;
}

export interface Match {
  /** Canonical competition name. */
  competition: string;
  /** Match date, or null when the source row has no parseable date. */
  date: Date | null;
  /** Season year. */
  season: number | null;
  /** Round label/number where available (league play, cup rounds). */
  round?: string;
  /** Tournament stage where available (e.g. Libertadores "group stage"). */
  stage?: string;
  /** Normalized lookup key for the home team (accent-free, lower case). */
  homeKey: string;
  /** Normalized lookup key for the away team. */
  awayKey: string;
  /** Display name for the home team (raw, original casing/accents). */
  homeTeam: string;
  /** Display name for the away team. */
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  /** Stadium/arena where available. */
  arena?: string;
  /** Identifier of the dataset this match came from. */
  source: string;
  /** Extended statistics where available (BR-Football-Dataset). */
  stats?: MatchStats;
}

export interface Player {
  id: number;
  name: string;
  /** Normalized lookup key for the player name. */
  nameKey: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  /** Normalized lookup key for the club. */
  clubKey: string;
  position: string;
  jerseyNumber: number | null;
  height: string;
  weight: string;
}

/** Aggregated win/draw/loss/goal record for a team over a set of matches. */
export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}
