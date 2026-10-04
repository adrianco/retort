/**
 * Team identity across datasets.
 *
 * The datasets name the same club in many ways: "Palmeiras-SP", "Palmeiras",
 * "Palmeiras - SP", "Sociedade Esportiva Palmeiras"; "Atletico-MG",
 * "Atlético Mineiro", "Atletico Mineiro"; "Nacional (URU)", "Nacional-URU".
 *
 * A name is parsed into a folded base name plus an optional region (Brazilian
 * state or 3-letter country code). Teams without a region take the region
 * they most often appear with in the match data (so "Botafogo" is
 * Botafogo-RJ, while "Botafogo-PB" stays distinct). The pair is the team's key.
 */
import { fold, hasAccents } from '../text.js';

export const BRAZILIAN_STATES = new Set([
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
]);

const COUNTRIES = new Set(['URU', 'PAR', 'EQU', 'ECU', 'PER', 'ARG', 'CHI', 'BOL', 'COL', 'VEN', 'MEX', 'BRA']);

const STATE_NAMES: Record<string, string> = {
  acre: 'AC', alagoas: 'AL', amapa: 'AP', amazonas: 'AM', bahia: 'BA', ceara: 'CE', 'distrito federal': 'DF',
  'espirito santo': 'ES', goias: 'GO', maranhao: 'MA', 'mato grosso': 'MT', 'mato grosso do sul': 'MS',
  'minas gerais': 'MG', para: 'PA', paraiba: 'PB', parana: 'PR', pernambuco: 'PE', piaui: 'PI',
  'rio de janeiro': 'RJ', 'rio grande do norte': 'RN', 'rio grande do sul': 'RS', rondonia: 'RO', roraima: 'RR',
  'santa catarina': 'SC', 'sao paulo': 'SP', sergipe: 'SE', tocantins: 'TO',
};

/** Full or alternative names (folded, region removed) → canonical base and region. */
const ALIASES: Record<string, { base: string; region?: string }> = {
  'atletico mineiro': { base: 'atletico', region: 'MG' },
  'clube atletico mineiro': { base: 'atletico', region: 'MG' },
  'atletico goianiense': { base: 'atletico', region: 'GO' },
  'atletico paranaense': { base: 'athletico', region: 'PR' },
  'athletico paranaense': { base: 'athletico', region: 'PR' },
  'club athletico paranaense': { base: 'athletico', region: 'PR' },
  'america mineiro': { base: 'america', region: 'MG' },
  'america natal': { base: 'america', region: 'RN' },
  'america fc natal': { base: 'america', region: 'RN' },
  'vasco da gama': { base: 'vasco', region: 'RJ' },
  'club de regatas vasco da gama': { base: 'vasco', region: 'RJ' },
  'cr vasco da gama': { base: 'vasco', region: 'RJ' },
  'clube de regatas do flamengo': { base: 'flamengo', region: 'RJ' },
  'cr flamengo': { base: 'flamengo', region: 'RJ' },
  'sport recife': { base: 'sport', region: 'PE' },
  'sport club do recife': { base: 'sport', region: 'PE' },
  'red bull bragantino': { base: 'bragantino', region: 'SP' },
  'rb bragantino': { base: 'bragantino', region: 'SP' },
  'nautico capibaribe': { base: 'nautico', region: 'PE' },
  'clube nautico capibaribe': { base: 'nautico', region: 'PE' },
  'gremio foot ball porto alegrense': { base: 'gremio', region: 'RS' },
  'sport club internacional': { base: 'internacional', region: 'RS' },
  'sport club corinthians paulista': { base: 'corinthians', region: 'SP' },
  'corinthians paulista': { base: 'corinthians', region: 'SP' },
  'sociedade esportiva palmeiras': { base: 'palmeiras', region: 'SP' },
  'botafogo de futebol e regatas': { base: 'botafogo', region: 'RJ' },
  'portuguesa desportos': { base: 'portuguesa', region: 'SP' },
  'associacao portuguesa de desportos': { base: 'portuguesa', region: 'SP' },
  'clube do remo': { base: 'remo', region: 'PA' },
  'gremio novorizontino': { base: 'novorizontino', region: 'SP' },
  'coritiba foot ball club': { base: 'coritiba', region: 'PR' },
  'ec vitoria': { base: 'vitoria', region: 'BA' },
  'esporte clube vitoria': { base: 'vitoria', region: 'BA' },
  'ec bahia': { base: 'bahia', region: 'BA' },
  'esporte clube bahia': { base: 'bahia', region: 'BA' },
  'ec juventude': { base: 'juventude', region: 'RS' },
  'ceara sporting club': { base: 'ceara', region: 'CE' },
  'america fc': { base: 'america' },
  'esporte clube juventude': { base: 'juventude', region: 'RS' },
};

const PREFIXES = ['sociedade esportiva ', 'esporte clube ', 'sport club ', 'clube de regatas ', 'clube ', 'ec ', 'fc ', 'sc ', 'ad ', 'se ', 'ge ', 'cs ', 'ce '];
const SUFFIXES = [' futebol clube', ' football club', ' foot ball club', ' esporte clube', ' sporting club', ' sport club', ' futebol', ' clube', ' fc', ' ec', ' sc'];

/** Display names for well-known clubs, keyed by team key. */
const DISPLAY: Record<string, string> = {
  'atletico|MG': 'Atlético-MG', 'atletico|GO': 'Atlético-GO', 'athletico|PR': 'Athletico-PR',
  'america|MG': 'América-MG', 'america|RN': 'América-RN', 'botafogo|RJ': 'Botafogo-RJ', 'botafogo|SP': 'Botafogo-SP',
  'botafogo|PB': 'Botafogo-PB', 'sao paulo|SP': 'São Paulo', 'gremio|RS': 'Grêmio', 'avai|SC': 'Avaí',
  'ceara|CE': 'Ceará', 'goias|GO': 'Goiás', 'criciuma|SC': 'Criciúma', 'vitoria|BA': 'Vitória', 'nautico|PE': 'Náutico',
  'parana|PR': 'Paraná', 'vasco|RJ': 'Vasco', 'sport|PE': 'Sport', 'bragantino|SP': 'Bragantino', 'cuiaba|MT': 'Cuiabá',
  'csa|AL': 'CSA', 'crb|AL': 'CRB', 'abc|RN': 'ABC', 'sao caetano|SP': 'São Caetano', 'santo andre|SP': 'Santo André',
  'flamengo|RJ': 'Flamengo', 'fluminense|RJ': 'Fluminense', 'palmeiras|SP': 'Palmeiras', 'corinthians|SP': 'Corinthians',
  'santos|SP': 'Santos', 'internacional|RS': 'Internacional', 'cruzeiro|MG': 'Cruzeiro', 'bahia|BA': 'Bahia',
  'fortaleza|CE': 'Fortaleza', 'coritiba|PR': 'Coritiba', 'chapecoense|SC': 'Chapecoense', 'figueirense|SC': 'Figueirense',
  'joinville|SC': 'Joinville', 'juventude|RS': 'Juventude', 'ponte preta|SP': 'Ponte Preta', 'portuguesa|SP': 'Portuguesa',
  'santa cruz|PE': 'Santa Cruz', 'guarani|SP': 'Guarani', 'paysandu|PA': 'Paysandu', 'remo|PA': 'Remo',
  'gremio prudente|SP': 'Grêmio Prudente',
};

/** Region used when the data never gives one for a well-known club. */
const DEFAULT_REGION: Record<string, string> = Object.fromEntries(
  Object.keys(DISPLAY)
    .map((key) => key.split('|'))
    .filter(([, region]) => region)
    .reverse() // earlier entries win: atletico → MG, america → MG, botafogo → RJ
    .map(([base, region]) => [base, region]),
);

export interface ParsedTeamName {
  raw: string;
  base: string;
  region?: string;
}

function stripAffixes(name: string): string {
  let result = name;
  let changed = true;
  while (changed) {
    changed = false;
    for (const prefix of PREFIXES) {
      if (result.startsWith(prefix) && result.length > prefix.length + 2) {
        result = result.slice(prefix.length);
        changed = true;
      }
    }
    for (const suffix of SUFFIXES) {
      if (result.endsWith(suffix) && result.length > suffix.length + 2) {
        result = result.slice(0, -suffix.length);
        changed = true;
      }
    }
  }
  return result;
}

/**
 * Parse a team name. `lenient` also strips club affixes ("FC", "Esporte
 * Clube"…) — right for match data and user queries, but too loose for the
 * FIFA club list, where "Boavista FC" is the Portuguese club, not Boavista-RJ.
 */
export function parseTeamName(raw: string, lenient = true): ParsedTeamName {
  let name = raw.trim();
  let region: string | undefined;

  // Parenthetical: "Nacional (URU)", "América FC (Minas Gerais)", "Boavista (antigo ...)"
  const paren = /\s*\(([^)]*)\)\s*/.exec(name);
  if (paren) {
    const inside = paren[1].trim();
    const upper = inside.toUpperCase();
    if (COUNTRIES.has(upper) || BRAZILIAN_STATES.has(upper)) region = upper;
    else if (STATE_NAMES[fold(inside)]) region = STATE_NAMES[fold(inside)];
    name = (name.slice(0, paren.index) + ' ' + name.slice(paren.index + paren[0].length)).trim();
  }

  // Dash suffix: "Palmeiras-SP", "América - MG", "Barcelona-EQU", "Csa-AL"
  const dash = /\s*-\s*([A-Za-z]{2,3})$/.exec(name);
  if (dash && !region) {
    const upper = dash[1].toUpperCase();
    if (BRAZILIAN_STATES.has(upper) || COUNTRIES.has(upper)) {
      region = upper;
      name = name.slice(0, dash.index).trim();
    }
  }

  // Space suffix written in capitals: "Botafogo RJ", "America MG"
  const spaced = /\s([A-Z]{2})$/.exec(name);
  if (spaced && !region && BRAZILIAN_STATES.has(spaced[1])) {
    region = spaced[1];
    name = name.slice(0, spaced.index).trim();
  }

  let base = fold(name)
    .replace(/\./g, '')
    .replace(/[-'’]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const lookup = (candidate: string) => ALIASES[candidate];
  let alias = lookup(base);
  if (!alias && lenient) {
    base = stripAffixes(base);
    alias = lookup(base);
  }
  if (alias) {
    base = alias.base;
    region = region ?? alias.region;
  }
  if (base === 'athletico') region = region ?? 'PR';
  if (base === 'atletico' && region === 'PR') base = 'athletico';
  return { raw, base, region };
}

export function teamKey(base: string, region: string | undefined): string {
  return `${base}|${region ?? ''}`;
}

/**
 * The teams known to the system, built from every team name seen in the match
 * data. Resolves any name variant to a team key and gives each key a display
 * name.
 */
export class TeamRegistry {
  private readonly regionCounts = new Map<string, Map<string, number>>();
  private readonly topFlightRegionCounts = new Map<string, Map<string, number>>();
  private readonly spellings = new Map<string, Map<string, number>>();
  private readonly regionsByBase = new Map<string, Set<string>>();
  private readonly known = new Map<string, number>();

  /**
   * Record a name seen in the match data (first pass, before resolving).
   * `topFlight` marks Brasileirão records: only clubs seen there are assumed
   * Brazilian when an international dataset names them without a state.
   */
  observe(parsed: ParsedTeamName, topFlight = false): void {
    if (!parsed.region) return;
    for (const table of topFlight ? [this.regionCounts, this.topFlightRegionCounts] : [this.regionCounts]) {
      const counts = table.get(parsed.base) ?? new Map<string, number>();
      counts.set(parsed.region, (counts.get(parsed.region) ?? 0) + 1);
      table.set(parsed.base, counts);
    }
  }

  /**
   * The key for a name, filling in the most usual region where none is given.
   * For international data (Libertadores, FIFA) only top-flight Brazilian clubs
   * get a state: a bare "River Plate" there is the Argentine club, not River Plate-SE.
   */
  keyFor(parsed: ParsedTeamName, international = false): string {
    return teamKey(parsed.base, parsed.region ?? this.usualRegion(parsed.base, international ? this.topFlightRegionCounts : this.regionCounts));
  }

  /** Register a team that appears in the match data (second pass). */
  register(parsed: ParsedTeamName, international = false): string {
    const key = this.keyFor(parsed, international);
    this.known.set(key, (this.known.get(key) ?? 0) + 1);
    const [base, region] = key.split('|');
    const regions = this.regionsByBase.get(base) ?? new Set<string>();
    regions.add(region);
    this.regionsByBase.set(base, regions);
    const spelling = cleanSpelling(parsed.raw);
    const counts = this.spellings.get(key) ?? new Map<string, number>();
    counts.set(spelling, (counts.get(spelling) ?? 0) + 1);
    this.spellings.set(key, counts);
    return key;
  }

  isKnown(key: string): boolean {
    return this.known.has(key);
  }

  /** Known team keys, most frequently seen first. */
  allKeys(): string[] {
    return [...this.known.entries()].sort((a, b) => b[1] - a[1]).map(([key]) => key);
  }

  /**
   * The Brazilian state a club usually appears with. Only Brazilian states are
   * filled in: a bare "River Plate" is the Argentine club, not River Plate-URU.
   */
  private usualRegion(base: string, observed: Map<string, Map<string, number>>): string | undefined {
    const counts = [...(observed.get(base) ?? new Map<string, number>()).entries()].filter(([region]) => BRAZILIAN_STATES.has(region));
    if (counts.length) return counts.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0][0];
    return DEFAULT_REGION[base];
  }

  displayName(key: string): string {
    if (DISPLAY[key]) return DISPLAY[key];
    const [base, region] = key.split('|');
    const counts = this.spellings.get(key);
    let name = base.replace(/\b\w/g, (c) => c.toUpperCase());
    if (counts) {
      const ranked = [...counts.entries()].sort((a, b) => Number(hasAccents(b[0])) - Number(hasAccents(a[0])) || b[1] - a[1]);
      name = ranked[0][0];
    }
    const ambiguous = (this.regionsByBase.get(base)?.size ?? 0) > 1;
    return ambiguous && region ? `${name}-${region}` : name;
  }

  /**
   * Resolve a user's name for a team to a known team key, tolerating
   * accents, state suffixes, full club names and partial names.
   */
  resolve(query: string): string | undefined {
    const parsed = parseTeamName(query);
    if (parsed.region && this.known.has(teamKey(parsed.base, parsed.region))) return teamKey(parsed.base, parsed.region);
    if (!parsed.region) {
      // The best-known club of that name: "Botafogo" → Botafogo-RJ, "River Plate" → the Argentine club.
      const sameName = this.allKeys().find((key) => key.split('|')[0] === parsed.base);
      if (sameName) return sameName;
    }
    const folded = fold(query);
    const candidates = this.allKeys().filter((key) => {
      const display = fold(this.displayName(key));
      const [base, region] = key.split('|');
      return (display === folded || base === parsed.base) && (!parsed.region || parsed.region === region);
    });
    if (candidates.length) return candidates[0];
    const partial = this.allKeys().filter((key) => {
      const base = key.split('|')[0];
      return parsed.base.length >= 4 && (base.startsWith(parsed.base + ' ') || parsed.base.startsWith(base + ' '));
    });
    return partial.length === 1 ? partial[0] : undefined;
  }

  suggestionsFor(query: string): string[] {
    const words = fold(query).split(/[^a-z0-9]+/).filter((w) => w.length >= 3);
    return this.allKeys()
      .map((key) => this.displayName(key))
      .filter((name) => words.some((w) => fold(name).includes(w)))
      .slice(0, 5);
  }
}

function cleanSpelling(raw: string): string {
  return raw
    .replace(/\s*\([^)]*\)\s*/g, ' ')
    .replace(/\s*-\s*[A-Za-z]{2,3}$/, (m) => (BRAZILIAN_STATES.has(m.replace(/[\s-]/g, '').toUpperCase()) || COUNTRIES.has(m.replace(/[\s-]/g, '').toUpperCase()) ? '' : m))
    .replace(/\s[A-Z]{2}$/, (m) => (BRAZILIAN_STATES.has(m.trim()) ? '' : m))
    .replace(/\s+/g, ' ')
    .trim();
}
