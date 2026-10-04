/** Parses the date formats found in the datasets into ISO yyyy-mm-dd (plus time when present). */

export interface ParsedDate {
  date: string;
  time?: string;
}

export function parseDate(raw: string | undefined): ParsedDate | null {
  if (!raw) return null;
  const text = raw.trim();
  let m = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2})(?::\d{2})?)?$/.exec(text);
  if (m) return { date: `${m[1]}-${m[2]}-${m[3]}`, time: m[4] };
  m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{2}:\d{2}))?$/.exec(text);
  if (m) return { date: `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`, time: m[4] };
  return null;
}

/** Accepts ISO or Brazilian dd/mm/yyyy input from a user and returns ISO, or throws. */
export function normaliseDateInput(raw: string): string {
  const parsed = parseDate(raw) ?? (/^\d{4}$/.test(raw.trim()) ? { date: `${raw.trim()}-01-01` } : null);
  if (!parsed) throw new Error(`"${raw}" is not a date I understand; use YYYY-MM-DD or DD/MM/YYYY`);
  return parsed.date;
}

export function daysBetween(a: string, b: string): number {
  return Math.abs(Date.parse(a) - Date.parse(b)) / 86_400_000;
}
