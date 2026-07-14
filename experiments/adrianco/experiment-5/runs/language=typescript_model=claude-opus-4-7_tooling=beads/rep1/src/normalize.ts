const BR_STATES = new Set([
  'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB',
  'PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO',
]);
const STATE_SUFFIX = /\s*[-–]\s*([A-Z]{2,3})$/;
const SPACE_STATE_SUFFIX = /\s+([A-Z]{2,3})$/;
const PAREN_COUNTRY = /\s*\(([A-Z]{2,4})\)$/;
const NON_ALNUM = /[^a-z0-9]+/g;

// Map normalized form → canonical key
// For ambiguous short names (Atlético, América, Internacional, etc.), keep the state.
const TEAM_ALIASES: Record<string, string> = {
  // Disambiguated
  'atletico mg': 'atletico mineiro',
  'atletico mineiro': 'atletico mineiro',
  'atletico go': 'atletico goianiense',
  'atletico goianiense': 'atletico goianiense',
  'atletico pr': 'athletico paranaense',
  'atletico paranaense': 'athletico paranaense',
  'athletico pr': 'athletico paranaense',
  'athletico paranaense': 'athletico paranaense',
  'america mg': 'america mineiro',
  'america mineiro': 'america mineiro',
  'america rn': 'america rn',
  // Common single-state clubs
  'sao paulo': 'sao paulo',
  'sao paulo fc': 'sao paulo',
  'gremio': 'gremio',
  'corinthians': 'corinthians',
  'sport club corinthians paulista': 'corinthians',
  'sc corinthians paulista': 'corinthians',
  'flamengo': 'flamengo',
  'palmeiras': 'palmeiras',
  'santos': 'santos',
  'fluminense': 'fluminense',
  'botafogo': 'botafogo',
  'vasco': 'vasco',
  'vasco da gama': 'vasco',
  'cruzeiro': 'cruzeiro',
  'internacional': 'internacional',
  'inter': 'internacional',
  'fortaleza': 'fortaleza',
  'fortaleza esporte clube': 'fortaleza',
  'ceara': 'ceara',
  'ceara sporting club': 'ceara',
  'bahia': 'bahia',
  'goias': 'goias',
  'sport': 'sport recife',
  'sport recife': 'sport recife',
  'chapecoense': 'chapecoense',
  'juventude': 'juventude',
  'cuiaba': 'cuiaba',
  'rb bragantino': 'red bull bragantino',
  'red bull bragantino': 'red bull bragantino',
  'bragantino': 'red bull bragantino',
};

// Single-state-only ambiguous prefixes: don't strip state for these.
const AMBIGUOUS_BASE = new Set([
  'atletico', 'athletico', 'america',
]);

function stripAccents(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function applyAlias(s: string): string {
  if (TEAM_ALIASES[s]) return TEAM_ALIASES[s];
  return s;
}

export function normalizeTeamName(raw: string | undefined | null): string {
  if (!raw) return '';
  let s = String(raw).trim();
  s = s.replace(PAREN_COUNTRY, ''); // strip country code in parens like (URU)

  // Detect (and remember) trailing state code in either "-XX" or " XX" form.
  let state: string | undefined;
  const dashMatch = s.match(STATE_SUFFIX);
  if (dashMatch && BR_STATES.has(dashMatch[1])) {
    state = dashMatch[1];
    s = s.slice(0, -dashMatch[0].length);
  } else {
    const spaceMatch = s.match(SPACE_STATE_SUFFIX);
    if (spaceMatch && BR_STATES.has(spaceMatch[1])) {
      state = spaceMatch[1];
      s = s.slice(0, -spaceMatch[0].length);
    }
  }

  s = stripAccents(s).toLowerCase();
  s = s.replace(NON_ALNUM, ' ').replace(/\s+/g, ' ').trim();

  // If the unsuffixed base is ambiguous (multiple states share it), include the state.
  if (state && AMBIGUOUS_BASE.has(s)) {
    const withState = `${s} ${state.toLowerCase()}`;
    return applyAlias(withState);
  }

  // Try aliasing with or without the state.
  if (state) {
    const withState = `${s} ${state.toLowerCase()}`;
    if (TEAM_ALIASES[withState]) return TEAM_ALIASES[withState];
  }
  return applyAlias(s);
}

export function teamMatches(target: string, name: string): boolean {
  const a = normalizeTeamName(target);
  const b = normalizeTeamName(name);
  if (!a || !b) return false;
  if (a === b) return true;
  return a.length >= 3 && (b.includes(a) || a.includes(b));
}

export function parseDate(raw: string | undefined | null): string {
  if (!raw) return '';
  const s = String(raw).trim();
  if (!s) return '';
  // Brazilian DD/MM/YYYY
  const brMatch = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (brMatch) {
    const [, d, m, y] = brMatch;
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
  }
  // ISO with time: 2012-05-19 18:30:00 or 2012-05-19T18:30:00
  const isoMatch = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) {
    return `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`;
  }
  return s;
}

export function parseSeason(raw: string | number | undefined | null, date?: string): number {
  if (raw !== undefined && raw !== null && raw !== '') {
    const n = Number(raw);
    if (!Number.isNaN(n) && n > 1900) return n;
  }
  if (date) {
    const m = date.match(/^(\d{4})/);
    if (m) return Number(m[1]);
  }
  return 0;
}

export function parseNumber(raw: unknown): number {
  if (raw === undefined || raw === null || raw === '') return 0;
  const n = Number(raw);
  return Number.isFinite(n) ? n : 0;
}

export function parseOptionalNumber(raw: unknown): number | undefined {
  if (raw === undefined || raw === null || raw === '') return undefined;
  const n = Number(raw);
  return Number.isFinite(n) ? n : undefined;
}
