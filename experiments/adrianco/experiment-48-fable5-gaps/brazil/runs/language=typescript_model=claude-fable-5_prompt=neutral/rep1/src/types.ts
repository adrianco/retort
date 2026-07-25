import type { TeamName } from "./teams.js";

/** Competitions covered by the datasets. */
export type Competition =
  | "Brasileirão Série A"
  | "Brasileirão Série B"
  | "Brasileirão Série C"
  | "Copa do Brasil"
  | "Copa Libertadores";

export interface MatchStats {
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  halfTimeHome?: string;
  halfTimeAway?: string;
}

export interface Match {
  competition: Competition;
  /** ISO date, e.g. "2019-11-24"; null when the source row had no parsable date. */
  date: string | null;
  season: number | null;
  round: string | null;
  stage: string | null;
  home: TeamName;
  away: TeamName;
  homeGoals: number;
  awayGoals: number;
  stadium: string | null;
  stats: MatchStats | null;
  /** Which CSV files contributed to this (deduplicated) match. */
  sources: string[];
}

export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number;
  potential: number | null;
  club: string;
  position: string;
  jerseyNumber: number | null;
  height: string;
  weight: string;
  preferredFoot: string;
  value: string;
  wage: string;
  skills: Record<string, number>;
}

export interface Dataset {
  matches: Match[];
  players: Player[];
  /** Row counts per source file, before deduplication. */
  fileCounts: Record<string, number>;
  /** Matches merged away as cross-file duplicates. */
  duplicatesMerged: number;
}
