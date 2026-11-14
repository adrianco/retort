/**
 * Text, team-name, date and number normalisation shared by the loaders and queries.
 *
 * The datasets name the same club many ways ("Palmeiras-SP", "Palmeiras",
 * "Atlético - MG", "Atletico Mineiro", "C. R. B. - AL"). `teamKey` maps every
 * variant to one stable, accent-free key.
 */

export const STATES = new Set([
  'ac', 'al', 'ap', 'am', 'ba', 'ce', 'df', 'es', 'go', 'ma', 'mt', 'ms', 'mg', 'pa',
  'pb', 'pr', 'pe', 'pi', 'rj', 'rn', 'rs', 'ro', 'rr', 'sc', 'sp', 'se', 'to',
]);

/** Lower-case, strip accents and punctuation, collapse whitespace. */
export function clean(s: string): string {
  const t = s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/\(antigo[^)]*\)/gi, ' ') // long parentheticals: "(antigo Esporte Clube Barreira)"
    .replace(/[.'’]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
  // Re-join spelled-out acronyms: "c r b" -> "crb"
  const out: string[] = [];
  let acc = '';
  for (const tok of t.split(' ')) {
    if (tok.length === 1 && /[a-z]/.test(tok)) {
      acc += tok;
    } else {
      if (acc) out.push(acc);
      acc = '';
      out.push(tok);
    }
  }
  if (acc) out.push(acc);
  return out.join(' ');
}

/** Full-name / nickname aliases -> canonical key. Applied to the cleaned name. */
const ALIASES: Record<string, string> = {
  'atletico mineiro': 'atletico mg',
  'atletico goianiense': 'atletico go',
  'atletico paranaense': 'athletico pr',
  'athletico paranaense': 'athletico pr',
  'atletico pr': 'athletico pr',
  athletico: 'athletico pr',
  'america mineiro': 'america mg',
  'america minas gerais': 'america mg',
  'america fc minas gerais': 'america mg',
  'america natal': 'america rn',
  'america de natal': 'america rn',
  'vasco da gama': 'vasco',
  'red bull bragantino': 'bragantino',
  'rb bragantino': 'bragantino',
  'sport recife': 'sport',
  'sport club do recife': 'sport',
  'sport club corinthians paulista': 'corinthians',
  'cs alagoano': 'csa',
  'clube do remo': 'remo',
  'ceara sporting club': 'ceara',
  'gremio foot ball porto alegrense': 'gremio',
  'sociedade esportiva palmeiras': 'palmeiras',
  'clube de regatas do flamengo': 'flamengo',
  'boavista sport club': 'boavista',
  'brasil de pelotas': 'brasil rs',
  'america fc natal': 'america rn',
  'nautico capibaribe': 'nautico',
  'campinense clube': 'campinense',
  'portuguesa desportos': 'portuguesa',
  'gremio barueri': 'barueri',
  'operario ferroviario esporte c': 'operario',
  'operario ferroviario': 'operario',
  'operario pr': 'operario',
  fla: 'flamengo',
  flu: 'fluminense',
  inter: 'internacional',
  galo: 'atletico mg',
};

/**
 * Base names shared by several clubs. The value is the state of the club that
 * owns the bare name (if any); other clubs keep their state in the key.
 */
const AMBIGUOUS: Record<string, string | null> = {
  atletico: null,
  america: null,
  botafogo: 'rj',
  bragantino: 'sp',
  boavista: 'rj',
  guarani: 'sp',
  internacional: 'rs',
  fluminense: 'rj',
  juventude: 'rs',
  brasil: null,
  comercial: null,
  nacional: null,
};

const ORG_TOKENS = new Set(['ec', 'fc', 'sc', 'ac', 'ca', 'ad', 'ae', 'ge']);
const ORG_PHRASES = /\b(futebol clube|esporte clube|sport club|sporting club|football club)\b/g;

/** Canonical key for any team-name variant. */
export function teamKey(raw: string): string {
  let c = clean(raw);
  if (ALIASES[c]) return ALIASES[c];
  let toks = c.split(' ').filter(Boolean);
  let state: string | undefined;
  if (toks.length > 1 && STATES.has(toks[toks.length - 1])) state = toks.pop();
  let base = toks.join(' ');
  const withState = () => (state ? `${base} ${state}` : base);
  if (ALIASES[withState()]) return ALIASES[withState()];
  if (ALIASES[base] && !(base in AMBIGUOUS)) return ALIASES[base];

  const stripped = base.replace(ORG_PHRASES, ' ').replace(/\s+/g, ' ').trim();
  if (stripped) base = stripped;
  toks = base.split(' ');
  while (toks.length > 1 && ORG_TOKENS.has(toks[0])) toks.shift();
  while (toks.length > 1 && ORG_TOKENS.has(toks[toks.length - 1])) toks.pop();
  base = toks.join(' ');
  if (ALIASES[withState()]) return ALIASES[withState()];
  if (ALIASES[base] && !state) return ALIASES[base];

  if (base in AMBIGUOUS) {
    const owner = AMBIGUOUS[base];
    if (!state || state === owner) return base;
    return `${base} ${state}`;
  }
  return base || c;
}

const DISPLAY: Record<string, string> = {
  'atletico mg': 'Atlético-MG',
  'atletico go': 'Atlético-GO',
  'athletico pr': 'Athletico-PR',
  'america mg': 'América-MG',
  'america rn': 'América-RN',
  vasco: 'Vasco da Gama',
  'sao paulo': 'São Paulo',
  gremio: 'Grêmio',
  goias: 'Goiás',
  ceara: 'Ceará',
  avai: 'Avaí',
  vitoria: 'Vitória',
  nautico: 'Náutico',
  criciuma: 'Criciúma',
  parana: 'Paraná',
  cuiaba: 'Cuiabá',
  csa: 'CSA',
  crb: 'CRB',
  abc: 'ABC',
  asa: 'ASA',
  bragantino: 'Red Bull Bragantino',
  sport: 'Sport Recife',
};

/** A human-friendly label for a raw name, given its key. */
export function displayCandidate(raw: string, key: string): { name: string; score: number } {
  if (DISPLAY[key]) return { name: DISPLAY[key], score: 100 };
  let name = raw
    .replace(/\(antigo[^)]*\)/gi, ' ')
    .replace(/\s*-\s*[A-Z]{2}\s*$/, '')
    .replace(/\s+[A-Z]{2}\s*$/, (m) => (STATES.has(m.trim().toLowerCase()) ? '' : m))
    .replace(/\s+/g, ' ')
    .trim();
  const kt = key.split(' ');
  const st = kt[kt.length - 1];
  if (kt.length > 1 && STATES.has(st) && kt.slice(0, -1).join(' ') in AMBIGUOUS) {
    name = `${name}-${st.toUpperCase()}`;
  }
  let score = 0;
  if (/[^\x00-\x7f]/.test(name)) score += 2;
  if (name !== name.toUpperCase() && !name.includes('.')) score += 1;
  return { name: name || raw, score };
}

/** Parse "2023-09-24", "2012-05-19 18:30:00" or "29/03/2003" to ISO date (+ optional time). */
export function parseDate(s: string | undefined): { date: string | null; time: string | null } {
  if (!s) return { date: null, time: null };
  const t = s.trim();
  let m = t.match(/^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}:\d{2})(?::\d{2})?)?/);
  if (m) {
    return { date: `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`, time: m[4] ?? null };
  }
  m = t.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}:\d{2}))?/);
  if (m) {
    return { date: `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`, time: m[4] ?? null };
  }
  return { date: null, time: null };
}

/** Parse "2", "2.0" -> number; "NA", "-", "" -> null. */
export function parseNum(s: string | undefined): number | null {
  if (s === undefined) return null;
  const t = s.trim();
  if (t === '' || t === 'NA' || t === '-') return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

export type Competition =
  | 'Brasileirão Série A'
  | 'Série B'
  | 'Série C'
  | 'Copa do Brasil'
  | 'Copa Libertadores';

export const COMPETITIONS: Competition[] = [
  'Brasileirão Série A',
  'Série B',
  'Série C',
  'Copa do Brasil',
  'Copa Libertadores',
];

/** Map free-text competition names to a known competition (undefined if unrecognised). */
export function parseCompetition(s: string | undefined): Competition | undefined {
  if (!s) return undefined;
  const c = clean(s);
  if (!c) return undefined;
  if (c.includes('libertadores')) return 'Copa Libertadores';
  if (c.includes('copa do brasil') || c.includes('cup') || c === 'copa') return 'Copa do Brasil';
  if (/\bserie b\b/.test(c) || c === 'b') return 'Série B';
  if (/\bserie c\b/.test(c) || c === 'c') return 'Série C';
  if (c.includes('brasileir') || /\bserie a\b/.test(c) || c.includes('league') || c.includes('campeonato')) {
    return 'Brasileirão Série A';
  }
  return undefined;
}
