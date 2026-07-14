export type Competition =
  | "Brasileirao"
  | "CopaDoBrasil"
  | "Libertadores"
  | "BRDataset"
  | "BrasileiraoHistorical";

export interface Match {
  id: string;
  competition: Competition;
  competitionLabel: string;
  season: number | null;
  round: string | null;
  stage: string | null;
  date: string; // ISO yyyy-mm-dd; empty if unknown
  time: string | null;
  homeTeam: string; // normalized
  awayTeam: string; // normalized
  homeTeamRaw: string;
  awayTeamRaw: string;
  homeTeamState: string | null;
  awayTeamState: string | null;
  homeGoals: number | null;
  awayGoals: number | null;
  arena: string | null;
  // Extended stats (BR-Football-Dataset)
  homeCorners?: number | null;
  awayCorners?: number | null;
  homeShots?: number | null;
  awayShots?: number | null;
  homeAttacks?: number | null;
  awayAttacks?: number | null;
  htResult?: string | null;
  atResult?: string | null;
  totalCorners?: number | null;
}

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
  // Selected skill ratings
  crossing: number | null;
  finishing: number | null;
  dribbling: number | null;
  shortPassing: number | null;
  longPassing: number | null;
  acceleration: number | null;
  sprintSpeed: number | null;
  stamina: number | null;
  strength: number | null;
  shotPower: number | null;
}

export interface Dataset {
  matches: Match[];
  players: Player[];
}
