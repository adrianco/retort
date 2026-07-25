/**
 * Core entities of the knowledge graph.
 *
 * A `Match` is the merged view of one real fixture, which may have been
 * described by more than one source file; `sources` records where the facts
 * came from. A `Player` is one row of the FIFA database. Both reference teams
 * by canonical id (see `domain/teams.ts`) rather than by raw label, which is
 * what makes cross-file queries possible.
 */

/** Identifier of a source CSV. */
export type SourceId =
  | 'brasileirao'
  | 'novo-brasileirao'
  | 'br-football'
  | 'copa-do-brasil'
  | 'libertadores'
  | 'fifa';

/** Identifier of a competition. */
export type CompetitionId =
  | 'serie-a'
  | 'serie-b'
  | 'serie-c'
  | 'copa-do-brasil'
  | 'libertadores';

export interface Competition {
  id: CompetitionId;
  name: string;
  /** `league` tables are computed as standings; `cup` competitions are bracketed. */
  format: 'league' | 'cup';
  country: string;
}

export const COMPETITIONS: Record<CompetitionId, Competition> = {
  'serie-a': { id: 'serie-a', name: 'Brasileirão Série A', format: 'league', country: 'Brazil' },
  'serie-b': { id: 'serie-b', name: 'Brasileirão Série B', format: 'league', country: 'Brazil' },
  'serie-c': { id: 'serie-c', name: 'Brasileirão Série C', format: 'league', country: 'Brazil' },
  'copa-do-brasil': { id: 'copa-do-brasil', name: 'Copa do Brasil', format: 'cup', country: 'Brazil' },
  libertadores: { id: 'libertadores', name: 'Copa Libertadores', format: 'cup', country: 'South America' },
};

/** Optional per-match detail, present only for rows sourced from BR-Football. */
export interface MatchStats {
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
  totalCorners?: number;
  homeHalfTimeResult?: string;
  awayHalfTimeResult?: string;
}

export interface Match {
  /** Deterministic id: `<competition>:<season>:<home>:<away>:<date>`. */
  id: string;
  competition: CompetitionId;
  season: number;
  /** `YYYY-MM-DD`. */
  date: string;
  /** `HH:MM` kick-off, when known. */
  time?: string;
  /** League round number, when known. */
  round?: number;
  /** Cup stage label ("group stage", "final", ...), when known. */
  stage?: string;
  homeTeamId: string;
  awayTeamId: string;
  /** `null` when the source recorded no score. */
  homeGoals: number | null;
  awayGoals: number | null;
  venue?: string;
  stats?: MatchStats;
  /** Every source file that described this fixture. */
  sources: SourceId[];
}

export type MatchOutcome = 'home' | 'away' | 'draw';

/** Winner of a match, or `undefined` when the score is unknown. */
export function outcomeOf(match: Match): MatchOutcome | undefined {
  if (match.homeGoals === null || match.awayGoals === null) return undefined;
  if (match.homeGoals > match.awayGoals) return 'home';
  if (match.homeGoals < match.awayGoals) return 'away';
  return 'draw';
}

export function hasScore(match: Match): match is Match & { homeGoals: number; awayGoals: number } {
  return match.homeGoals !== null && match.awayGoals !== null;
}

export type PositionGroup = 'Goalkeeper' | 'Defender' | 'Midfielder' | 'Forward' | 'Unknown';

export interface Player {
  /** FIFA player id, as a string. */
  id: string;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  /** Raw club label from the FIFA file, e.g. "Fluminense". */
  club: string;
  /**
   * Accent-folded, lower-cased forms of `name` and `club`, computed once at
   * load. Recomputing these per query costs ~7 ms across the 18k-row file, on
   * every single name or club search.
   */
  normalizedName: string;
  normalizedClub: string;
  /** Canonical team id, when the club could be matched to the team registry. */
  clubTeamId?: string;
  position: string;
  positionGroup: PositionGroup;
  jerseyNumber: number | null;
  /** Market value in euros, parsed from "€110.5M". */
  valueEur: number | null;
  /** Weekly wage in euros, parsed from "€565K". */
  wageEur: number | null;
  preferredFoot: string;
  height: string;
  weight: string;
  contractValidUntil: string;
  /** Selected skill ratings (Crossing, Finishing, ...). */
  skills: Record<string, number>;
}

/** Map a FIFA position code to a coarse group. */
export function positionGroupOf(position: string): PositionGroup {
  const code = position.trim().toUpperCase();
  if (code === '') return 'Unknown';
  if (code === 'GK') return 'Goalkeeper';
  if (/^(LB|LCB|CB|RCB|RB|LWB|RWB)$/.test(code)) return 'Defender';
  if (/^(CDM|LDM|RDM|CM|LCM|RCM|LM|RM|CAM|LAM|RAM)$/.test(code)) return 'Midfielder';
  if (/^(LW|RW|LF|CF|RF|ST|LS|RS)$/.test(code)) return 'Forward';
  return 'Unknown';
}
