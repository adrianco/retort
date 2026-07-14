export type Competition =
  | 'Brasileirao'
  | 'Copa do Brasil'
  | 'Libertadores'
  | 'BR-Football'
  | 'Historical';

export interface Match {
  date: string;
  datetime?: string;
  homeTeam: string;
  homeTeamNorm: string;
  awayTeam: string;
  awayTeamNorm: string;
  homeGoals: number;
  awayGoals: number;
  season: number;
  competition: Competition;
  round?: string | number;
  stage?: string;
  arena?: string;
  homeState?: string;
  awayState?: string;
  homeCorner?: number;
  awayCorner?: number;
  homeShots?: number;
  awayShots?: number;
  homeAttack?: number;
  awayAttack?: number;
  htResult?: string;
  atResult?: string;
  totalCorners?: number;
}

export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality?: string;
  overall?: number;
  potential?: number;
  club?: string;
  clubNorm?: string;
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

export interface TeamStats {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  winRate: number;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  totalMatches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  matches: Match[];
}

export interface StandingsEntry extends TeamStats {
  position: number;
}
