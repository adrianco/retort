export type Competition =
  | 'Brasileirão'
  | 'Copa do Brasil'
  | 'Libertadores'
  | 'Other';

export interface Match {
  /** Source CSV file. */
  source: string;
  /** Normalized competition name. */
  competition: Competition;
  /** Original competition / tournament string when available. */
  tournamentRaw?: string;
  /** ISO date string (YYYY-MM-DD). */
  date: string;
  /** Optional kickoff time. */
  time?: string;
  /** Home team display name (raw). */
  homeTeam: string;
  /** Away team display name (raw). */
  awayTeam: string;
  /** Normalized home team key. */
  homeKey: string;
  /** Normalized away team key. */
  awayKey: string;
  homeGoals: number;
  awayGoals: number;
  season?: number;
  round?: string;
  stage?: string;
  arena?: string;
  homeState?: string;
  awayState?: string;
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
  htResult?: string;
  atResult?: string;
}

export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality?: string;
  overall?: number;
  potential?: number;
  club?: string;
  /** Normalized club key. */
  clubKey?: string;
  position?: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  preferredFoot?: string;
  workRate?: string;
  value?: string;
  wage?: string;
}

export interface DataStore {
  matches: Match[];
  players: Player[];
}
