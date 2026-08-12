export type Competition =
  | "Brasileirão Serie A"
  | "Copa do Brasil"
  | "Copa Libertadores"
  | string;

export interface MatchSource {
  file: string;
  row: number;
}

export interface MatchStats {
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
  totalCorners?: number;
  halfTimeHomeGoals?: number;
  halfTimeAwayGoals?: number;
  stadium?: string;
}

export interface Match {
  id: string;
  date: string;
  kickoff?: string;
  season: number;
  competition: Competition;
  round?: string;
  stage?: string;
  homeTeam: string;
  homeTeamKey: string;
  awayTeam: string;
  awayTeamKey: string;
  homeGoals: number;
  awayGoals: number;
  stats?: MatchStats;
  sources: MatchSource[];
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
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  attributes: Record<string, number>;
}

export interface MatchFilter {
  team?: string;
  opponent?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: string;
  season?: number;
  from?: string;
  to?: string;
  round?: string;
  stage?: string;
  finals?: boolean;
  limit?: number;
  offset?: number;
  newestFirst?: boolean;
}

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  winRate: number;
}

export interface StandingRow extends TeamStats {
  position: number;
}

export interface DatasetSummary {
  matches: number;
  players: number;
  sources: Record<string, number>;
  seasons: { earliest: number; latest: number } | null;
  competitions: string[];
}
