/**
 * Date parsing across the three formats present in the datasets:
 *
 *   ISO date          2023-09-24                 (BR-Football-Dataset)
 *   ISO date + time   2012-05-19 18:30:00        (Brasileirao / Cup / Libertadores)
 *   Brazilian         29/03/2003                 (novo_campeonato_brasileiro)
 *
 * Everything is normalised to a `YYYY-MM-DD` string plus an optional `HH:MM`
 * kick-off time. We deliberately avoid `Date` for storage: these are calendar
 * dates in Brazil, and round-tripping them through a UTC `Date` shifts matches
 * across midnight.
 */

export interface ParsedDate {
  /** `YYYY-MM-DD`. */
  date: string;
  /** `HH:MM`, when the source carried a kick-off time. */
  time?: string;
}

const ISO = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::\d{2})?)?/;
const BR = /^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:[T ](\d{2}):(\d{2}))?/;

/** Parse any supported representation, or return undefined for blank/NA values. */
export function parseDate(raw: string | undefined): ParsedDate | undefined {
  if (!raw) return undefined;
  const value = raw.trim();
  if (value === '' || value.toUpperCase() === 'NA' || value.toLowerCase() === 'nan') {
    return undefined;
  }

  const iso = ISO.exec(value);
  if (iso) return build(iso[1]!, iso[2]!, iso[3]!, iso[4], iso[5]);

  const br = BR.exec(value);
  if (br) return build(br[3]!, br[2]!, br[1]!, br[4], br[5]);

  return undefined;
}

function build(
  year: string,
  month: string,
  day: string,
  hour?: string,
  minute?: string,
): ParsedDate | undefined {
  const y = Number(year);
  const m = Number(month);
  const d = Number(day);
  if (!isValidCalendarDate(y, m, d)) return undefined;

  const result: ParsedDate = {
    date: `${pad(y, 4)}-${pad(m, 2)}-${pad(d, 2)}`,
  };
  if (hour !== undefined && minute !== undefined) result.time = `${hour}:${minute}`;
  return result;
}

function isValidCalendarDate(y: number, m: number, d: number): boolean {
  if (!Number.isInteger(y) || !Number.isInteger(m) || !Number.isInteger(d)) return false;
  if (m < 1 || m > 12 || d < 1) return false;
  return d <= daysInMonth(y, m);
}

function daysInMonth(year: number, month: number): number {
  const lengths = [31, isLeapYear(year) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return lengths[month - 1]!;
}

function isLeapYear(year: number): boolean {
  return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
}

function pad(value: number, width: number): string {
  return String(value).padStart(width, '0');
}

/**
 * Accept a user-supplied date bound in either ISO or Brazilian form.
 * Throws on unparseable input so tool callers get an explicit error rather than
 * a silently ignored filter.
 */
export function parseDateBound(raw: string, label: string): string {
  const parsed = parseDate(raw);
  if (!parsed) {
    throw new Error(
      `Could not parse ${label} "${raw}". Use YYYY-MM-DD (e.g. 2019-11-24) or DD/MM/YYYY.`,
    );
  }
  return parsed.date;
}

/** Whole days between two `YYYY-MM-DD` strings (absolute value). */
export function daysBetween(a: string, b: string): number {
  const msPerDay = 86_400_000;
  return Math.round(Math.abs(Date.parse(`${a}T00:00:00Z`) - Date.parse(`${b}T00:00:00Z`)) / msPerDay);
}
