const STATE_SUFFIXES = new Set([
  'SP', 'RJ', 'MG', 'RS', 'PR', 'PE', 'BA', 'CE', 'SC', 'GO', 'PA', 'DF',
  'AM', 'MA', 'ES', 'MT', 'MS', 'AL', 'SE', 'PB', 'RN', 'TO', 'RO', 'AP',
  'RR', 'AC', 'PI',
]);

const COUNTRY_SUFFIXES = new Set([
  'BRA', 'ARG', 'URU', 'PAR', 'CHI', 'COL', 'EQU', 'BOL', 'PER', 'VEN',
  'MEX', 'USA', 'CRC', 'HON', 'JAM',
]);

function stripAccents(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function baseLower(s: string): string {
  return stripAccents(s).toLowerCase().replace(/\s+/g, ' ').trim();
}

// Canonical full-name aliases collapse to short canonical names.
// These map AFTER suffix extraction.
const ALIASES: Record<string, string> = {
  'sport club corinthians paulista': 'corinthians',
  'sociedade esportiva palmeiras': 'palmeiras',
  'clube de regatas do flamengo': 'flamengo-rj',
  'fluminense football club': 'fluminense-rj',
  'santos fc': 'santos',
  'santos futebol clube': 'santos',
  'sport club internacional': 'internacional',
  'sport club do recife': 'sport-pe',
  'fortaleza esporte clube': 'fortaleza-ce',
  'cuiaba esporte clube': 'cuiaba',
  'red bull bragantino': 'bragantino',
  'gremio foot-ball porto alegrense': 'gremio-rs',
  'boavista sport club antigo esporte clube barreira': 'boavista-rj',
  'atletico mineiro': 'atletico-mg',
  'clube atletico mineiro': 'atletico-mg',
  'atletico paranaense': 'athletico-pr',
  'athletico paranaense': 'athletico-pr',
  'club athletico paranaense': 'athletico-pr',
  'atletico goianiense': 'atletico-go',
  'america mineiro': 'america-mg',
};

export interface CanonicalName {
  canonical: string;
  base: string; // without trailing region/country suffix
  suffix?: string; // uppercase state or country code if any
}

export function canonicalize(raw: string | undefined | null): CanonicalName {
  if (!raw) return { canonical: '', base: '' };
  let name = String(raw).trim();

  // Drop trailing parenthetical country code: "Nacional (URU)"
  let suffix: string | undefined;
  const paren = name.match(/^(.*?)\s*\(([A-Z]{2,4})\)\s*$/);
  if (paren) {
    name = paren[1];
    if (COUNTRY_SUFFIXES.has(paren[2]) || STATE_SUFFIXES.has(paren[2])) {
      suffix = paren[2];
    }
  }

  // Trailing " - XX" or "-XX"
  const dash = name.match(/^(.*?)\s*-\s*([A-Z]{2,4})\s*$/);
  if (dash && (STATE_SUFFIXES.has(dash[2]) || COUNTRY_SUFFIXES.has(dash[2]))) {
    suffix = suffix ?? dash[2];
    name = dash[1];
  }

  const base = baseLower(name);
  const aliasKey = base;
  if (ALIASES[aliasKey]) {
    const aliased = ALIASES[aliasKey];
    // Aliases already include their suffix if any
    const m = aliased.match(/^(.+?)-([a-z]{2,4})$/);
    if (m) return { canonical: aliased, base: m[1], suffix: m[2].toUpperCase() };
    return { canonical: aliased, base: aliased, suffix };
  }

  const canonical = suffix ? `${base}-${suffix.toLowerCase()}` : base;
  return { canonical, base, suffix };
}

export function normalizeTeamName(raw: string | undefined | null): string {
  return canonicalize(raw).canonical;
}

// Whether a stored team's canonical matches a user-provided query canonical.
// Lenient: if the query has no suffix, also match canonical names that share the base.
export function teamMatches(storedCanonical: string, queryRaw: string): boolean {
  const q = canonicalize(queryRaw);
  if (!q.canonical) return false;
  if (storedCanonical === q.canonical) return true;
  if (!q.suffix) {
    // Match stored "<base>-XX" if user didn't disambiguate.
    if (storedCanonical === q.base) return true;
    if (storedCanonical.startsWith(q.base + '-')) return true;
  }
  return false;
}

export function parseDate(raw: string | undefined | null): {
  date: string;
  datetime?: string;
} {
  if (!raw) return { date: '' };
  const s = String(raw).trim();
  const br = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?/);
  if (br) {
    const [, dd, mm, yyyy, hh, mi] = br;
    const date = `${yyyy}-${mm.padStart(2, '0')}-${dd.padStart(2, '0')}`;
    if (hh != null) return { date, datetime: `${date} ${hh.padStart(2, '0')}:${mi}:00` };
    return { date };
  }
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if (iso) {
    const [, y, mo, d, hh, mi, ss] = iso;
    const date = `${y}-${mo}-${d}`;
    if (hh != null) return { date, datetime: `${date} ${hh}:${mi}:${ss ?? '00'}` };
    return { date };
  }
  return { date: s };
}

export function parseNumber(raw: string | undefined | null): number {
  if (raw == null || raw === '') return 0;
  const n = Number(String(raw).replace(/"/g, '').trim());
  return Number.isFinite(n) ? n : 0;
}

export function parseOptionalNumber(
  raw: string | undefined | null
): number | undefined {
  if (raw == null || raw === '') return undefined;
  const n = Number(String(raw).replace(/"/g, '').trim());
  return Number.isFinite(n) ? n : undefined;
}

export function extractStateSuffix(raw: string | undefined | null): string | undefined {
  if (!raw) return undefined;
  const m = String(raw).match(/-([A-Z]{2})\s*$/);
  if (m && STATE_SUFFIXES.has(m[1])) return m[1];
  return undefined;
}
