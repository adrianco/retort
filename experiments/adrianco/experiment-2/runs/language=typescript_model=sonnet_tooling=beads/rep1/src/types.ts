export interface Match {
  date: string; // ISO date string
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  competition: string;
  season: number;
  round?: string;
  stage?: string;
  arena?: string;
  // Extended stats (from BR-Football-Dataset)
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
}

export interface Player {
  id: string;
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
  value?: string;
  wage?: string;
}

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
  winRate: number;
}

export interface HeadToHead {
  team1: string;
  team2: string;
  matches: Match[];
  team1Wins: number;
  team2Wins: number;
  draws: number;
}

export interface DataStore {
  matches: Match[];
  players: Player[];
}
