/**
 * Date parsing for the formats found in the datasets and in user input:
 *   "2023-09-24", "2012-05-19 18:30:00", "29/03/2003", "2023-09-24T20:00:00Z".
 * Everything is converted to ISO "YYYY-MM-DD" strings, which sort lexically.
 */

export interface ParsedDate {
  date: string;
  time?: string;
}

const pad = (n: number) => String(n).padStart(2, "0");

function valid(y: number, m: number, d: number): boolean {
  return y > 1800 && m >= 1 && m <= 12 && d >= 1 && d <= 31;
}

export function parseDate(raw: string | undefined | null): ParsedDate | null {
  if (!raw) return null;
  const s = raw.trim();
  if (!s || s.toUpperCase() === "NA") return null;

  let m = /^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?/.exec(s);
  if (m) {
    const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
    if (!valid(y, mo, d)) return null;
    return { date: `${y}-${pad(mo)}-${pad(d)}`, time: m[4] ? `${pad(Number(m[4]))}:${m[5]}` : undefined };
  }
  m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?/.exec(s);
  if (m) {
    const [d, mo, y] = [Number(m[1]), Number(m[2]), Number(m[3])];
    if (!valid(y, mo, d)) return null;
    return { date: `${y}-${pad(mo)}-${pad(d)}`, time: m[4] ? `${pad(Number(m[4]))}:${m[5]}` : undefined };
  }
  return null;
}

/** Normalise a user-supplied date bound; a bare year expands to its first/last day. */
export function normalizeDateBound(raw: string | undefined, end: boolean): string | undefined {
  if (!raw) return undefined;
  const s = raw.trim();
  if (/^\d{4}$/.test(s)) return end ? `${s}-12-31` : `${s}-01-01`;
  if (/^\d{4}-\d{1,2}$/.test(s)) {
    const [y, mo] = s.split("-").map(Number);
    return end ? `${y}-${pad(mo)}-31` : `${y}-${pad(mo)}-01`;
  }
  return parseDate(s)?.date;
}

/** Absolute difference in days between two ISO dates. */
export function daysBetween(a: string, b: string): number {
  return Math.abs(Date.parse(a) - Date.parse(b)) / 86_400_000;
}
