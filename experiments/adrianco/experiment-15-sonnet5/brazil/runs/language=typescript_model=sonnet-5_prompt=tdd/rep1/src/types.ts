export interface Match {
  id: string;
  source: string;
  competition: string;
  date: Date;
  season: number;
  round?: string;
  stage?: string;
  homeTeam: string;
  awayTeam: string;
  homeTeamState?: string;
  awayTeamState?: string;
  homeGoals: number;
  awayGoals: number;
  venue?: string;
  extra?: Record<string, number | string>;
}

export interface Player {
  id: string;
  name: string;
  age?: number;
  nationality: string;
  club: string;
  overall?: number;
  potential?: number;
  position?: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
}
