/**
 * Brazilian team / player name normalization helpers.
 *
 * The provided datasets use a mix of conventions:
 *   - "Palmeiras-SP", "Palmeiras - SP", "Palmeiras (SP)" — with state suffix
 *   - "Sao Paulo" vs "São Paulo" — with/without diacritics
 *   - "Athletico-PR" / "Atlético Paranaense" — abbreviations vs long form
 *
 * We aim for a consistent "key" string so that the same team always matches.
 */

const DIACRITICS = /[̀-ͯ]/g;

export function stripAccents(s: string): string {
  return s.normalize('NFD').replace(DIACRITICS, '');
}

/** Common state-code suffixes used in the datasets. */
const STATE_CODES = new Set([
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
  'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
  'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
  // Country codes used in Libertadores data
  'URU', 'ARG', 'CHI', 'COL', 'EQU', 'PAR', 'PER', 'VEN', 'BOL', 'MEX',
]);

/**
 * Strip noisy descriptors and state/country suffixes so different
 * spellings of the same team converge to one key.
 */
export function normalizeTeam(rawInput: string | undefined | null): string {
  if (!rawInput) return '';
  let s = String(rawInput).trim();

  // Drop parenthetical content e.g. "Nacional (URU)" -> "Nacional"
  s = s.replace(/\s*\([^)]*\)\s*/g, ' ').trim();

  // Drop common state suffix patterns: "Palmeiras-SP", "Palmeiras - SP", "Palmeiras /SP"
  // Iterate to handle multiple suffixes ("Boavista - RJ" then strip residual " - ")
  for (let i = 0; i < 3; i++) {
    const m = s.match(/^(.*?)[\s,/-]+([A-Z]{2,3})\s*$/);
    if (m && STATE_CODES.has(m[2])) {
      s = m[1].trim();
    } else {
      break;
    }
  }

  // Strip common descriptors that vary between datasets
  s = s.replace(/^Sport Club\s+/i, '');
  s = s.replace(/^Esporte Clube\s+/i, '');
  s = s.replace(/\s+Esporte Clube$/i, '');
  s = s.replace(/\s+Futebol Clube$/i, '');
  s = s.replace(/\s+Football Club$/i, '');
  s = s.replace(/\s+FC$/i, '');
  s = s.replace(/^FC\s+/i, '');

  // Lower-case and strip accents for keying
  const key = stripAccents(s.toLowerCase())
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');

  return key;
}

/**
 * Soft contains: does the haystack key contain all words of the needle key?
 * Used to match "Flamengo" against "flamengo rj" or "Atletico" against
 * "atletico mineiro".
 */
export function keyMatches(haystackKey: string, needleKey: string): boolean {
  if (!haystackKey || !needleKey) return false;
  if (haystackKey === needleKey) return true;
  const needleWords = needleKey.split(' ').filter(Boolean);
  if (needleWords.length === 0) return false;
  return needleWords.every((w) => haystackKey.split(' ').includes(w));
}

/** Returns the display version of the team name (raw, trimmed). */
export function displayTeam(raw: string): string {
  return String(raw ?? '').trim();
}

/**
 * Parse dates encountered in the datasets:
 *   - "2023-09-24"
 *   - "2012-05-19 18:30:00"
 *   - "29/03/2003"
 * Returns ISO date (YYYY-MM-DD) and optional time string.
 */
export function parseDate(raw: string | undefined | null): {
  date: string;
  time?: string;
} {
  if (!raw) return { date: '' };
  const s = String(raw).trim();
  if (!s) return { date: '' };

  // ISO with optional time: 2012-05-19 18:30:00 OR 2012-05-19T18:30:00
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2}(?::\d{2})?))?/);
  if (m) {
    return { date: `${m[1]}-${m[2]}-${m[3]}`, time: m[4] };
  }

  // Brazilian DD/MM/YYYY
  m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (m) {
    return { date: `${m[3]}-${m[2]}-${m[1]}` };
  }

  return { date: s };
}
