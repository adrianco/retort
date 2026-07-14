/**
 * Normalization helpers for the Brazilian Soccer knowledge base.
 *
 * The datasets use inconsistent conventions for team names (state suffixes,
 * accents, country codes, full club names) and dates (ISO, Brazilian
 * DD/MM/YYYY). These helpers produce stable, accent-free, lower-cased lookup
 * keys for teams and parse the various date formats into `Date` objects so that
 * downstream query code can match and sort reliably.
 */

/** Remove diacritics (accents, cedilla) while preserving base letters. */
export function removeAccents(input: string): string {
  return input.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/**
 * Aliases mapping a normalized fragment to a canonical team key. These collapse
 * the most common cross-dataset naming differences for popular Brazilian clubs,
 * including the state-qualified forms of clubs that share a base name.
 */
const TEAM_ALIASES: Record<string, string> = {
  "sport": "sport recife",
  "sport recife": "sport recife",
  "athletico": "athletico paranaense",
  "athletico paranaense": "athletico paranaense",
  "atletico paranaense": "athletico paranaense",
  "atletico pr": "athletico paranaense",
  "athletico pr": "athletico paranaense",
  "atletico mg": "atletico mineiro",
  "atletico mineiro": "atletico mineiro",
  "america mg": "america mineiro",
  "america mineiro": "america mineiro",
};

/**
 * Base names that are shared by more than one real club, where the state suffix
 * is the only distinguishing feature (e.g. Atlético-MG vs Atlético-PR). For
 * these we retain the suffix in the key instead of stripping it, so the clubs do
 * not collapse into one.
 */
const AMBIGUOUS_BASES = new Set(["atletico", "america"]);

/**
 * Produce a canonical lookup key for a team name:
 *  - strip accents and lower-case
 *  - detect and remove a trailing state suffix ("-SP", " - MG") or country
 *    code ("(URU)"), keeping it only when the base name is ambiguous
 *  - collapse whitespace
 *  - apply a small alias table for well-known clubs
 */
export function normalizeTeamName(raw: string): string {
  let s = removeAccents(raw).toLowerCase();

  // Detect a state/country suffix: parenthesised code or trailing 2-3 letters.
  let suffix = "";
  const paren = s.match(/\s*\(([a-z]{2,3})\)\s*$/);
  if (paren) {
    suffix = paren[1];
    s = s.replace(/\s*\([a-z]{2,3}\)\s*$/, "");
  } else {
    const dash = s.match(/[\s\-–]+([a-z]{2,3})\s*$/);
    if (dash) {
      suffix = dash[1];
      s = s.replace(/[\s\-–]+[a-z]{2,3}\s*$/, "");
    }
  }

  // Collapse whitespace; `s` is now the base name.
  s = s.replace(/\s+/g, " ").trim();

  // For ambiguous bases, keep the state suffix so distinct clubs stay distinct.
  const key = suffix && AMBIGUOUS_BASES.has(s) ? `${s} ${suffix}` : s;

  return TEAM_ALIASES[key] ?? TEAM_ALIASES[s] ?? key;
}

/**
 * Produce a lookup key for a free-text name (player, club) without stripping
 * trailing short tokens the way team normalization does. Accent-free,
 * lower-cased, whitespace-collapsed.
 */
export function normalizeName(raw: string): string {
  return removeAccents(raw).toLowerCase().replace(/\s+/g, " ").trim();
}

/**
 * Determine whether a stored team name matches a user-provided query. Matching
 * is tolerant: equal canonical keys, or the query key appearing as a token /
 * substring of the team's canonical key (so "Boavista" matches a long official
 * club name).
 */
export function teamMatches(teamName: string, query: string): boolean {
  const team = normalizeTeamName(teamName);
  const q = normalizeTeamName(query);
  if (!q || !team) return false;
  if (team === q) return true;
  // Whole-word / substring containment in either direction.
  return team.includes(q) || q.includes(team);
}

/**
 * Parse the multiple date formats found across datasets into a UTC `Date`:
 *  - "2012-05-19 18:30:00" (ISO with time)
 *  - "2023-09-24" (ISO date)
 *  - "29/03/2003" (Brazilian DD/MM/YYYY)
 * Returns null for empty/unparseable values (including "NA").
 */
export function parseDate(value: string | null | undefined): Date | null {
  if (value == null) return null;
  const s = value.trim();
  if (!s || s.toUpperCase() === "NA") return null;

  // ISO date or datetime.
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if (iso) {
    const [, y, m, d, hh, mm, ss] = iso;
    return new Date(
      Date.UTC(+y, +m - 1, +d, hh ? +hh : 0, mm ? +mm : 0, ss ? +ss : 0)
    );
  }

  // Brazilian DD/MM/YYYY (optionally with time).
  const br = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
  if (br) {
    const [, d, m, y, hh, mm] = br;
    return new Date(Date.UTC(+y, +m - 1, +d, hh ? +hh : 0, mm ? +mm : 0, 0));
  }

  return null;
}

/** Format a date as YYYY-MM-DD (UTC), or "unknown date" when null. */
export function formatDate(date: Date | null): string {
  if (!date) return "unknown date";
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
