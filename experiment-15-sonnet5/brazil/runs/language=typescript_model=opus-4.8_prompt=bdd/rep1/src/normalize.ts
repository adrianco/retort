/**
 * Normalization helpers for messy, multi-source Brazilian soccer data.
 *
 * The datasets disagree on team naming ("Palmeiras-SP" vs "Palmeiras" vs
 * "Sport Club Corinthians Paulista"), date formats (ISO, DD/MM/YYYY, with or
 * without time), and encodings (accented Portuguese). These helpers produce
 * stable, comparable values so queries can match across all sources.
 */

/** Strip diacritics (São -> Sao, Grêmio -> Gremio) for accent-insensitive matching. */
export function stripAccents(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/**
 * Remove the state/country suffix and parenthetical annotations from a raw
 * team name, returning a clean display name.
 *
 * Examples:
 *   "Palmeiras-SP"                    -> "Palmeiras"
 *   "América - MG"                    -> "América"
 *   "Nacional (URU)"                  -> "Nacional"
 *   "Boavista Sport Club (x) - RJ"    -> "Boavista Sport Club"
 */
export function cleanTeamName(raw: string): string {
  let name = raw.trim();
  // Drop parenthetical annotations such as "(URU)" or "(antigo ...)".
  name = name.replace(/\s*\([^)]*\)/g, "");
  // Drop a trailing " - SP" or "-SP" style state/country suffix (2-3 letters).
  name = name.replace(/\s*-\s*[A-Za-z]{2,3}\s*$/u, "");
  return name.replace(/\s+/g, " ").trim();
}

/**
 * Produce a canonical, comparable key for a team name: cleaned, accent-free,
 * lower-cased, punctuation-normalized. Used for loose matching of a user's
 * query term against dataset team names (suffix removed so "Palmeiras-SP"
 * matches "Palmeiras").
 */
export function teamKey(raw: string): string {
  return stripAccents(cleanTeamName(raw))
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Produce a *distinct-identity* key that PRESERVES the state/country suffix, so
 * clubs differing only by suffix ("Atlético-MG" vs "Atlético-PR") stay separate.
 * Used to group teams into standings tables where merging distinct clubs would
 * corrupt the results.
 */
export function teamIdentityKey(raw: string): string {
  return stripAccents(raw)
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Decide whether a dataset team name matches a user-supplied query term.
 * Matches when the canonical keys are equal, or when one key contains the
 * other as a whole (handles "Sao Paulo" vs "Sao Paulo FC", "Atletico" vs
 * "Atletico Mineiro" partials the user may type).
 */
export function teamMatches(datasetName: string, query: string): boolean {
  const a = teamKey(datasetName);
  const b = teamKey(query);
  if (!a || !b) return false;
  if (a === b) return true;
  // Whole-word containment in either direction.
  return containsWholeWords(a, b) || containsWholeWords(b, a);
}

function containsWholeWords(haystack: string, needle: string): boolean {
  if (haystack === needle) return true;
  return (
    haystack.startsWith(needle + " ") ||
    haystack.endsWith(" " + needle) ||
    haystack.includes(" " + needle + " ")
  );
}

/**
 * Parse a date from any of the formats present in the datasets:
 *   "2012-05-19 18:30:00", "2023-09-24", "29/03/2003".
 * Returns null when the value is empty or unparseable.
 */
export function parseDate(raw: string | undefined | null): Date | null {
  if (!raw) return null;
  const value = raw.trim();
  if (!value || value.toUpperCase() === "NA") return null;

  // DD/MM/YYYY (Brazilian format).
  const brMatch = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (brMatch) {
    const [, dd, mm, yyyy] = brMatch;
    return buildDate(Number(yyyy), Number(mm), Number(dd));
  }

  // YYYY-MM-DD optionally followed by a time component.
  const isoMatch = value.match(/^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?/);
  if (isoMatch) {
    const [, yyyy, mm, dd, hh, min, sec] = isoMatch;
    return buildDate(
      Number(yyyy),
      Number(mm),
      Number(dd),
      Number(hh ?? 0),
      Number(min ?? 0),
      Number(sec ?? 0),
    );
  }

  return null;
}

function buildDate(y: number, m: number, d: number, hh = 0, mm = 0, ss = 0): Date | null {
  const date = new Date(Date.UTC(y, m - 1, d, hh, mm, ss));
  if (Number.isNaN(date.getTime())) return null;
  // Guard against rollover (e.g. month 13, day 32).
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== m - 1 || date.getUTCDate() !== d) {
    return null;
  }
  return date;
}

/** Format a Date as an ISO calendar day (YYYY-MM-DD), or "unknown-date". */
export function formatDate(date: Date | null): string {
  if (!date) return "unknown-date";
  return date.toISOString().slice(0, 10);
}

/**
 * Parse a goal count that may appear as "2", "1.0", quoted, empty, or "NA".
 * Returns null when there is no usable score.
 */
export function parseGoals(raw: string | undefined | null): number | null {
  if (raw === undefined || raw === null) return null;
  const value = String(raw).trim();
  if (!value || value.toUpperCase() === "NA") return null;
  const num = Number(value);
  if (Number.isNaN(num)) return null;
  return Math.round(num);
}

/** Parse an integer field, returning null for blank/invalid values. */
export function parseIntOrNull(raw: string | undefined | null): number | null {
  if (raw === undefined || raw === null) return null;
  const value = String(raw).trim();
  if (!value) return null;
  const num = Number.parseInt(value, 10);
  return Number.isNaN(num) ? null : num;
}
