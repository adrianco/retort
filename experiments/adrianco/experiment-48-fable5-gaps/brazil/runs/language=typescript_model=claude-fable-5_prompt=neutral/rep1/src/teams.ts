/**
 * Team name normalization.
 *
 * The datasets use several naming conventions for the same club:
 *   - "Palmeiras-SP", "Palmeiras" (with/without state suffix)
 *   - "América - MG", "America MG", "América-MG" (spacing/accents vary)
 *   - "Sao Paulo" vs "São Paulo" (diacritics stripped in some files)
 *   - "Athletico Paranaense" vs "Athletico-PR" vs "Atlético-PR" (renames)
 *   - "Nacional (URU)", "Barcelona-EQU" (Libertadores country suffixes)
 *
 * Every team name is reduced to a { base, region } pair:
 *   base   – accent-free, lowercase club name with suffixes removed
 *   region – Brazilian state (SP, RJ, ...) or country code (URU, ARG, ...)
 *            when one can be derived from the name; otherwise undefined.
 *
 * Two names refer to the same club when the bases match and the regions
 * do not conflict (a missing region matches any region). This lets a
 * query for "Flamengo" find "Flamengo-RJ" while keeping "América-MG"
 * and "América-RN" distinct.
 */

const BRAZILIAN_STATES = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
  "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
  "SP", "SE", "TO",
]);

const COUNTRY_CODES = new Set([
  "ARG", "BOL", "BRA", "CHI", "COL", "EQU", "ECU", "MEX", "PAR", "PER",
  "URU", "VEN",
]);

export interface TeamName {
  /** Original name exactly as it appears in the dataset. */
  raw: string;
  /** Human-friendly display name (raw with redundant suffix noise trimmed). */
  display: string;
  /** Normalized accent-free lowercase base name. */
  base: string;
  /** State or country code derived from the name, if any. */
  region?: string;
  /** Stable canonical key: base plus region when known. */
  key: string;
}

export function stripDiacritics(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/**
 * Aliases applied to the normalized base name (after diacritic removal and
 * lowercasing). Maps variant spellings/renames to one canonical base, and
 * fills in the region for names that embed it in words.
 */
const ALIASES: Record<string, { base: string; region?: string }> = {
  "athletico paranaense": { base: "athletico", region: "PR" },
  "atletico paranaense": { base: "athletico", region: "PR" },
  "atletico": { base: "athletico" }, // only when region PR — handled below
  "atletico mineiro": { base: "atletico", region: "MG" },
  "atletico goianiense": { base: "atletico", region: "GO" },
  "america mineiro": { base: "america", region: "MG" },
  "america fc natal": { base: "america", region: "RN" },
  "gremio fbpa": { base: "gremio" },
  "sport recife": { base: "sport", region: "PE" },
  "sport club do recife": { base: "sport", region: "PE" },
  "sao paulo fc": { base: "sao paulo" },
  "ec bahia": { base: "bahia" },
  "ec vitoria": { base: "vitoria", region: "BA" },
  "esporte clube vitoria": { base: "vitoria", region: "BA" },
  "red bull bragantino": { base: "bragantino", region: "SP" },
  "rb bragantino": { base: "bragantino", region: "SP" },
  "bragantino": { base: "bragantino", region: "SP" },
  "vasco da gama": { base: "vasco", region: "RJ" },
  "cr vasco da gama": { base: "vasco", region: "RJ" },
  "clube de regatas vasco da gama": { base: "vasco", region: "RJ" },
  "botafogo fr": { base: "botafogo", region: "RJ" },
  "botafogo de futebol e regatas": { base: "botafogo", region: "RJ" },
  "chapecoense af": { base: "chapecoense", region: "SC" },
  "associacao chapecoense de futebol": { base: "chapecoense", region: "SC" },
  "ponte preta": { base: "ponte preta", region: "SP" },
  "aa ponte preta": { base: "ponte preta", region: "SP" },
  "csa al": { base: "csa", region: "AL" },
  "santa cruz pe": { base: "santa cruz", region: "PE" },
};

/**
 * Extract a trailing state/country suffix from a raw name.
 * Recognized forms: "Name-SP", "Name - SP", "Name SP", "Name (URU)", "Name-EQU".
 */
function extractSuffix(name: string): { core: string; region?: string } {
  let core = name.trim();
  let region: string | undefined;

  // Parenthetical country/state: "Nacional (URU)"
  const paren = core.match(/^(.*?)\s*\(([A-Za-z]{2,3})\)\s*$/);
  if (paren) {
    const code = paren[2].toUpperCase();
    if (BRAZILIAN_STATES.has(code) || COUNTRY_CODES.has(code)) {
      core = paren[1].trim();
      region = code === "ECU" ? "EQU" : code;
      return { core, region };
    }
  }

  // Hyphen or spaced-hyphen suffix: "Palmeiras-SP", "América - MG", "Barcelona-EQU"
  const hyphen = core.match(/^(.*?)\s*-\s*([A-Za-z]{2,3})\s*$/);
  if (hyphen) {
    const code = hyphen[2].toUpperCase();
    if (BRAZILIAN_STATES.has(code) || COUNTRY_CODES.has(code)) {
      core = hyphen[1].trim();
      region = code === "ECU" ? "EQU" : code;
      return { core, region };
    }
  }

  // Trailing bare state token: "America MG", "Boavista RJ" (uppercase only,
  // so "Grêmio" or clubs whose name ends in a real word are unaffected).
  const bare = core.match(/^(.{2,}?)\s+([A-Z]{2})$/);
  if (bare && BRAZILIAN_STATES.has(bare[2])) {
    core = bare[1].trim();
    region = bare[2];
    return { core, region };
  }

  return { core };
}

export function normalizeTeamName(raw: string): TeamName {
  const cleaned = raw.replace(/\s+/g, " ").trim();
  // Drop parenthetical annotations that are not region codes,
  // e.g. "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ".
  const noNotes = cleaned.replace(/\(([^)]{4,})\)/g, " ").replace(/\s+/g, " ").trim();

  const { core, region: suffixRegion } = extractSuffix(noNotes);
  let base = stripDiacritics(core).toLowerCase().replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  let region = suffixRegion;

  // Strip leading/trailing club-type abbreviations ("EC Bahia", "Fortaleza FC",
  // "Santos FC") so the same club normalizes identically across files. Only
  // strip when a meaningful name remains.
  const CLUB_TOKENS = new Set(["fc", "ec", "sc", "ac", "cr", "aa", "ad", "se", "cd", "afc", "esporte clube", "futebol clube"]);
  let words = base.split(" ");
  while (words.length > 1 && CLUB_TOKENS.has(words[0])) words = words.slice(1);
  while (words.length > 1 && CLUB_TOKENS.has(words[words.length - 1])) words = words.slice(0, -1);
  if (words.join(" ").length >= 3) base = words.join(" ");

  const alias = ALIASES[base];
  if (alias) {
    // "atletico" only means Athletico Paranaense when the PR suffix says so.
    if (base === "atletico") {
      if (region === "PR") base = "athletico";
    } else {
      base = alias.base;
      if (!region && alias.region) region = alias.region;
    }
  }

  const key = region ? `${base}-${region.toLowerCase()}` : base;
  const display = core || cleaned;
  return { raw, display, base, region, key };
}

/**
 * True when a stored team name matches a user query. Bases must match
 * exactly, or the query must be a whole-word prefix/substring of the base
 * (so "corinthians" finds "sport club corinthians paulista"). A region
 * constraint on either side only conflicts when both sides specify
 * different regions.
 */
export function teamMatches(team: TeamName, query: TeamName): boolean {
  const baseMatch =
    team.base === query.base ||
    (query.base.length >= 4 &&
      new RegExp(`(^| )${escapeRegExp(query.base)}( |$)`).test(team.base));
  if (!baseMatch) return false;
  if (team.region && query.region && team.region !== query.region) return false;
  return true;
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Convenience: does a raw stored name match a raw query string? */
export function namesMatch(storedRaw: string, queryRaw: string): boolean {
  return teamMatches(normalizeTeamName(storedRaw), normalizeTeamName(queryRaw));
}
