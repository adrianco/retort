/**
 * Team identity: the datasets spell the same club many ways
 * ("Palmeiras-SP", "Palmeiras - SP", "Sociedade Esportiva Palmeiras",
 * "Sao Paulo", "São Paulo", "Atlético - MG", "Atletico Mineiro"...).
 * Every spelling is reduced to a stable key, while clubs that share a name
 * but come from different states (Atlético-MG / Atlético-PR / Atlético-GO,
 * Botafogo-RJ / Botafogo-PB) are kept apart.
 */
import { countAccented, fold } from './text.js';

export interface TeamIdentity {
  key: string;
  name: string;
  canonical: boolean;
}

const BR_STATES = new Set([
  'ac', 'al', 'ap', 'am', 'ba', 'ce', 'df', 'es', 'go', 'ma', 'mt', 'ms', 'mg', 'pa',
  'pb', 'pr', 'pe', 'pi', 'rj', 'rn', 'rs', 'ro', 'rr', 'sc', 'sp', 'se', 'to',
]);

const COUNTRIES: Record<string, string> = {
  uru: 'URU', par: 'PAR', equ: 'ECU', ecu: 'ECU', per: 'PER', ven: 'VEN', bol: 'BOL',
  chi: 'CHI', arg: 'ARG', col: 'COL', mex: 'MEX',
};

interface Club {
  name: string;
  state: string;
  variants: string[];
}

/** Clubs we know well enough to give one proper, accented name. */
const CLUBS: Club[] = [
  { name: 'Flamengo', state: 'RJ', variants: ['cr flamengo', 'clube de regatas do flamengo'] },
  { name: 'Fluminense', state: 'RJ', variants: ['fluminense fc'] },
  { name: 'Botafogo', state: 'RJ', variants: ['botafogo fr', 'botafogo de futebol e regatas'] },
  { name: 'Vasco da Gama', state: 'RJ', variants: ['vasco', 'cr vasco da gama', 'club de regatas vasco da gama'] },
  { name: 'Corinthians', state: 'SP', variants: ['sport club corinthians paulista', 'sc corinthians paulista', 'corinthians paulista'] },
  { name: 'Palmeiras', state: 'SP', variants: ['se palmeiras', 'sociedade esportiva palmeiras'] },
  { name: 'Santos', state: 'SP', variants: ['santos fc'] },
  { name: 'São Paulo', state: 'SP', variants: ['sao paulo fc', 'sao paulo futebol clube', 'spfc'] },
  { name: 'Red Bull Bragantino', state: 'SP', variants: ['bragantino', 'rb bragantino'] },
  { name: 'Ponte Preta', state: 'SP', variants: ['aa ponte preta'] },
  { name: 'Guarani', state: 'SP', variants: ['guarani fc'] },
  { name: 'Portuguesa', state: 'SP', variants: ['portuguesa desportos'] },
  { name: 'São Caetano', state: 'SP', variants: [] },
  { name: 'Santo André', state: 'SP', variants: [] },
  { name: 'Grêmio Barueri', state: 'SP', variants: ['barueri'] },
  { name: 'Grêmio Prudente', state: 'SP', variants: [] },
  { name: 'Mirassol', state: 'SP', variants: [] },
  { name: 'Grêmio', state: 'RS', variants: ['gremio fbpa', 'gremio foot ball porto alegrense'] },
  { name: 'Internacional', state: 'RS', variants: ['sc internacional'] },
  { name: 'Juventude', state: 'RS', variants: [] },
  { name: 'Cruzeiro', state: 'MG', variants: ['cruzeiro ec'] },
  { name: 'Atlético Mineiro', state: 'MG', variants: ['clube atletico mineiro', 'atletico mg'] },
  { name: 'América Mineiro', state: 'MG', variants: ['america fc minas gerais', 'america mg'] },
  { name: 'Ipatinga', state: 'MG', variants: [] },
  { name: 'Athletico Paranaense', state: 'PR', variants: ['atletico paranaense', 'athletico', 'club athletico paranaense', 'athletico pr', 'atletico pr'] },
  { name: 'Coritiba', state: 'PR', variants: [] },
  { name: 'Paraná', state: 'PR', variants: ['parana clube'] },
  { name: 'Atlético Goianiense', state: 'GO', variants: ['atletico go'] },
  { name: 'Goiás', state: 'GO', variants: [] },
  { name: 'Vila Nova', state: 'GO', variants: [] },
  { name: 'Bahia', state: 'BA', variants: [] },
  { name: 'Vitória', state: 'BA', variants: [] },
  { name: 'Sport', state: 'PE', variants: ['sport recife', 'sport club do recife'] },
  { name: 'Náutico', state: 'PE', variants: ['nautico capibaribe'] },
  { name: 'Santa Cruz', state: 'PE', variants: [] },
  { name: 'Ceará', state: 'CE', variants: ['ceara sc', 'ceara sporting club'] },
  { name: 'Fortaleza', state: 'CE', variants: [] },
  { name: 'Chapecoense', state: 'SC', variants: [] },
  { name: 'Avaí', state: 'SC', variants: [] },
  { name: 'Figueirense', state: 'SC', variants: [] },
  { name: 'Criciúma', state: 'SC', variants: [] },
  { name: 'Joinville', state: 'SC', variants: [] },
  { name: 'Cuiabá', state: 'MT', variants: [] },
  { name: 'CSA', state: 'AL', variants: ['c s a'] },
  { name: 'CRB', state: 'AL', variants: ['c r b'] },
  { name: 'América de Natal', state: 'RN', variants: ['america fc natal'] },
  { name: 'Paysandu', state: 'PA', variants: [] },
  { name: 'Remo', state: 'PA', variants: ['clube do remo'] },
  { name: 'Brasiliense', state: 'DF', variants: [] },
];

/** Bare names that only identify a club once the state is known. */
const BY_NAME_AND_STATE: Record<string, string> = {
  'atletico|mg': 'Atlético Mineiro',
  'atletico|pr': 'Athletico Paranaense',
  'athletico|pr': 'Athletico Paranaense',
  'atletico|go': 'Atlético Goianiense',
  'america|mg': 'América Mineiro',
  'america|rn': 'América de Natal',
};

/** Names shared by unrelated smaller clubs, so the state must stay part of the identity. */
const SHARED_NAMES = new Set([
  'atletico', 'america', 'operario', 'sao raimundo', 'nacional', 'rio branco', 'real', 'river',
  'comercial', 'independente', 'sao jose', 'ypiranga', 'boavista', 'sao francisco', 'guarany',
]);

const CLUB_BY_KEY = new Map<string, Club>();
for (const club of CLUBS) {
  CLUB_BY_KEY.set(fold(club.name), club);
  for (const v of club.variants) CLUB_BY_KEY.set(v, club);
}

const LEADING_TOKENS = /^(?:ec|fc|sc|ac|se|cr|ca|ce|cs|ad|ae|ge|aa|clube|club)\s+/;
const TRAILING_TOKENS = /\s+(?:ec|fc|sc|ac|fr|f c|e c|s c|clube|sport club|futebol clube|esporte clube)$/;

function withoutClubWords(folded: string): string {
  let previous: string;
  let result = folded;
  do {
    previous = result;
    result = result.replace(LEADING_TOKENS, '').replace(TRAILING_TOKENS, '');
  } while (result !== previous && result.length > 0);
  return result || folded;
}

function canonical(club: Club): TeamIdentity {
  return { key: fold(club.name), name: club.name, canonical: true };
}

function knownClub(folded: string): Club | undefined {
  return CLUB_BY_KEY.get(folded) ?? CLUB_BY_KEY.get(withoutClubWords(folded));
}

/** Splits "Atlético - MG", "Gremio RS", "Nacional (URU)", "Delfín-EQU" into a name and a state/country. */
function splitQualifier(raw: string): { base: string; qualifier?: string } {
  let base = raw;
  let qualifier: string | undefined;
  for (let i = 0; i < 3; i++) {
    const paren = /^(.*?)\s*\(([^)]*)\)\s*$/.exec(base);
    if (paren) {
      const q = fold(paren[2]);
      if (!qualifier && (BR_STATES.has(q) || COUNTRIES[q])) qualifier = q;
      base = paren[1];
      continue;
    }
    const hyphen = /^(.*?\S)\s*-\s*([A-Za-z]{2,3})\s*$/.exec(base);
    if (hyphen && (BR_STATES.has(hyphen[2].toLowerCase()) || COUNTRIES[hyphen[2].toLowerCase()])) {
      qualifier ??= hyphen[2].toLowerCase();
      base = hyphen[1];
      continue;
    }
    const spaced = /^(.*\S)\s+([A-Z]{2})$/.exec(base);
    if (spaced && BR_STATES.has(spaced[2].toLowerCase())) {
      qualifier ??= spaced[2].toLowerCase();
      base = spaced[1];
      continue;
    }
    break;
  }
  return { base: base.trim(), qualifier };
}

export function identifyTeam(raw: string): TeamIdentity {
  const original = raw.trim().replace(/\s+/g, ' ');
  const whole = CLUB_BY_KEY.get(fold(original));
  if (whole) return canonical(whole);

  const { base, qualifier } = splitQualifier(original);
  const folded = fold(base);
  const plain = withoutClubWords(folded);

  if (qualifier && BR_STATES.has(qualifier)) {
    const byState = BY_NAME_AND_STATE[`${folded}|${qualifier}`] ?? BY_NAME_AND_STATE[`${plain}|${qualifier}`];
    if (byState) return canonical(CLUB_BY_KEY.get(fold(byState))!);
    const club = knownClub(folded);
    if (club && club.state.toLowerCase() === qualifier) return canonical(club);
    if (club || SHARED_NAMES.has(plain)) {
      return { key: `${plain}|${qualifier}`, name: `${base}-${qualifier.toUpperCase()}`, canonical: false };
    }
    return { key: plain, name: base, canonical: false };
  }
  if (qualifier && COUNTRIES[qualifier]) {
    return { key: `${plain}|${qualifier}`, name: `${base} (${COUNTRIES[qualifier]})`, canonical: false };
  }
  const club = knownClub(folded);
  if (club) return canonical(club);
  return { key: plain, name: base, canonical: false };
}

/** Every team seen in the match data, with the best display name found for it. */
export class TeamRegistry {
  private readonly names = new Map<string, string>();
  private readonly canonicalKeys = new Set<string>();
  private readonly appearances = new Map<string, number>();

  register(raw: string): string {
    const id = identifyTeam(raw);
    const current = this.names.get(id.key);
    if (id.canonical) {
      this.canonicalKeys.add(id.key);
      this.names.set(id.key, id.name);
    } else if (current === undefined || (!this.canonicalKeys.has(id.key) && countAccented(id.name) > countAccented(current))) {
      this.names.set(id.key, id.name);
    }
    this.appearances.set(id.key, (this.appearances.get(id.key) ?? 0) + 1);
    return id.key;
  }

  name(key: string): string {
    return this.names.get(key) ?? key;
  }

  has(key: string): boolean {
    return this.names.has(key);
  }

  /** Finds the team a person most likely means, or null. */
  resolve(query: string): string | null {
    const id = identifyTeam(query);
    if (this.names.has(id.key)) return id.key;
    const wanted = fold(query);
    if (!wanted) return null;
    const candidates = [...this.names.entries()].filter(([key, name]) => {
      const folded = fold(name);
      return folded === wanted || key === wanted || folded.includes(wanted) || key.includes(wanted) || (wanted.includes(folded) && folded.length >= 4);
    });
    if (candidates.length === 0) return null;
    candidates.sort(([a], [b]) => (this.appearances.get(b) ?? 0) - (this.appearances.get(a) ?? 0));
    return candidates[0][0];
  }
}
