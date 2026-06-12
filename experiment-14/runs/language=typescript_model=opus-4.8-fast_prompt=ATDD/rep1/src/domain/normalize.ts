/**
 * Normalization helpers for the messy real-world data described in TASK.md:
 *  - Team names appear with state/country suffixes ("Palmeiras-SP", "América - MG",
 *    "Nacional (URU)") and full names; we need a stable key for matching while
 *    keeping a clean display name.
 *  - Dates appear as ISO, ISO+time, or Brazilian DD/MM/YYYY.
 *  - Text is UTF-8 with accents and cedillas, which must not defeat matching.
 */

/** Strip a leading BOM that sometimes prefixes the first CSV header cell. */
export function stripBom(s: string): string {
  return s.charCodeAt(0) === 0xfeff ? s.slice(1) : s;
}

/** Remove accents/diacritics so "São" matches "Sao", "Grêmio" matches "Gremio". */
export function deburr(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

const SUFFIX_PATTERNS = [
  /\s*\([^)]*\)\s*$/, // trailing "(URU)", "(antigo ...)"
  /\s*[-–]\s*[A-Za-z]{2,3}\s*$/, // trailing "-SP", " - MG", "-EQU"
];

/**
 * Produce a clean display name by repeatedly peeling state/country suffixes and
 * trailing parentheticals, e.g.
 *   "Palmeiras-SP" -> "Palmeiras"
 *   "América - MG" -> "América"
 *   "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ" -> "Boavista Sport Club"
 *   "Nacional (URU)" -> "Nacional"
 */
export function cleanTeamName(raw: string): string {
  let s = (raw ?? '').trim();
  let changed = true;
  while (changed) {
    changed = false;
    for (const re of SUFFIX_PATTERNS) {
      const next = s.replace(re, '').trim();
      if (next !== s && next.length > 0) {
        s = next;
        changed = true;
      }
    }
  }
  return s;
}

/**
 * Aliases for well-known clubs whose names vary across datasets beyond simple
 * suffix stripping. Maps an alternate canonical key to the preferred one.
 *
 * NB: stripping state suffixes can still merge distinct clubs that share a base
 * name (e.g. "Atlético-MG" vs "Atlético-GO"); resolving those fully would need a
 * curated club registry and is out of scope for this demo dataset.
 */
const TEAM_ALIASES: Record<string, string> = {
  'vasco da gama': 'vasco',
  // "Athletico" (Paranaense) is spelled both with and without the silent "h"
  // across the datasets; fold them together.
  athletico: 'atletico',
};

/**
 * Base canonical key used for case/accent/suffix-insensitive team matching,
 * after applying known aliases. State/country suffixes are stripped, so
 * same-base-name clubs from different states share this key — see `teamKey`'s
 * callers (the store) for state-aware disambiguation.
 */
export function teamKey(raw: string): string {
  const base = deburr(cleanTeamName(raw))
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
  return TEAM_ALIASES[base] ?? base;
}

/**
 * Extract a 2-3 letter state/country code from a team name when present, e.g.
 *   "Atletico-MG" -> "mg", "América - RN" -> "rn", "Nacional (URU)" -> "uru".
 * Returns '' when the name carries no such suffix.
 */
export function extractState(raw: string): string {
  const s = (raw ?? '').trim();
  const paren = s.match(/\(([A-Za-z]{2,4})\)\s*$/);
  if (paren) return paren[1].toLowerCase();
  const hyphen = s.match(/[-–]\s*([A-Za-z]{2,3})\s*$/);
  if (hyphen) return hyphen[1].toLowerCase();
  return '';
}

/** Lowercase, accent-folded form for substring text matching (names, clubs). */
export function foldText(raw: string): string {
  return deburr((raw ?? '').toLowerCase()).replace(/\s+/g, ' ').trim();
}

/**
 * Whole-word, accent/case-insensitive match: does `haystack` contain `needle`
 * as a complete word? Used for stage matching so "final" does not also match
 * "semifinals" or "quarterfinals".
 */
export function wordMatch(haystack: string, needle: string): boolean {
  const n = foldText(needle);
  if (!n) return true;
  const escaped = n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(^|[^a-z0-9])${escaped}([^a-z0-9]|$)`).test(foldText(haystack));
}

/**
 * Parse the various date formats into ISO `YYYY-MM-DD`. Returns the input
 * untouched if it matches no known format.
 */
export function parseDate(raw: string): string {
  const s = (raw ?? '').trim();
  if (!s) return '';
  // ISO, optionally with a time component.
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  // Brazilian DD/MM/YYYY.
  const br = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (br) {
    const [, d, m, y] = br;
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
  }
  return s;
}

/** Coerce a CSV cell like "2", 1.0, "3.0" into an integer goal count. */
export function parseGoals(raw: string | number | undefined | null): number {
  if (raw === undefined || raw === null || raw === '') return 0;
  const n = typeof raw === 'number' ? raw : parseFloat(String(raw).trim());
  return Number.isFinite(n) ? Math.round(n) : 0;
}
