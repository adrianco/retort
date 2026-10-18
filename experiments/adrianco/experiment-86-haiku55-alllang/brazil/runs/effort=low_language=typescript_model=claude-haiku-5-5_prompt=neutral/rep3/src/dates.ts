/*
 * Context: Date parsing for the mixed-format datasets. Supports ISO ("2023-09-24",
 * "2012-05-19 18:30:00"), Brazilian ("29/03/2003") and dotted/slashed variants.
 * Dates are returned as "YYYY-MM-DD" strings so no timezone conversion can shift them.
 * Related: dataset.ts (row ingestion).
 */

const ISO = /^(\d{4})-(\d{2})-(\d{2})/;
const BR = /^(\d{1,2})\/(\d{1,2})\/(\d{4})/;

/** Parse a date string in any supported format. Returns "YYYY-MM-DD" or null when unparseable. */
export function parseDate(raw: string | undefined | null): string | null {
  if (!raw) return null;
  const value = raw.trim();
  const iso = ISO.exec(value);
  if (iso) return validate(iso[1], iso[2], iso[3]);
  const br = BR.exec(value);
  if (br) return validate(br[3], br[2], br[1]);
  return null;
}

function validate(year: string, month: string, day: string): string | null {
  const y = Number(year);
  const m = Number(month);
  const d = Number(day);
  const probe = new Date(Date.UTC(y, m - 1, d));
  if (probe.getUTCFullYear() !== y || probe.getUTCMonth() !== m - 1 || probe.getUTCDate() !== d) {
    return null;
  }
  return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
}
