/**
 * Text, number and date normalisation helpers shared by the loaders and the
 * query engine.
 */

/** Remove diacritics: "São Paulo" -> "Sao Paulo", "Grêmio" -> "Gremio". */
export function stripAccents(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/** Lower-case, accent-free, single-spaced text suitable for comparisons. */
export function foldText(s: string): string {
  return stripAccents(s).toLowerCase().replace(/\s+/g, " ").trim();
}

/** Parse an integer-ish cell ("2", "2.0", " 3 ") - returns null for blanks/NA. */
export function parseNum(s: string | undefined): number | null {
  if (s === undefined) return null;
  const t = s.trim();
  if (t === "" || t.toUpperCase() === "NA" || t.toLowerCase() === "nan") return null;
  const v = Number(t);
  return Number.isFinite(v) ? v : null;
}

export function parseIntOrNull(s: string | undefined): number | null {
  const v = parseNum(s);
  return v === null ? null : Math.round(v);
}

export interface ParsedDate {
  /** ISO date YYYY-MM-DD */
  date: string;
  /** HH:MM if known */
  time?: string;
}

const pad = (n: number) => String(n).padStart(2, "0");

/**
 * Parse the date formats found in the datasets (and accepted from users):
 *  - ISO "2023-09-24", optionally with time "2012-05-19 18:30:00" or "T" separator
 *  - Brazilian "29/03/2003" (DD/MM/YYYY), optionally with time
 *  - Year-only "2019" (interpreted as 1 January) for convenience
 */
export function parseDate(input: string | undefined | null): ParsedDate | null {
  if (!input) return null;
  const s = input.trim();
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::\d{2})?)?/);
  if (m) {
    const date = `${m[1]}-${pad(+m[2])}-${pad(+m[3])}`;
    return m[4] ? { date, time: `${pad(+m[4])}:${m[5]}` } : { date };
  }
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::\d{2})?)?/);
  if (m) {
    const date = `${m[3]}-${pad(+m[2])}-${pad(+m[1])}`;
    return m[4] ? { date, time: `${pad(+m[4])}:${m[5]}` } : { date };
  }
  m = s.match(/^(\d{4})$/);
  if (m) return { date: `${m[1]}-01-01` };
  return null;
}

/** Days between two ISO dates (absolute value). */
export function daysBetween(a: string, b: string): number {
  return Math.abs(Date.parse(a) - Date.parse(b)) / 86_400_000;
}

export function pct(num: number, den: number): string {
  if (den === 0) return "0.0%";
  return `${((100 * num) / den).toFixed(1)}%`;
}
