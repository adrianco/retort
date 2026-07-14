// Parse the several date formats found across the CSV sources into ISO YYYY-MM-DD.

export function parseDate(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const s = String(raw).trim();
  if (!s || s === "NA" || s === "-") return null;

  // 2023-09-24 or 2012-05-19 18:30:00 -> 2023-09-24
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;

  // 29/03/2003
  const br = s.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (br) return `${br[3]}-${br[2]}-${br[1]}`;

  return null;
}

export function parseSeason(raw: string | number | null | undefined): number | null {
  if (raw === null || raw === undefined) return null;
  const s = String(raw).trim();
  if (!s || s === "NA") return null;
  const n = parseInt(s, 10);
  return Number.isFinite(n) ? n : null;
}

export function parseGoal(raw: string | number | null | undefined): number | null {
  if (raw === null || raw === undefined) return null;
  const s = String(raw).trim();
  if (!s || s === "NA" || s === "-") return null;
  const n = parseFloat(s);
  return Number.isFinite(n) ? Math.round(n) : null;
}
