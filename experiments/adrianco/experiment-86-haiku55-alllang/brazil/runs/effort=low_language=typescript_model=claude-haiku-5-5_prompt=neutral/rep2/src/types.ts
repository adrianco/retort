/**
 * Context: domain types shared by the loader, queries and MCP tools.
 * Matches from all match files are normalized into one `Match` shape.
 */
import type { CompetitionName, TeamIdentity } from './normalize.js';

export interface Match {
  id: string;
  source: string;
  competition: CompetitionName;
  season: number;
  /** ISO date, YYYY-MM-DD. */
  date: string;
  /** Cup round number or Libertadores stage, when the source provides one. */
  round?: string;
  stage?: string;
  home: TeamIdentity;
  away: TeamIdentity;
  homeGoals: number;
  awayGoals: number;
}

export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality: string;
  overall?: number;
  potential?: number;
  club: string;
  clubKey: string;
  position?: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  preferredFoot?: string;
  value?: string;
  wage?: string;
  /** Skill attributes such as Finishing, Dribbling, and GK ratings. */
  attributes: Record<string, number>;
}

export interface Dataset {
  matches: Match[];
  players: Player[];
  /** Per-file load counts, reported by the dataset_info tool. */
  sources: Array<{ file: string; rows: number; loaded: number }>;
}

export interface MatchFilter {
  team?: string;
  opponent?: string;
  venue?: 'home' | 'away' | 'any';
  competition?: string;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  dateFrom?: string;
  dateTo?: string;
  /** Final rounds: the last round of each cup season, or stage "final" for Libertadores. */
  finalOnly?: boolean;
}
