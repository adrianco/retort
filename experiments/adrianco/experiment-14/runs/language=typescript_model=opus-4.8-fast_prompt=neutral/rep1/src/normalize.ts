/**
 * Brazilian Soccer MCP — Normalization utilities
 * ----------------------------------------------
 * Context: The provided datasets describe the same real-world clubs with wildly
 * inconsistent spellings: with state suffixes ("Palmeiras-SP"), without
 * ("Palmeiras"), with accents ("Grêmio") or without ("Gremio"), in full form
 * ("Atletico Mineiro") or abbreviated ("Atlético-MG"). Dates appear in ISO,
 * Brazilian (DD/MM/YYYY) and datetime forms.
 *
 * This module centralizes all of that messiness so the rest of the system can
 * rely on a single canonical key per club and ISO dates everywhere. The key
 * piece is `canonicalTeam`, which maps any raw team string to a stable
 * `{ id, display }` pair. Ambiguous bases (Atlético, América, Botafogo — which
 * denote different clubs depending on state) are disambiguated by state.
 */

/** Brazilian state (UF) codes used as team-name suffixes. */
const UF_CODES = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
  "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
  "SP", "SE", "TO",
]);

/** Foreign country codes seen in Libertadores data (kept to disambiguate). */
const COUNTRY_CODES = new Set([
  "URU", "EQU", "ARG", "CHI", "COL", "PAR", "PER", "BOL", "VEN", "MEX",
]);

/** Remove diacritics and lowercase. */
export function stripDiacritics(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/**
 * Generic club-type tokens that carry no identity and are dropped so that
 * "Fortaleza FC" / "Fortaleza" and "EC Bahia" / "Bahia" canonicalize equally.
 * Identity-bearing words (atletico, gremio, sport, etc.) are deliberately
 * excluded — stripping them would merge distinct clubs.
 */
const SAFE_GENERIC = new Set([
  "fc", "ec", "sc", "ac", "ad", "cr", "aa", "cd", "se", "ca", "af",
  "futebol", "esporte", "esportivo", "clube", "club",
]);

function tokenKey(s: string): string {
  const base = stripDiacritics(s)
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const tokens = base.split(" ").filter((t) => t && !SAFE_GENERIC.has(t));
  // Never strip everything away (e.g. a club literally named "Sport").
  return (tokens.length ? tokens : base.split(" ")).join(" ").trim();
}

/**
 * Bases that map to multiple distinct clubs and therefore must keep their
 * state to stay distinct (e.g. Atlético-MG vs Atlético-PR vs Atlético-GO).
 */
const AMBIGUOUS_BASES = new Set([
  "atletico", "america", "botafogo", "nacional",
]);

/**
 * Explicit aliases: maps a normalized (accent-stripped, lowercased) full team
 * string — with any state already removed — to a canonical id. This resolves
 * full-name spellings that the generic logic can't, and unifies variants like
 * "Vasco" / "Vasco da Gama" or "Athletico Paranaense" / "Atlético-PR".
 */
const NAME_ALIASES: Record<string, string> = {
  "atletico mineiro": "atletico-mg",
  "atletico paranaense": "atletico-pr",
  "athletico paranaense": "atletico-pr",
  "atletico goianiense": "atletico-go",
  "atletico acreano": "atletico-ac",
  "america mineiro": "america-mg",
  "america de natal": "america-rn",
  "america fc natal": "america-rn",
  "america rn": "america-rn",
  "america mg": "america-mg",
  "vasco da gama": "vasco",
  "vasco": "vasco",
  "red bull bragantino": "bragantino",
  "rb bragantino": "bragantino",
  "bragantino": "bragantino",
  "athletic club mg": "athletic-mg",
  "gremio prudente": "gremio-prudente",
  "botafogo sp": "botafogo-sp",
  // Sport Recife appears as "Sport", "Sport-PE" and "Sport Recife" — unify.
  "sport": "sport",
  "sport recife": "sport",
  "sport pe": "sport",
  "sport club do recife": "sport",
  "sport club recife": "sport",
  "sport recife pe": "sport",
};

/**
 * Curated display names (with proper accents/casing) for canonical ids that
 * benefit from it. Ids not present here fall back to a title-cased base.
 */
const DISPLAY_NAMES: Record<string, string> = {
  "flamengo": "Flamengo",
  "fluminense": "Fluminense",
  "palmeiras": "Palmeiras",
  "santos": "Santos",
  "corinthians": "Corinthians",
  "sao paulo": "São Paulo",
  "gremio": "Grêmio",
  "internacional": "Internacional",
  "cruzeiro": "Cruzeiro",
  "vasco": "Vasco da Gama",
  "bahia": "Bahia",
  "fortaleza": "Fortaleza",
  "ceara": "Ceará",
  "sport": "Sport Recife",
  "vitoria": "Vitória",
  "goias": "Goiás",
  "coritiba": "Coritiba",
  "chapecoense": "Chapecoense",
  "avai": "Avaí",
  "figueirense": "Figueirense",
  "parana": "Paraná",
  "nautico": "Náutico",
  "ponte preta": "Ponte Preta",
  "portuguesa": "Portuguesa",
  "juventude": "Juventude",
  "criciuma": "Criciúma",
  "bragantino": "Red Bull Bragantino",
  "atletico-mg": "Atlético-MG",
  "atletico-pr": "Athletico-PR",
  "atletico-go": "Atlético-GO",
  "america-mg": "América-MG",
  "america-rn": "América-RN",
  "botafogo-rj": "Botafogo-RJ",
  "santa cruz": "Santa Cruz",
};

function titleCase(s: string): string {
  // Capitalize the first letter of each whitespace-separated word. Using a
  // Unicode-aware "start or space" anchor (rather than \b\w) avoids spuriously
  // uppercasing letters that follow accented characters, e.g. "São Luís".
  return s.replace(/(^|\s)(\p{L})/gu, (_m, pre, ch) => pre + ch.toUpperCase());
}

export interface CanonicalTeam {
  id: string;
  display: string;
}

const teamCache = new Map<string, CanonicalTeam>();

/**
 * Map any raw team string to a stable canonical `{ id, display }`.
 *
 * Strategy:
 *   1. Strip a trailing state/country code suffix (capturing the state).
 *   2. Build a normalized base key (accent-free, lowercase, punctuation-free).
 *   3. Resolve via the explicit alias table when possible.
 *   4. Otherwise: for ambiguous bases keep the state in the id; for everything
 *      else the base itself is the id.
 */
export function canonicalTeam(raw: string): CanonicalTeam {
  const cached = teamCache.get(raw);
  if (cached) return cached;

  let work = (raw ?? "").trim();

  // Drop parenthetical country codes like "(URU)".
  work = work.replace(/\(([^)]*)\)/g, (m, inner) => {
    const code = stripDiacritics(String(inner)).toUpperCase().trim();
    return COUNTRY_CODES.has(code) || UF_CODES.has(code) ? "" : m;
  });

  // Extract a trailing state code separated by "-", "/", "–" or whitespace.
  let state: string | null = null;
  const suffixMatch = work.match(/^(.*?)[\s]*[-/–]?\s*([A-Za-z]{2,3})\s*$/);
  if (suffixMatch) {
    const candidate = stripDiacritics(suffixMatch[2]).toUpperCase();
    const hadSeparator = /[-/–]\s*[A-Za-z]{2,3}\s*$/.test(work) ||
      /\s[A-Za-z]{2}\s*$/.test(work);
    if ((UF_CODES.has(candidate) || COUNTRY_CODES.has(candidate)) && hadSeparator) {
      state = UF_CODES.has(candidate) ? candidate.toLowerCase() : candidate.toLowerCase();
      work = suffixMatch[1];
    }
  }

  // Unify spelling variants before keying. "Athletico" (Paranaense) is the
  // modern spelling of "Atlético" Paranaense; collapse so both reach the same
  // canonical id regardless of which source used which spelling.
  const base = tokenKey(work).replace(/\bathletico\b/g, "atletico");

  // Build the lookup candidates for the alias table.
  const aliasKey = state ? `${base} ${state}` : base;
  let id =
    NAME_ALIASES[base] ??
    NAME_ALIASES[aliasKey] ??
    null;

  if (!id) {
    if (AMBIGUOUS_BASES.has(base) && state) {
      id = `${base}-${state}`;
    } else {
      id = base;
    }
  }

  const display =
    DISPLAY_NAMES[id] ??
    (state && AMBIGUOUS_BASES.has(base)
      ? `${titleCase(base)}-${state.toUpperCase()}`
      : titleCase(work.trim() || base));

  const result: CanonicalTeam = { id: id || base || "unknown", display };
  teamCache.set(raw, result);
  return result;
}

/** Convenience: just the canonical id for a raw team string. */
export function teamId(raw: string): string {
  return canonicalTeam(raw).id;
}

/**
 * Parse the many date formats present in the datasets into an ISO `YYYY-MM-DD`
 * string. Handles:
 *   - "2023-09-24" / "2012-05-19 18:30:00" (ISO, optionally with time)
 *   - "29/03/2003" (Brazilian DD/MM/YYYY)
 * Returns null when the value cannot be parsed.
 */
export function parseDate(raw: string | undefined | null): string | null {
  if (!raw) return null;
  const s = raw.trim();
  if (!s) return null;

  // ISO (optionally with time component).
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;

  // Brazilian DD/MM/YYYY.
  const br = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (br) {
    const dd = br[1].padStart(2, "0");
    const mm = br[2].padStart(2, "0");
    return `${br[3]}-${mm}-${dd}`;
  }

  return null;
}

/** Parse a number that may be a float-encoded int ("2.0") or empty. */
export function parseNum(raw: string | undefined | null): number | null {
  if (raw === undefined || raw === null) return null;
  const s = String(raw).trim();
  if (s === "" || s.toLowerCase() === "nan") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

/** Parse an integer (rounding floats like "2.0"). */
export function parseInt0(raw: string | undefined | null): number | null {
  const n = parseNum(raw);
  return n === null ? null : Math.round(n);
}
