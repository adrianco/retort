/** Text helpers for comparing Brazilian Portuguese names regardless of accents, case and punctuation. */

export function stripAccents(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

/** "São Paulo F.C." → "sao paulo f c" */
export function fold(text: string): string {
  return stripAccents(text).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

export function countAccented(text: string): number {
  return text.normalize('NFD').replace(/[^̀-ͯ]/g, '').length;
}

export function round(value: number, places = 1): number {
  const factor = 10 ** places;
  return Math.round(value * factor) / factor;
}

export function percentage(part: number, whole: number): number {
  return whole === 0 ? 0 : round((part / whole) * 100, 1);
}
