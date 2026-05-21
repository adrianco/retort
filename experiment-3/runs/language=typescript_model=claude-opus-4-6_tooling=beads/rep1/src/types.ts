export interface Match {
  date: string;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  season: number;
  competition: string;
  round?: string;
  stage?: string;
  stadium?: string;
  homeTeamState?: string;
  awayTeamState?: string;
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
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
  value?: string;
  wage?: string;
  crossing?: number;
  finishing?: number;
  headingAccuracy?: number;
  shortPassing?: number;
  dribbling?: number;
  curve?: number;
  longPassing?: number;
  ballControl?: number;
  acceleration?: number;
  sprintSpeed?: number;
  agility?: number;
  reactions?: number;
  shotPower?: number;
  stamina?: number;
  strength?: number;
  longShots?: number;
  aggression?: number;
  interceptions?: number;
  positioning?: number;
  vision?: number;
  penalties?: number;
  composure?: number;
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
}

export interface DataStore {
  matches: Match[];
  players: Player[];
}
