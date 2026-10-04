/** The domain model the datasets are loaded into. */
import type { CompetitionId } from './competitions.js';

export interface MatchStats {
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
  homeAttacks?: number;
  awayAttacks?: number;
}

export interface Match {
  competition: CompetitionId;
  season: number;
  date: string;
  time?: string;
  round?: number;
  stage?: string;
  homeKey: string;
  awayKey: string;
  homeGoals: number;
  awayGoals: number;
  arena?: string;
  stats?: MatchStats;
  sources: string[];
}

export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality: string;
  overall: number;
  potential?: number;
  club: string;
  clubKey: string;
  position: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  value?: string;
  wage?: string;
  preferredFoot?: string;
  contractValidUntil?: string;
  attributes: Record<string, number>;
}

export interface DatasetInfo {
  file: string;
  description: string;
  records: number;
  loaded: boolean;
}
