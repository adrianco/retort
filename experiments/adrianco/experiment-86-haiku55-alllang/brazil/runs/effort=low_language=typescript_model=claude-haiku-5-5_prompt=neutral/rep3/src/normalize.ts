/*
 * Context: Team- and text-normalization helpers. The source datasets name the same
 * club differently ("Palmeiras-SP", "Palmeiras", "Sociedade Esportiva Palmeiras",
 * "Sao Paulo" vs "São Paulo"). Every comparison in the server goes through `teamKey`,
 * so name variations collapse to one canonical key.
 * Some clubs only differ by state ("Atlético-MG" vs "Atlético-PR"), so state-qualified
 * names are resolved against the full raw name BEFORE the state suffix is stripped.
 * Related: dataset.ts (uses teamKey for indexing), queries.ts (resolves user input).
 */

/** Full raw names (folded, with "-" normalized) that must resolve before suffix stripping. */
const QUALIFIED_ALIASES: Record<string, string> = {
  'atletico-mg': 'atletico mineiro',
  'atletico mg': 'atletico mineiro',
  'atletico-pr': 'athletico pr',
  'atletico pr': 'athletico pr',
  'athletico-pr': 'athletico pr',
  'athletico pr': 'athletico pr',
  'atletico-go': 'atletico goianiense',
  'atletico go': 'atletico goianiense',
  'america-rn': 'america rn',
  'america rn': 'america rn',
  'america-mg': 'america',
  'america mg': 'america',
};

/** Known full-name / alternate spellings mapped to a canonical key (applied after suffix stripping). */
const TEAM_ALIASES: Record<string, string> = {
  'sport club corinthians paulista': 'corinthians',
  'sociedade esportiva palmeiras': 'palmeiras',
  'clube de regatas do flamengo': 'flamengo',
  'sport club internacional': 'internacional',
  'clube atletico mineiro': 'atletico mineiro',
  'club atletico mineiro': 'atletico mineiro',
  'athletico paranaense': 'athletico pr',
  'atletico paranaense': 'athletico pr',
  'clube atletico paranaense': 'athletico pr',
  'fluminense football club': 'fluminense',
  'sao paulo futebol clube': 'sao paulo',
  'gremio foot-ball porto alegrense': 'gremio',
  'sport club do recife': 'sport',
  'ceara sporting club': 'ceara',
  'america fc (minas gerais)': 'america',
  'vasco da gama': 'vasco',
  'ec bahia': 'bahia',
  'sport recife': 'sport',
};

/** Brazilian state (UF) codes, used to recognise "Team SP" style suffixes. */
const UF_CODES = 'AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO';

/** Strip accents, lowercase, collapse whitespace. */
export function foldText(input: string): string {
  return input
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

/** Remove trailing state / country suffixes, parenthetical notes and EC/FC/SC club tags. */
export function stripTeamDecorations(raw: string): string {
  return raw
    .replace(/\s*\(antigo[^)]*\)/gi, '')
    .replace(/\s*\([A-Za-z]{2,3}\)\s*$/, '')
    .replace(/\s*[-–]\s*[A-Za-z]{2,3}\s*$/, '')
    .replace(new RegExp(`\\s+(${UF_CODES})$`), '')
    .replace(/\s+(EC|FC|SC|AC)$/i, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Display names for canonical keys whose raw spelling is ambiguous (e.g. bare "Atletico"). */
const CANONICAL_DISPLAY: Record<string, string> = {
  'athletico pr': 'Athletico-PR',
  'atletico mineiro': 'Atlético-MG',
  'atletico goianiense': 'Atlético-GO',
  'america rn': 'América-RN',
};

/** Brazilian state code from a club suffix ("Botafogo-SP", "Sport RJ", "Botafogo - PB"), or null. */
export function stateOf(raw: string): string | null {
  const m = new RegExp(`(?:[-–(]\\s*|\\s+)(${UF_CODES})\\)?\\s*$`, 'i').exec(raw.trim());
  return m ? m[1].toUpperCase() : null;
}

/** Canonical lookup key for a team name, e.g. "Palmeiras-SP" -> "palmeiras". */
export function teamKey(raw: string): string {
  const qualified = foldText(raw).replace(/\s*-\s*/g, '-');
  if (QUALIFIED_ALIASES[qualified]) return QUALIFIED_ALIASES[qualified];
  const stripped = foldText(stripTeamDecorations(raw));
  return TEAM_ALIASES[stripped] ?? stripped;
}

/** Human-friendly display name: the raw name with state/country suffixes removed. */
export function teamDisplayName(raw: string): string {
  return stripTeamDecorations(raw).replace(/\s+/g, ' ').trim();
}

/** Display name for a resolved key; `qualifyState` appends the state for clubs sharing a base name. */
export function displayFor(raw: string, key: string, qualifyState: boolean): string {
  if (CANONICAL_DISPLAY[key]) return CANONICAL_DISPLAY[key];
  const base = teamDisplayName(raw);
  const state = stateOf(raw);
  return qualifyState && state ? `${base} (${state})` : base;
}

/**
 * Accent/case-insensitive test: every search token must be the start of some word in the
 * haystack. "Neymar" matches "Neymar Jr"; "a" matches "Série A" but not "Série B".
 */
export function matchesText(haystack: string, needle: string): boolean {
  const words = foldText(haystack).split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  const tokens = foldText(needle).split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  return tokens.every((t) => words.some((w) => w.startsWith(t)));
}
