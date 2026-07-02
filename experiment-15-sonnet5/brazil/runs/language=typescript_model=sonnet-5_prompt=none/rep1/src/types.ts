export type Competition =
  | "Brasileirao"
  | "Copa do Brasil"
  | "Libertadores"
  | "BR-Football"
  | "Historical-Brasileirao";

/** A team name broken down into a display form and normalized keys used for
 * cross-dataset matching (see src/normalize.ts). */
export interface TeamKey {
  raw: string;
  display: string;
  baseKey: string;
  state: string | null;
  key: string;
}

export interface MatchExtraStats {
  homeCorners: number | null;
  awayCorners: number | null;
  homeShots: number | null;
  awayShots: number | null;
  homeAttacks: number | null;
  awayAttacks: number | null;
}

export interface Match {
  id: string;
  source: Competition;
  /** Human readable competition/tournament label, e.g. "Brasileirao Serie A", "Serie B". */
  competition: string;
  season: number | null;
  round: string | null;
  stage: string | null;
  date: Date | null;
  dateRaw: string;
  homeTeam: TeamKey;
  awayTeam: TeamKey;
  homeGoals: number | null;
  awayGoals: number | null;
  stadium: string | null;
  extra: MatchExtraStats | null;
}

export interface Player {
  id: string;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  position: string;
  jerseyNumber: number | null;
  preferredFoot: string | null;
  height: string | null;
  weight: string | null;
  valueRaw: string | null;
  wageRaw: string | null;
}

export interface Dataset {
  matches: Match[];
  players: Player[];
}
