export type Competition =
  | 'Brasileirão'
  | 'Copa do Brasil'
  | 'Copa Libertadores'
  | 'Other';

export interface Match {
  competition: Competition;
  source: string;
  date: string;
  season: number;
  round?: string | number;
  stage?: string;
  homeTeam: string;
  awayTeam: string;
  homeTeamRaw: string;
  awayTeamRaw: string;
  homeTeamState?: string;
  awayTeamState?: string;
  homeGoals: number;
  awayGoals: number;
  arena?: string;
  stats?: MatchStats;
}

export interface MatchStats {
  homeCorners?: number;
  awayCorners?: number;
  totalCorners?: number;
  homeShots?: number;
  awayShots?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  htHomeResult?: string;
  atAwayResult?: string;
}

export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality?: string;
  overall?: number;
  potential?: number;
  club?: string;
  clubNormalized?: string;
  position?: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  preferredFoot?: string;
  value?: string;
  wage?: string;
  workRate?: string;
  bodyType?: string;
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

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  history: Match[];
}
