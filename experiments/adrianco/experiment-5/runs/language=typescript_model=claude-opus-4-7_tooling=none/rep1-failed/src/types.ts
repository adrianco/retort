export type Competition =
  | 'Brasileirao'
  | 'Copa do Brasil'
  | 'Libertadores'
  | 'BR-Football'
  | 'Historical Brasileirao';

export interface Match {
  competition: Competition;
  season: number;
  date: string;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  round?: string;
  stage?: string;
  homeState?: string;
  awayState?: string;
  arena?: string;
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  totalCorners?: number;
}

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
  height?: string;
  weight?: string;
  preferredFoot?: string;
}

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
