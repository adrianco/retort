/**
 * Context
 * -------
 * Team-name and date normalization helpers.
 *
 * The datasets name the same club many different ways:
 *   "Palmeiras-SP", "Palmeiras", "América - MG", "Nacional (URU)",
 *   "Sport Club Corinthians Paulista", "Sao Paulo", "São Paulo".
 *
 * `normalizeTeamName` produces a clean display name (suffixes stripped),
 * and `canonicalKey` produces an accent-insensitive, lowercase key plus a
 * small alias table so the query layer can match user input ("flamengo",
 * "Sao Paulo") against any of the raw spellings.
 *
 * Dates appear as ISO ("2023-09-24"), Brazilian ("29/03/2003") and with a
 * time component ("2012-05-19 18:30:00"). `normalizeDate` returns a plain
 * ISO YYYY-MM-DD string for all of them.
 */

/** Remove diacritics (ç -> c, ã -> a, ê -> e, ...) and lowercase. */
export function stripAccents(input: string): string {
  return input
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

/**
 * Strip trailing state / country suffixes and surrounding noise from a raw
 * team string, returning a tidy display name.
 *
 * Handles: "-SP", " - MG", " (URU)", " (EQU)", trailing parenthetical codes.
 */
/** Two-letter Brazilian state codes that appear as team-name suffixes. */
const STATE_CODES = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
  "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]);

/** Club-type abbreviation tokens to drop (e.g. "São Paulo FC", "EC Bahia"). */
const CLUB_TOKENS = new Set(["FC", "EC", "SC", "AC", "CR", "SE", "AA", "CA", "FBC"]);

export function normalizeTeamName(raw: string): string {
  if (!raw) return "";
  let name = raw.trim();

  // Remove a trailing parenthetical country/state code, e.g. "Nacional (URU)".
  name = name.replace(/\s*\([A-Za-zÀ-ÿ.\s]{2,4}\)\s*$/u, "").trim();

  // Remove " - MG" / "- RJ" style suffixes (space-dash-space-CODE).
  name = name.replace(/\s*-\s*[A-Z]{2}\s*$/u, "").trim();

  // Remove "-SP" style attached suffixes (no spaces).
  name = name.replace(/-[A-Z]{2}$/u, "").trim();

  // Drop a trailing standalone state code with no dash, e.g. "Botafogo RJ".
  // Skip if it is the only token (so a club literally named by a code survives).
  let tokens = name.split(/\s+/).filter(Boolean);
  if (tokens.length > 1 && STATE_CODES.has(tokens[tokens.length - 1])) {
    tokens = tokens.slice(0, -1);
  }

  // Drop club-type abbreviation tokens ("FC", "EC", ...) when not the whole name.
  if (tokens.length > 1) {
    tokens = tokens.filter((t) => !CLUB_TOKENS.has(t));
  }

  name = tokens.join(" ").replace(/\s+/g, " ").trim();
  return name;
}

/**
 * Alias table mapping common alternate spellings to a single canonical key.
 * Keys and values are already accent-stripped + lowercased.
 */
const ALIASES: Record<string, string> = {
  // Atlético Mineiro (no "h") vs Athletico Paranaense ("h"): the short forms
  // "Atletico" / "Athletico" left after suffix-stripping map to the full club.
  "atletico": "atletico mineiro",
  "atletico mineiro": "atletico mineiro",
  "athletico": "athletico paranaense",
  "athletico paranaense": "athletico paranaense",
  "atletico paranaense": "athletico paranaense",
  // Vasco da Gama is universally called Vasco.
  "vasco da gama": "vasco",
  "vasco": "vasco",
};

/**
 * Produce an accent-insensitive matching key for a (raw or display) team name.
 * Applies suffix stripping first, then accent stripping, then alias mapping.
 */
export function canonicalKey(raw: string): string {
  const display = normalizeTeamName(raw);
  const key = stripAccents(display).replace(/\s+/g, " ").trim();
  return ALIASES[key] ?? key;
}

/**
 * Returns true when `query` should be considered a match for team `raw`.
 * Matching is accent-insensitive and based on the canonical key, but also
 * allows substring matches so "atletico" finds "Atletico Mineiro".
 */
export function teamMatches(raw: string, query: string): boolean {
  if (!query) return false;
  const teamKey = canonicalKey(raw);
  const queryKey = canonicalKey(query);
  if (!teamKey) return false;
  if (teamKey === queryKey) return true;
  // Substring match in both directions for partial team names.
  return teamKey.includes(queryKey) || queryKey.includes(teamKey);
}

/** Parse a numeric value that may be quoted, blank, "NA" or a float string. */
export function parseIntSafe(value: string | undefined | null): number | null {
  if (value == null) return null;
  const trimmed = String(value).trim();
  if (trimmed === "" || trimmed.toUpperCase() === "NA") return null;
  const n = Number(trimmed);
  return Number.isFinite(n) ? Math.round(n) : null;
}

/**
 * Normalize a date in ISO, Brazilian (DD/MM/YYYY) or datetime form into a
 * plain ISO YYYY-MM-DD string. Returns null when it cannot be parsed.
 */
export function normalizeDate(value: string | undefined | null): string | null {
  if (value == null) return null;
  const raw = String(value).trim();
  if (raw === "" || raw.toUpperCase() === "NA") return null;

  // ISO or datetime: take the date portion before any space or 'T'.
  const isoMatch = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) {
    return `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`;
  }

  // Brazilian DD/MM/YYYY (optionally with time).
  const brMatch = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (brMatch) {
    const day = brMatch[1].padStart(2, "0");
    const month = brMatch[2].padStart(2, "0");
    return `${brMatch[3]}-${month}-${day}`;
  }

  return null;
}
