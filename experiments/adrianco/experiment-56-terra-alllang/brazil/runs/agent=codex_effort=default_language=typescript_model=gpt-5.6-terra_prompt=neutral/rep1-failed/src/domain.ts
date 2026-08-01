export type Competition = "Brasileirão" | "Copa do Brasil" | "Libertadores" | "Brazilian Football";

export interface Match {
  source: string;
  competition: Competition;
  date: string;
  season?: number;
  round?: string;
  stage?: string;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  extras?: Record<string, number>;
}

export interface Player {
  id: string;
  name: string;
  age?: number;
  nationality: string;
  overall?: number;
  potential?: number;
  club: string;
  position: string;
  jerseyNumber?: string;
}

export interface TeamRecord {
  team: string; matches: number; wins: number; draws: number; losses: number;
  goalsFor: number; goalsAgainst: number; points: number; winRate: number;
}
