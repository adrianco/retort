export const MATCH_SOURCES = [
  "Brasileirao_Matches.csv",
  "Brazilian_Cup_Matches.csv",
  "Libertadores_Matches.csv",
  "BR-Football-Dataset.csv",
  "novo_campeonato_brasileiro.csv",
] as const;

export type MatchSource = (typeof MATCH_SOURCES)[number];

export interface MatchMetrics {
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
  sources: MatchSource[];
  competition: string;
  date: string;
  kickoff?: string;
  season: number;
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
  stadium?: string;
  metrics?: MatchMetrics;
}

export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality: string;
  overall?: number;
  potential?: number;
  club?: string;
  clubKey?: string;
  position?: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  attributes: Record<string, number>;
}

export interface DatasetSummary {
  rawMatchRows: number;
  uniqueMatches: number;
  players: number;
  teams: number;
  competitions: number;
  seasons: { first: number; last: number } | null;
  sourceRows: Record<string, number>;
}

export interface MatchSearchCriteria {
  team?: string;
  opponent?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  stage?: string;
  round?: string;
  sort?: "asc" | "desc";
  offset?: number;
  limit?: number;
}

export interface MatchSearchResult {
  matches: SoccerMatch[];
  total: number;
  offset: number;
  limit: number;
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

export interface PlayerSearchCriteria {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxAge?: number;
  limit?: number;
}

export interface GraphNode {
  id: string;
  type: "team" | "player" | "competition" | "match";
  label: string;
  properties?: Record<string, string | number | boolean | null>;
}

export interface GraphEdge {
  from: string;
  to: string;
  type: "PLAYED_IN" | "HOME_TEAM" | "AWAY_TEAM" | "PLAYS_FOR" | "PARTICIPATED_IN";
}

export interface SoccerGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
}
