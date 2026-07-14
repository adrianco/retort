/**
 * ============================================================================
 * File: src/types.ts
 * Project: Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * Context:
 *   Shared TypeScript type definitions for the Brazilian soccer knowledge
 *   graph. The graph is built from six Kaggle CSV datasets (five match files
 *   and one FIFA player file). Entities are Teams, Matches, Players and
 *   Competitions. Matches act as edges between two Team nodes; Players are
 *   linked to Teams (clubs) by normalized name.
 *
 *   These types are consumed by the loader (src/loader.ts), the in-memory
 *   knowledge graph (src/knowledgeGraph.ts) and the MCP tool layer
 *   (src/server.ts).
 * ============================================================================
 */

/** Canonical competition identifiers used across all datasets. */
export type Competition =
  | "Brasileirão Série A"
  | "Brasileirão Série B"
  | "Brasileirão Série C"
  | "Copa do Brasil"
  | "Copa Libertadores";

/** Optional extended per-match statistics (only present for some sources). */
export interface MatchStats {
  homeCorners?: number;
  awayCorners?: number;
  totalCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
  halfTimeHomeResult?: string;
  halfTimeAwayResult?: string;
}

/** A single match. Acts as an edge between homeTeamKey and awayTeamKey. */
export interface Match {
  /** Canonical competition name. */
  competition: string;
  /** Source CSV file the record originated from. */
  source: string;
  /** ISO date (YYYY-MM-DD) or null if unparseable/missing. */
  date: string | null;
  /** Season year, or null if unknown. */
  season: number | null;
  /** Round label (number or text), or null. */
  round: string | null;
  /** Tournament stage (e.g. "group stage", "final"), or null. */
  stage: string | null;
  /** Display name of home team (state suffix stripped). */
  homeTeam: string;
  /** Display name of away team. */
  awayTeam: string;
  /** Normalized lookup key for the home team. */
  homeTeamKey: string;
  /** Normalized lookup key for the away team. */
  awayTeamKey: string;
  homeGoals: number | null;
  awayGoals: number | null;
  homeState?: string;
  awayState?: string;
  venue?: string;
  stats?: MatchStats;
}

/** Aggregated win/draw/loss + goal record. */
export interface Record {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}

/** A FIFA player node. */
export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  /** Normalized lookup key for the player's club. */
  clubKey: string;
  position: string;
  jerseyNumber: number | null;
  height: string;
  weight: string;
  preferredFoot: string;
}

/** A team node in the knowledge graph. */
export interface Team {
  key: string;
  name: string;
  states: Set<string>;
  competitions: Set<string>;
}
