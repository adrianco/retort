/**
 * Domain types for the Brazilian Soccer knowledge base.
 *
 * These describe the problem-domain entities (matches, players) independent of
 * any particular CSV file format. CSV loaders translate raw rows into these
 * canonical shapes; the query layer and MCP tools operate purely on them.
 */

/** A single football match with its result. */
export interface Match {
  /** Competition name, e.g. "Brasileirão", "Copa do Brasil", "Libertadores", "Serie A". */
  competition: string;
  /** Calendar year of the season. */
  season: number;
  /** Match date in ISO `YYYY-MM-DD` form. */
  date: string;
  /** Round number or stage label (e.g. "1", "final", "group stage"). */
  round?: string;
  /** Home team name as it appears in the source (may carry a state suffix). */
  homeTeam: string;
  /** Away team name as it appears in the source. */
  awayTeam: string;
  /** Authoritative home-team state code from the source file, when available. */
  homeState?: string;
  /** Authoritative away-team state code from the source file, when available. */
  awayState?: string;
  /** Goals scored by the home team. */
  homeGoals: number;
  /** Goals scored by the away team. */
  awayGoals: number;
  /** Stadium / arena name when known. */
  stadium?: string;
}

/** A player record sourced from the FIFA dataset. */
export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality?: string;
  /** FIFA overall rating. */
  overall?: number;
  /** FIFA potential rating. */
  potential?: number;
  club?: string;
  position?: string;
  jerseyNumber?: number;
}
