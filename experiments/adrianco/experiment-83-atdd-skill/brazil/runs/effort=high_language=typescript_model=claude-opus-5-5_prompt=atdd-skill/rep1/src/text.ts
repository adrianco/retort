/**
 * Text helpers shared across the system: accent-insensitive folding of
 * Portuguese/Spanish names, and number formatting for answers.
 */

/** Lower-case, strip accents/cedillas, collapse whitespace: "São Paulo" → "sao paulo". */
export function fold(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

export function hasAccents(text: string): boolean {
  return text.normalize('NFD') !== text;
}

export function tokens(text: string): string[] {
  return fold(text)
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

export function round(value: number, places = 1): number {
  const factor = 10 ** places;
  return Math.round(value * factor) / factor;
}

export function rate(part: number, whole: number): number {
  return whole === 0 ? 0 : round((part / whole) * 100, 1);
}

export function pct(value: number): string {
  return `${value.toFixed(1)}%`;
}
