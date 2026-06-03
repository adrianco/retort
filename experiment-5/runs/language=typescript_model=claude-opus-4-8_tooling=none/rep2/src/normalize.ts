/**
 * ============================================================================
 * File: src/normalize.ts
 * Project: Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * Context:
 *   Normalization helpers that absorb the data-quality issues called out in
 *   the specification:
 *     - Team name variations: state suffixes ("Palmeiras-SP", "América - MG"),
 *       country tags ("Nacional (URU)"), and verbose full names.
 *     - Multiple date formats: ISO ("2023-09-24"), ISO+time
 *       ("2012-05-19 18:30:00") and Brazilian ("29/03/2003").
 *     - UTF-8 accented characters (São, Grêmio, Avaí) and cedillas.
 *
 *   `teamKey()` produces an accent-free, lowercase, suffix-free matching key
 *   so the same club is matched consistently across datasets, while
 *   `teamDisplayName()` keeps a clean human-readable name.
 * ============================================================================
 */

/** Remove diacritics (accents, cedillas) from a string. */
export function stripAccents(input: string): string {
  return input.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/** Brazilian federative-unit (state) codes, used to strip state tags. */
const UF_CODES = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
  "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
  "SP", "SE", "TO",
]);

/**
 * Strip trailing state ("-SP", " - MG", " RJ"), country ("(URU)") tags and
 * common club-type abbreviations ("FC", "EC", "SC") from a raw team name,
 * returning a clean display name.
 */
export function teamDisplayName(raw: string): string {
  let name = (raw ?? "").trim();
  // Drop a parenthetical country/region tag, e.g. "Nacional (URU)".
  name = name.replace(/\s*\([^)]*\)\s*$/g, "").trim();
  // Drop a trailing state/country code separated by a hyphen,
  // with or without surrounding spaces: "Palmeiras-SP", "América - MG".
  name = name.replace(/\s*-\s*[A-Za-zÀ-ÿ]{2,3}\s*$/u, "").trim();
  // Drop a trailing whitespace-separated UF code: "Botafogo RJ".
  const tail = name.match(/^(.*\S)\s+([A-Za-z]{2})$/);
  if (tail && UF_CODES.has(tail[2].toUpperCase())) {
    name = tail[1].trim();
  }
  // Drop a trailing club-type abbreviation: "Fortaleza FC", "Bahia EC".
  name = name.replace(/\s+(FC|EC|SC|AC|CF|CR)$/i, "").trim();
  // Drop a leading club-type abbreviation: "EC Bahia", "FC Santos".
  name = name.replace(/^(FC|EC|SC|AC|CR|CA|SE|AA)\s+/i, "").trim();
  // Collapse internal whitespace.
  name = name.replace(/\s+/g, " ").trim();
  return name || raw.trim();
}

/**
 * Hand-curated aliases mapping alternative spellings to a canonical base key.
 * Keys and values are already accent-free + lowercase, with state stripped.
 * These fold long/variant names onto the short canonical form used elsewhere.
 */
const TEAM_ALIASES: Record<string, string> = {
  "atletico mineiro": "atletico mg",
  "atletico goianiense": "atletico go",
  "athletico paranaense": "athletico",
  "atletico paranaense": "athletico",
  "vasco da gama": "vasco",
  "red bull bragantino": "bragantino",
  "rb bragantino": "bragantino",
};

/**
 * Base names that collide once the state suffix is stripped (several distinct
 * clubs share them, e.g. Atlético-MG vs Atlético-GO, América-MG vs América-RN).
 * For these we keep the state in the key to avoid merging different clubs.
 */
const AMBIGUOUS_BASES = new Set(["atletico", "america"]);

/**
 * Aliases for the disambiguated "base + state" form. Atlético Paranaense is
 * written both as "Athletico" (with an h → base "athletico") and as
 * "Atlético-PR" (→ "atletico pr"); fold the latter onto the former.
 */
const COMBINED_ALIASES: Record<string, string> = {
  "atletico pr": "athletico",
};

/** Extract a 2-letter UF state code from a raw team name if present. */
export function extractState(raw: string): string | undefined {
  const value = raw ?? "";
  // Hyphen form: "Palmeiras-SP", "América - MG".
  const hyphen = value.match(/-\s*([A-Za-z]{2})\s*$/);
  if (hyphen && UF_CODES.has(hyphen[1].toUpperCase())) return hyphen[1].toUpperCase();
  // Whitespace form: "Botafogo RJ".
  const space = value.match(/\s([A-Za-z]{2})\s*$/);
  if (space && UF_CODES.has(space[1].toUpperCase())) return space[1].toUpperCase();
  return undefined;
}

/**
 * Produce a stable normalized lookup key for a team name. Strips suffixes,
 * accents and punctuation, lowercases, applies the alias table, and — only for
 * ambiguous shared base names — appends the (explicit or parsed) state code.
 */
export function teamKey(raw: string, explicitState?: string): string {
  const display = teamDisplayName(raw);
  let base = stripAccents(display).toLowerCase();
  base = base.replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
  base = TEAM_ALIASES[base] ?? base;

  if (AMBIGUOUS_BASES.has(base)) {
    const state = (explicitState || extractState(raw) || "").toLowerCase();
    const combined = state ? `${base} ${state}` : base;
    return COMBINED_ALIASES[combined] ?? combined;
  }
  return base;
}

/**
 * Parse the various date formats into an ISO date string (YYYY-MM-DD).
 * Returns null when the value cannot be interpreted.
 */
export function parseDate(raw: string | undefined | null): string | null {
  if (!raw) return null;
  const value = raw.trim();
  if (!value) return null;

  // ISO date, optionally followed by a time component.
  const iso = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) {
    return `${iso[1]}-${iso[2]}-${iso[3]}`;
  }

  // Brazilian DD/MM/YYYY (also supports DD/MM/YY rarely).
  const br = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})/);
  if (br) {
    const day = br[1].padStart(2, "0");
    const month = br[2].padStart(2, "0");
    let year = br[3];
    if (year.length === 2) year = `20${year}`;
    return `${year}-${month}-${day}`;
  }

  return null;
}

/** Derive the year from a parsed/raw date or explicit season cell. */
export function parseYear(
  dateIso: string | null,
  seasonRaw?: string | number | null,
): number | null {
  if (seasonRaw !== undefined && seasonRaw !== null && `${seasonRaw}`.trim()) {
    const n = parseInt(`${seasonRaw}`.trim(), 10);
    if (!Number.isNaN(n)) return n;
  }
  if (dateIso) {
    const n = parseInt(dateIso.slice(0, 4), 10);
    if (!Number.isNaN(n)) return n;
  }
  return null;
}

/** Parse a goal/number cell that may be "2", "2.0", '"2"' or empty. */
export function parseNumber(raw: string | number | undefined | null): number | null {
  if (raw === undefined || raw === null) return null;
  const value = `${raw}`.trim().replace(/^"|"$/g, "");
  if (!value) return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

/** Parse an integer, returning null on failure. */
export function parseInteger(raw: string | number | undefined | null): number | null {
  const n = parseNumber(raw);
  return n === null ? null : Math.trunc(n);
}
