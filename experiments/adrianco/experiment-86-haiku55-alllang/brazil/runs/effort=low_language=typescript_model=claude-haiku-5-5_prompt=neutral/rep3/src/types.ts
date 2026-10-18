/*
 * Context: Shared domain types. A Match is the unified record produced from all source
 * files; a Player comes only from the FIFA dataset. `homeKey`/`awayKey` are the
 * canonical team keys used for every lookup.
 */

export type Venue = 'home' | 'away' | 'any';

export interface Match {
  id: string;
  date: string; // YYYY-MM-DD
  season: number | null;
  competition: string; // canonical competition name, e.g. "Brasileirão Série A"
  round: string | null;
  home: string; // display name
  away: string; // display name
  homeKey: string;
  awayKey: string;
  homeGoals: number;
  awayGoals: number;
  source: string; // originating file
}

export interface Player {
  id: string;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  clubKey: string;
  position: string;
  jerseyNumber: number | null;
  preferredFoot: string;
  heightCm: number | null;
  weightKg: number | null;
  value: string;
  wage: string;
  attributes: Record<string, number>;
}

export interface Dataset {
  matches: Match[];
  players: Player[];
  /** Canonical team key -> display name seen most recently. */
  teams: Map<string, string>;
  loadedFiles: string[];
}
