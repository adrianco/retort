export type Competition =
  | 'Brasileirão Serie A'
  | 'Copa do Brasil'
  | 'Copa Libertadores'
  | 'BR-Football Dataset'
  | 'Brasileirão (Historical 2003-2019)';

export interface Match {
  competition: Competition;
  date: string;
  season: number;
  round?: string | number;
  stage?: string;
  homeTeam: string;
  homeTeamRaw: string;
  homeState?: string;
  awayTeam: string;
  awayTeamRaw: string;
  awayState?: string;
  homeGoals: number;
  awayGoals: number;
  arena?: string;
  homeShots?: number;
  awayShots?: number;
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
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
  position?: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  preferredFoot?: string;
  value?: string;
  wage?: string;
}

export interface DataStore {
  matches: Match[];
  players: Player[];
}

export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}
