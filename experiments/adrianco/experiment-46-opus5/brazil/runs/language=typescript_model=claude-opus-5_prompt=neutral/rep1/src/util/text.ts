/**
 * Text helpers for matching Brazilian Portuguese names.
 *
 * Every user-supplied name ("Sao Paulo", "São Paulo", "SAO PAULO") and every
 * dataset spelling has to collapse onto the same comparison key, so accent
 * folding and whitespace/punctuation normalisation live here and are used by
 * both the team registry and the player index.
 */

const COMBINING_MARKS = /[\u0300-\u036f]/g;

/** Fold accents and cedillas: "Grêmio" -> "Gremio", "Avaí" -> "Avai". */
export function stripDiacritics(value: string): string {
  return value.normalize('NFD').replace(COMBINING_MARKS, '');
}

/**
 * Lowercase, accent-free, punctuation-free, single-spaced form used as the key
 * for all fuzzy name comparisons.
 */
export function normalizeName(value: string): string {
  return stripDiacritics(value)
    .toLowerCase()
    .replace(/[.'`´]/g, '')
    .replace(/[^a-z0-9()]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

/** Kebab-case identifier suitable for a graph node id. */
export function slugify(value: string): string {
  return normalizeName(value).replace(/[()]/g, '').trim().replace(/\s+/g, '-');
}

/**
 * Similarity in [0, 1] between two already-normalized strings.
 *
 * Uses Levenshtein distance over the longer length. Good enough to rank
 * "gremio" against "gremio prudente" or to catch a one-letter typo, and cheap
 * enough to run across a few hundred candidate team names.
 */
export function similarity(a: string, b: string): number {
  if (a === b) return 1;
  if (a.length === 0 || b.length === 0) return 0;
  const distance = levenshtein(a, b);
  return 1 - distance / Math.max(a.length, b.length);
}

export function levenshtein(a: string, b: string): number {
  // Single-row dynamic programming: O(a*b) time, O(b) space.
  let previous = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const current = [i];
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      current[j] = Math.min(current[j - 1]! + 1, previous[j]! + 1, previous[j - 1]! + cost);
    }
    previous = current;
  }
  return previous[b.length]!;
}
