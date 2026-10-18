/** A single match from any of the source files, after normalization. */
export interface Match {
  id: string;
  /** ISO date, YYYY-MM-DD. */
  date: string;
  season: number;
  /** Display label, e.g. "Brasileirão Série A", "Copa do Brasil", "Copa Libertadores". */
  competition: string;
  /** Round or stage label, may be empty when the source has none. */
  round: string;
  home: string;
  away: string;
  homeGoals: number;
  awayGoals: number;
  /** Source file name the match was loaded from. */
  source: string;
}

/** A player row from the FIFA dataset. */
export interface Player {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jerseyNumber?: number;
  height: string;
  weight: string;
  preferredFoot: string;
  value: string;
}

export interface Dataset {
  matches: Match[];
  players: Player[];
}
