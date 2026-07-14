import type { TeamKey } from "./types.js";

/** Brazilian state abbreviations plus a handful of South American country
 * codes that appear as suffixes in the Libertadores dataset (e.g. "Barcelona-EQU"). */
const STATE_CODES = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
  "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
  "URU", "ARG", "CHI", "PAR", "BOL", "EQU", "COL", "PER", "VEN", "MEX",
]);

export function stripDiacritics(input: string): string {
  return input.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/** Lowercased, accent-free, punctuation-collapsed comparison key. */
export function normalizeKey(input: string): string {
  return stripDiacritics(input)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

/** Parses a raw team name (e.g. "Palmeiras-SP", "América - MG", "Botafogo RJ")
 * into a display name and a normalized key, splitting off a trailing state
 * (or country) code when one is recognized. Names without a recognizable
 * suffix are left untouched. */
export function parseTeamName(rawInput: string): TeamKey {
  const raw = rawInput.trim();
  const withoutParens = raw.replace(/\s*\([^)]*\)\s*/g, " ").trim();
  const unifiedHyphen = withoutParens.replace(/\s*-\s*/g, "-");

  let base = unifiedHyphen;
  let state: string | null = null;

  const hyphenMatch = unifiedHyphen.match(/^(.+)-([A-Za-z]{2,3})$/);
  if (hyphenMatch && hyphenMatch[1].trim().length >= 2 && STATE_CODES.has(hyphenMatch[2].toUpperCase())) {
    base = hyphenMatch[1];
    state = hyphenMatch[2].toUpperCase();
  } else {
    const spaceMatch = unifiedHyphen.match(/^(.+)\s+([A-Za-z]{2,3})$/);
    if (spaceMatch && spaceMatch[1].trim().length >= 3 && STATE_CODES.has(spaceMatch[2].toUpperCase())) {
      base = spaceMatch[1];
      state = spaceMatch[2].toUpperCase();
    }
  }

  base = base.trim();
  const baseKey = normalizeKey(base);
  const key = state ? `${baseKey}-${state.toLowerCase()}` : baseKey;
  const display = state ? `${base}-${state}` : base;

  return { raw: rawInput, display, baseKey, state, key };
}

/** Does `candidate` (a parsed team from the dataset) match `query` (a raw
 * team name typed by a user/LLM)? Matches on exact key first, then falls
 * back to base-name matching when the query has no state suffix, then to a
 * loose substring match so partial names still resolve. */
export function teamKeyMatchesQuery(candidate: TeamKey, query: string): boolean {
  const q = parseTeamName(query);
  if (candidate.key === q.key) return true;
  // Both sides name a state/country: if they disagree, this is a different
  // club sharing a base name (e.g. Atletico-MG vs Atletico-GO) - don't match.
  if (q.state && candidate.state && q.state !== candidate.state) return false;
  if (candidate.baseKey === q.baseKey) return true;
  if (q.baseKey.length >= 4 && (candidate.baseKey.includes(q.baseKey) || q.baseKey.includes(candidate.baseKey))) {
    return true;
  }
  return false;
}

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/;
const BR_DATE = /^(\d{2})\/(\d{2})\/(\d{4})$/;

/** Parses either ISO ("2023-09-24", "2012-05-19 18:30:00") or Brazilian
 * ("29/03/2003") date formats into a UTC Date. Returns null when unparsable. */
export function parseFlexibleDate(input: string | null | undefined): Date | null {
  if (!input) return null;
  const trimmed = input.trim();
  if (!trimmed) return null;

  const iso = trimmed.match(ISO_DATE);
  if (iso) {
    const [, y, mo, d, h = "0", mi = "0", s = "0"] = iso;
    return new Date(Date.UTC(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi), Number(s)));
  }

  const br = trimmed.match(BR_DATE);
  if (br) {
    const [, d, mo, y] = br;
    return new Date(Date.UTC(Number(y), Number(mo) - 1, Number(d)));
  }

  return null;
}

export function formatDate(date: Date | null): string | null {
  if (!date) return null;
  return date.toISOString().slice(0, 10);
}
