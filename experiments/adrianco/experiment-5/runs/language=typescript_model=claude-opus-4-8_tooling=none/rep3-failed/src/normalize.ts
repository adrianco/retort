/**
 * ============================================================================
 * Context Block
 * ----------------------------------------------------------------------------
 * File:    src/normalize.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: Text-normalization helpers that make the heterogeneous datasets
 *          mutually queryable. Brazilian club names appear with state suffixes
 *          ("Palmeiras-SP"), country codes ("Nacional (URU)"), accents
 *          ("São Paulo", "Grêmio"), and long official names. This module
 *          collapses those variants into a single comparable key and parses the
 *          several date formats found across the CSVs into ISO `YYYY-MM-DD`.
 *
 * Key functions:
 *   - teamKey(name):  normalized matching key (accent-folded, suffix-stripped).
 *   - normalizeText:  generic accent-folding / lowercasing for fuzzy search.
 *   - parseDate:      multi-format date parser -> ISO string or null.
 *   - parseGoals:     tolerant numeric parser ("1", "1.0", '"2"').
 * ============================================================================
 */

/** Two-letter Brazilian state abbreviations used as team-name suffixes. */
const BR_STATES = new Set([
  'ac', 'al', 'ap', 'am', 'ba', 'ce', 'df', 'es', 'go', 'ma', 'mt', 'ms',
  'mg', 'pa', 'pb', 'pr', 'pe', 'pi', 'rj', 'rn', 'rs', 'ro', 'rr', 'sc',
  'sp', 'se', 'to',
]);

/** Fold accents/diacritics and lowercase. Keeps letters, digits and spaces. */
export function normalizeText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '') // strip combining diacritical marks
    .toLowerCase()
    .trim();
}

/**
 * Produce a canonical key for a team name so that accent / punctuation variants
 * collapse together while *preserving* a trailing state suffix as a token.
 *
 * Examples:
 *   "Palmeiras-SP"   -> "palmeiras sp"
 *   "Palmeiras"      -> "palmeiras"
 *   "São Paulo"      -> "sao paulo"
 *   "Atlético-MG"    -> "atletico mg"   (distinct from "atletico pr")
 *   "Nacional (URU)" -> "nacional"
 *
 * The state token is retained (not deleted) so that clubs which share a base
 * name but differ by state — Atlético-MG vs Atlético-PR, América-MG vs
 * América-RN — remain distinct. Loose matching that ignores the state is
 * handled separately via {@link teamBaseKey} / {@link teamKeyState}.
 */
export function teamKey(rawName: string): string {
  if (!rawName) return '';
  let name = normalizeText(rawName);

  // Remove parenthetical country/qualifier codes, e.g. "nacional (uru)".
  name = name.replace(/\([^)]*\)/g, ' ');

  // Normalize a trailing state suffix " - sp" / "-sp" into " sp".
  name = name.replace(/\s*-\s*([a-z]{2})\s*$/u, (m, code) =>
    BR_STATES.has(code) ? ` ${code}` : m,
  );

  // Replace remaining separators/punctuation with spaces; collapse whitespace.
  name = name
    .replace(/[._/-]/g, ' ')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return name;
}

/** The trailing two-letter Brazilian state token of a key, or null. */
export function teamKeyState(key: string): string | null {
  const m = key.match(/\s([a-z]{2})$/);
  return m && BR_STATES.has(m[1]) ? m[1] : null;
}

/** A team key with any trailing state token removed (the "base" name). */
export function teamBaseKey(key: string): string {
  return key.replace(/\s[a-z]{2}$/, (m) =>
    BR_STATES.has(m.trim()) ? '' : m,
  ).trim();
}

/**
 * Does `candidateKey` (from a match record) refer to the team named by
 * `queryKey`? Bases must match; states must agree when *both* are specified.
 * A query without a state matches any state (e.g. "Atletico" -> MG and PR),
 * while "Atletico-MG" will not match "Atletico-PR".
 */
export function teamKeyMatches(candidateKey: string, queryKey: string): boolean {
  if (!queryKey) return false;
  if (candidateKey === queryKey) return true;
  const cb = teamBaseKey(candidateKey);
  const qb = teamBaseKey(queryKey);
  if (cb !== qb) return false;
  const cs = teamKeyState(candidateKey);
  const qs = teamKeyState(queryKey);
  return cs === null || qs === null || cs === qs;
}

/**
 * A human-friendly display name. Collapses whitespace and normalizes a trailing
 * state suffix to the compact "Name-UF" form, but KEEPS the state so that clubs
 * sharing a base name (Atlético-MG vs Atlético-PR) remain distinguishable.
 */
export function displayTeamName(rawName: string): string {
  const cleaned = rawName.replace(/\s+/g, ' ').trim();
  return cleaned.replace(/\s*-\s*([A-Za-z]{2})$/u, (m, code) =>
    BR_STATES.has(code.toLowerCase()) ? `-${code.toUpperCase()}` : m,
  );
}

/**
 * Parse the several date formats present in the datasets into an ISO date
 * (`YYYY-MM-DD`). Returns null when no date can be extracted.
 *
 * Handles:
 *   - "2023-09-24" and "2012-05-19 18:30:00" (ISO, optionally with time)
 *   - "29/03/2003" (Brazilian DD/MM/YYYY)
 */
export function parseDate(raw: string | undefined | null): string | null {
  if (!raw) return null;
  const value = String(raw).trim().replace(/^"|"$/g, '');
  if (!value) return null;

  // ISO date, optionally followed by a time component.
  const iso = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;

  // Brazilian DD/MM/YYYY (also accepts D/M/YYYY).
  const br = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (br) {
    const day = br[1].padStart(2, '0');
    const month = br[2].padStart(2, '0');
    return `${br[3]}-${month}-${day}`;
  }

  return null;
}

/** Extract the four-digit year from a raw date/season string. */
export function parseYear(raw: string | undefined | null): number | null {
  if (raw == null) return null;
  const m = String(raw).match(/(\d{4})/);
  return m ? Number(m[1]) : null;
}

/** Tolerant goal parser: handles "1", "1.0", quoted '"2"', empty -> null. */
export function parseGoals(raw: string | undefined | null): number | null {
  if (raw == null) return null;
  const value = String(raw).trim().replace(/^"|"$/g, '');
  if (value === '' || value.toLowerCase() === 'nan') return null;
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return Math.round(n);
}

/** Parse an integer field, returning null when absent/unparseable. */
export function parseIntField(raw: string | undefined | null): number | null {
  if (raw == null) return null;
  const value = String(raw).trim().replace(/^"|"$/g, '');
  if (value === '') return null;
  const n = parseInt(value, 10);
  return Number.isFinite(n) ? n : null;
}
