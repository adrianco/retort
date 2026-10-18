/**
 * Context: normalization helpers for the heterogeneous Brazilian soccer
 * datasets. Team names carry state suffixes ("Palmeiras-SP", "Atlético - MG"),
 * parenthetical notes, accents and long official names. Dates come in ISO,
 * ISO-with-time and DD/MM/YYYY. Goals may be "2.0", "2", or "NA".
 */

export type CompetitionName =
  | 'Brasileirão Série A'
  | 'Brasileirão Série B'
  | 'Brasileirão Série C'
  | 'Copa do Brasil'
  | 'Copa Libertadores';

export const BRAZILIAN_STATES = new Set([
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
  'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
]);

interface TeamAlias {
  key: string;
  state?: string;
}

/**
 * Official or alternative names mapped to the short key (and state, when the
 * name implies one) used for matching. Club suffixes such as "FC" and "EC" are
 * stripped generically in normalizeTeam, so only real renames belong here.
 */
const TEAM_ALIASES: Record<string, TeamAlias> = {
  'sport club corinthians paulista': { key: 'corinthians', state: 'SP' },
  'corinthians paulista': { key: 'corinthians', state: 'SP' },
  'sociedade esportiva palmeiras': { key: 'palmeiras', state: 'SP' },
  'clube de regatas do flamengo': { key: 'flamengo', state: 'RJ' },
  'fluminense football club': { key: 'fluminense', state: 'RJ' },
  'gremio foot-ball porto alegrense': { key: 'gremio', state: 'RS' },
  'athletico paranaense': { key: 'athletico', state: 'PR' },
  'club athletico paranaense': { key: 'athletico', state: 'PR' },
  'atletico paranaense': { key: 'athletico', state: 'PR' },
  'atletico mineiro': { key: 'atletico', state: 'MG' },
  'atletico goianiense': { key: 'atletico', state: 'GO' },
  'red bull bragantino': { key: 'bragantino', state: 'SP' },
  'sport club do recife': { key: 'sport', state: 'PE' },
  'vasco da gama': { key: 'vasco', state: 'RJ' },
};

/** Trailing or leading club abbreviations, e.g. "Fortaleza FC", "EC Juventude". */
const CLUB_ABBREVIATION = /^(?:ec|fc|sc|ac|af)\s+|\s+(?:ec|fc|sc|ac|af)$/g;

export function foldText(text: string): string {
  return text
    .normalize('NFD')
    .replace(/\p{M}+/gu, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

export interface TeamIdentity {
  /** Display name without state suffix or parenthetical notes. */
  name: string;
  /** Matching key, state-agnostic: "palmeiras". */
  key: string;
  /** Matching key including the state when known: "atletico-mg". */
  qualified: string;
  /** Two-letter state code, when present. */
  state?: string;
}

export function normalizeTeam(raw: string): TeamIdentity {
  let base = raw.replace(/\([^)]*\)/g, ' ').replace(/\s+/g, ' ').trim();
  let state: string | undefined;

  const suffix = base.match(/^(.*?)[\s-]+([A-Za-z]{2,3})$/);
  if (suffix) {
    const code = suffix[2].toUpperCase();
    const hyphenated = /-[A-Za-z]{2,3}$/.test(base);
    if (BRAZILIAN_STATES.has(code) || (hyphenated && code === code.toUpperCase())) {
      base = suffix[1].trim();
      if (BRAZILIAN_STATES.has(code)) state = code;
    }
  }
  base = base.replace(/-\s*$/, '').trim();

  const folded = foldText(base);
  const alias = TEAM_ALIASES[folded];
  const key = alias?.key ?? foldText(folded.replace(CLUB_ABBREVIATION, '').trim());
  state = state ?? alias?.state;
  // Atlético-PR was renamed Athletico-PR; the files use both spellings.
  const renamed = key === 'atletico' && state === 'PR' ? 'athletico' : key;
  const qualified = state ? `${renamed}-${state.toLowerCase()}` : renamed;
  return { name: base, key: renamed, qualified, state };
}

/**
 * Whether a user-supplied team name refers to a dataset team. A query with a
 * state ("Atletico-MG") matches only that state; a bare name matches any state.
 */
export function teamMatches(query: TeamIdentity, team: TeamIdentity): boolean {
  if (query.state) return query.qualified === team.qualified;
  return query.key === team.key;
}

const COMPETITION_KEYWORDS: Array<[RegExp, CompetitionName]> = [
  [/libertadores/, 'Copa Libertadores'],
  [/copa do brasil|copa brasil|brazilian cup|copa-do-brasil/, 'Copa do Brasil'],
  [/serie b|série b|segunda divisao|brasileirao b/, 'Brasileirão Série B'],
  [/serie c|série c/, 'Brasileirão Série C'],
  [/brasileirao|brasileirão|serie a|série a|campeonato brasileiro/, 'Brasileirão Série A'],
];

/** Maps free text like "Brasileirão" or "Copa do Brasil" to a canonical competition. */
export function normalizeCompetition(raw: string): CompetitionName | undefined {
  const folded = foldText(raw);
  return COMPETITION_KEYWORDS.find(([pattern]) => pattern.test(folded))?.[1];
}

/** Returns ISO "YYYY-MM-DD" for ISO, ISO-with-time, or DD/MM/YYYY input. */
export function parseDate(raw: string): string | undefined {
  const value = raw.trim();
  const iso = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  const br = value.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (br) return `${br[3]}-${br[2]}-${br[1]}`;
  return undefined;
}

/** Parses a goal count, tolerating "2.0" and returning undefined for "NA". */
export function parseGoals(raw: string | undefined): number | undefined {
  if (raw === undefined) return undefined;
  const trimmed = raw.trim();
  if (trimmed === '' || trimmed.toUpperCase() === 'NA') return undefined;
  const value = Number(trimmed);
  return Number.isFinite(value) ? Math.round(value) : undefined;
}

export function parseNumber(raw: string | undefined): number | undefined {
  if (raw === undefined) return undefined;
  const value = Number(raw.trim());
  return raw.trim() !== '' && Number.isFinite(value) ? value : undefined;
}
