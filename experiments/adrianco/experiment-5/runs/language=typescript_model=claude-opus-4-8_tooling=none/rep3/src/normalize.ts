/**
 * ============================================================================
 * Context: Brazilian Soccer MCP Server — Name & Value Normalization
 * ----------------------------------------------------------------------------
 * Purpose : Brazilian soccer datasets use inconsistent team naming ("Palmeiras"
 *           vs "Palmeiras-SP" vs "Nacional (URU)"), accents (São Paulo / Sao
 *           Paulo), and several date formats. These helpers produce stable,
 *           comparable keys and clean display strings so the query layer can
 *           match teams reliably regardless of source formatting.
 * Consumers: dataLoader.ts, queries.ts, server.ts.
 * Note     : `normalizeKey` is the canonical matching key — accent-folded,
 *           lower-cased, suffix-stripped. Never show it to users; use the
 *           cleaned display name from `cleanTeamName` for output.
 * ============================================================================
 */

/** Remove diacritics (accents, cedilla) so "Grêmio" === "Gremio" for matching. */
export function stripAccents(input: string): string {
  // ̀-ͯ is the Unicode "Combining Diacritical Marks" block.
  return input.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/**
 * Strip a trailing state/country qualifier from a raw team name.
 * Handles "Palmeiras-SP", "Palmeiras - SP", and "Nacional (URU)".
 */
export function cleanTeamName(raw: string): string {
  if (!raw) return "";
  let name = raw.trim();
  // Parenthetical country/state suffix: "Nacional (URU)"
  name = name.replace(/\s*\([^)]*\)\s*$/u, "");
  // Hyphenated 2-3 letter state/country suffix: "Palmeiras-SP", "America - MG"
  name = name.replace(/\s*-\s*[A-Za-z]{2,3}\s*$/u, "");
  return name.trim();
}

/**
 * Canonical matching key for a team: cleaned, accent-folded, lower-cased,
 * punctuation-collapsed. Used for all equality/contains comparisons.
 */
export function normalizeKey(raw: string): string {
  return stripAccents(cleanTeamName(raw))
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Loose match: does a team name match a user-supplied query? True when either
 * key contains the other (so "Sao Paulo" matches "São Paulo FC" and vice
 * versa, and "Flamengo" matches "Flamengo-RJ").
 */
export function teamMatches(teamName: string, query: string): boolean {
  const a = normalizeKey(teamName);
  const b = normalizeKey(query);
  if (!a || !b) return false;
  return a === b || a.includes(b) || b.includes(a);
}

/** Generic accent-insensitive substring test for free-text fields. */
export function looseIncludes(haystack: string, needle: string): boolean {
  if (!needle) return true;
  return stripAccents(haystack ?? "")
    .toLowerCase()
    .includes(stripAccents(needle).toLowerCase());
}

/**
 * Parse the various date encodings into ISO `YYYY-MM-DD`.
 *  - "2012-05-19 18:30:00"  (ISO with time)
 *  - "2023-09-24"           (ISO)
 *  - "29/03/2003"           (Brazilian DD/MM/YYYY)
 * Returns null when no valid date can be extracted.
 */
export function parseDate(raw: string | undefined | null): string | null {
  if (!raw) return null;
  const value = raw.trim();
  if (!value || value.toUpperCase() === "NA") return null;

  // ISO date, optionally followed by a time component.
  const iso = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) {
    return `${iso[1]}-${iso[2]}-${iso[3]}`;
  }

  // Brazilian DD/MM/YYYY (also accepts D/M/YYYY).
  const br = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (br) {
    const day = br[1].padStart(2, "0");
    const month = br[2].padStart(2, "0");
    return `${br[3]}-${month}-${day}`;
  }

  return null;
}

/** Extract a 4-digit year from an ISO date string, or null. */
export function yearFromIso(iso: string | null): number | null {
  if (!iso) return null;
  const m = iso.match(/^(\d{4})/);
  return m ? Number(m[1]) : null;
}

/** Parse a possibly-float, possibly-quoted goal value ("1.0", "2", "") to int|null. */
export function parseGoals(raw: string | undefined | null): number | null {
  if (raw === undefined || raw === null) return null;
  const value = String(raw).trim();
  if (value === "" || value.toUpperCase() === "NA") return null;
  const n = Number(value);
  return Number.isFinite(n) ? Math.round(n) : null;
}

/** Parse an integer-ish field, tolerating empty/NA. */
export function parseIntSafe(raw: string | undefined | null): number | null {
  if (raw === undefined || raw === null) return null;
  const value = String(raw).trim();
  if (value === "" || value.toUpperCase() === "NA") return null;
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}
