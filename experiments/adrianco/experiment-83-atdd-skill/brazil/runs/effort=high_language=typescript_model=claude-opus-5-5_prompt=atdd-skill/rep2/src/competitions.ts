/** The competitions covered by the datasets, and how people refer to them. */
import { fold } from './text.js';

export type CompetitionId = 'serie-a' | 'serie-b' | 'serie-c' | 'copa-do-brasil' | 'libertadores';

export const COMPETITION_NAMES: Record<CompetitionId, string> = {
  'serie-a': 'Brasileirão Série A',
  'serie-b': 'Brasileirão Série B',
  'serie-c': 'Brasileirão Série C',
  'copa-do-brasil': 'Copa do Brasil',
  libertadores: 'Copa Libertadores',
};

/** The shorter label used in readable answers. */
export const COMPETITION_LABELS: Record<CompetitionId, string> = {
  'serie-a': 'Brasileirão',
  'serie-b': 'Série B',
  'serie-c': 'Série C',
  'copa-do-brasil': 'Copa do Brasil',
  libertadores: 'Copa Libertadores',
};

export function isLeague(id: CompetitionId): boolean {
  return id === 'serie-a' || id === 'serie-b' || id === 'serie-c';
}

export function parseCompetition(input: string): CompetitionId {
  const f = fold(input);
  if (f.includes('libertadores')) return 'libertadores';
  if (f.includes('copa do brasil') || f.includes('brazil cup') || f.includes('brazilian cup') || f === 'cup' || f === 'cdb') return 'copa-do-brasil';
  if (/\bserie b\b/.test(f) || f === 'b') return 'serie-b';
  if (/\bserie c\b/.test(f) || f === 'c') return 'serie-c';
  if (f.includes('brasileir') || f.includes('brazilian league') || /\bserie a\b/.test(f) || f === 'a' || f === 'league' || f.includes('campeonato brasileiro')) {
    return 'serie-a';
  }
  throw new Error(`I don't know the competition "${input}". Try: ${Object.values(COMPETITION_NAMES).join(', ')}`);
}

const STAGE_ALIASES: Array<[RegExp, string]> = [
  [/^(the )?finals?$/, 'final'],
  [/^semi ?finals?$|^semis$/, 'semifinals'],
  [/^quarter ?finals?$|^quarters$/, 'quarterfinals'],
  [/^(round of 16|last 16|r16|eighth ?finals?)$/, 'round of 16'],
  [/^group( stage)?s?$/, 'group stage'],
];

export function normaliseStage(input: string): string {
  const f = fold(input);
  for (const [pattern, stage] of STAGE_ALIASES) if (pattern.test(f)) return stage;
  return f;
}

/** Brasileirão relegation places by season (two in 2003's 24-team league, four since). */
export function relegationPlaces(id: CompetitionId, season: number): number {
  if (id === 'serie-a') return season <= 2003 ? 2 : 4;
  if (id === 'serie-b') return 4;
  return 0;
}
