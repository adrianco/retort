const ISO_DATETIME = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/;
const BR_DATE = /^(\d{2})\/(\d{2})\/(\d{4})$/;

export function parseFlexibleDate(raw: string): Date {
  const value = raw.trim();

  const iso = value.match(ISO_DATETIME);
  if (iso) {
    const [, year, month, day, hour = "0", minute = "0", second = "0"] = iso;
    return new Date(Date.UTC(
      Number(year), Number(month) - 1, Number(day),
      Number(hour), Number(minute), Number(second),
    ));
  }

  const br = value.match(BR_DATE);
  if (br) {
    const [, day, month, year] = br;
    return new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  }

  throw new Error(`Unparseable date: "${raw}"`);
}

export function formatISODate(date: Date): string {
  const year = String(date.getUTCFullYear()).padStart(4, "0");
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function isWithinDateRange(date: Date, start?: string, end?: string): boolean {
  const value = formatISODate(date);
  if (start && value < start) return false;
  if (end && value > end) return false;
  return true;
}
