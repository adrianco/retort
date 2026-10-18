/**
 * Text normalization helpers shared by the loader and the query layer.
 *
 * Team names appear as "Palmeiras-SP", "Santos - SP", "Nacional (URU)",
 * "Sao Paulo" and "São Paulo" across the source files. Everything is folded
 * to a common form (no accents, lowercase, state suffix kept as a word) so
 * that a query such as "Flamengo" or "Sao Paulo" matches every spelling.
 */

/** Lowercase, strip diacritics, collapse whitespace. */
export function normalizeText(s: string): string {
  return s
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Canonical form of a team name, e.g.
 *   "Palmeiras-SP"                                  -> "palmeiras sp"
 *   "Santos - SP"                                   -> "santos sp"
 *   "Boavista Sport Club (antigo Esporte ...) - RJ" -> "boavista sport club rj"
 *   "Nacional (URU)"                                -> "nacional"
 *   "Athletico-PR"                                  -> "athletico pr"
 */
export function normalizeTeamName(raw: string): string {
  const s = raw
    .replace(/\([^)]*\)/g, " ")
    .replace(/\s*-\s*([A-Za-z]{2,3})\s*$/, " $1")
    .replace(/-/g, " ");
  return normalizeText(s);
}

/** True when `needle` appears as whole words inside `haystack` (accent/case-insensitive). */
export function containsWords(haystack: string, needle: string): boolean {
  const n = normalizeText(needle);
  if (!n) return false;
  return ` ${normalizeText(haystack)} `.includes(` ${n} `);
}

/**
 * True when a team name in the data matches a user-supplied team query.
 * Matches exact canonical names and whole-word containment, so "Flamengo"
 * matches "Flamengo-RJ" and "Sport Club Corinthians Paulista" matches "Corinthians".
 */
export function teamMatches(teamName: string, query: string): boolean {
  const q = normalizeTeamName(query);
  if (!q) return false;
  const t = normalizeTeamName(teamName);
  return t === q || ` ${t} `.includes(` ${q} `);
}

const MONTHS_IN_YEAR = 12;

/**
 * Parse the date formats found in the datasets into YYYY-MM-DD.
 * Accepts "2023-09-24", "2012-05-19 18:30:00" and "29/03/2003".
 * Returns undefined for anything else or for impossible calendar dates.
 */
export function parseDate(raw: string): string | undefined {
  const s = raw.trim();
  let y: number;
  let m: number;
  let d: number;

  const iso = /^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T]|$)/.exec(s);
  const br = /^(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(s);
  if (iso) {
    [y, m, d] = [Number(iso[1]), Number(iso[2]), Number(iso[3])];
  } else if (br) {
    [d, m, y] = [Number(br[1]), Number(br[2]), Number(br[3])];
  } else {
    return undefined;
  }

  if (m < 1 || m > MONTHS_IN_YEAR || d < 1) return undefined;
  const check = new Date(Date.UTC(y, m - 1, d));
  if (check.getUTCMonth() !== m - 1 || check.getUTCDate() !== d) return undefined;

  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}
