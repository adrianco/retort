export const COMPETITIONS = {
  brasileirao: "Brasileirão Série A",
  copaDoBrasil: "Copa do Brasil",
  libertadores: "Copa Libertadores",
} as const;

export type MatchSource =
  | "brasileirao"
  | "copa-do-brasil"
  | "libertadores"
  | "extended"
  | "historical-brasileirao";

export interface MatchStatistics {
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
  totalCorners?: number;
}

export interface SoccerMatch {
  id: string;
  source: MatchSource;
  sourceRow: number;
  competition: string;
  season: number;
  date: string;
  timestamp: number;
  time?: string;
  round?: string;
  stage?: string;
  homeTeam: string;
  homeTeamKey: string;
  homeState?: string;
  awayTeam: string;
  awayTeamKey: string;
  awayState?: string;
  homeGoals: number;
  awayGoals: number;
  venue?: string;
  statistics?: MatchStatistics;
}

export interface Player {
  id: number;
  name: string;
  nameKey: string;
  age?: number;
  nationality: string;
  nationalityKey: string;
  overall?: number;
  potential?: number;
  club?: string;
  clubKey?: string;
  position?: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  preferredFoot?: string;
  attributes: Record<string, number>;
}

export interface DataSetSummary {
  matches: number;
  players: number;
  teams: number;
  competitions: number;
  sourceCounts: Record<MatchSource, number>;
}

export interface MatchFilters {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  stage?: string;
  venue?: "home" | "away" | "either";
  limit?: number;
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
  winRate: number;
}

export interface Standing extends TeamRecord {
  position: number;
}

export interface PlayerFilters {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
}

export interface QueryResult<T = unknown> {
  kind: string;
  summary: string;
  data: T;
  formatted: string;
  limitations?: string[];
}
