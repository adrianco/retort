export type Competition = "Brasileirão" | "Copa do Brasil" | "Libertadores" | "Brazilian Football";

export interface Match {
  id: string;
  competition: Competition;
  date?: string;
  season?: number;
  round?: string;
  stage?: string;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  stadium?: string;
  source: string;
}

export interface Player {
  id: string;
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
}

export interface MatchFilter {
  team?: string;
  opponent?: string;
  competition?: Competition;
  season?: number;
  from?: string;
  to?: string;
  round?: string;
  stage?: string;
  limit?: number;
}
