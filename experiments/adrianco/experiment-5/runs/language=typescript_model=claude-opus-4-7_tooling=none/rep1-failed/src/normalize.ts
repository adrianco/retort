const STATE_SUFFIX_RE = /[-\s]([A-Z]{2})$/;

const REPLACEMENTS: Array<[RegExp, string]> = [
  [/\s*\(antigo[^)]*\)/i, ''],
  [/[áàâãä]/g, 'a'],
  [/[éèêë]/g, 'e'],
  [/[íìîï]/g, 'i'],
  [/[óòôõö]/g, 'o'],
  [/[úùûü]/g, 'u'],
  [/[ç]/g, 'c'],
  [/[ÁÀÂÃÄ]/g, 'A'],
  [/[ÉÈÊË]/g, 'E'],
  [/[ÍÌÎÏ]/g, 'I'],
  [/[ÓÒÔÕÖ]/g, 'O'],
  [/[ÚÙÛÜ]/g, 'U'],
  [/[Ç]/g, 'C'],
];

const ALIASES: Record<string, string> = {
  athletico: 'atletico-pr',
  'atletico paranaense': 'atletico-pr',
  'club athletico paranaense': 'atletico-pr',
  'atletico mineiro': 'atletico-mg',
  'clube atletico mineiro': 'atletico-mg',
  'atletico goianiense': 'atletico-go',
  'sao paulo': 'sao paulo',
  'sao paulo fc': 'sao paulo',
  'sport club corinthians paulista': 'corinthians',
  corinthians: 'corinthians',
  'sport club internacional': 'internacional',
  'sport club do recife': 'sport',
  sport: 'sport',
  'fortaleza esporte clube': 'fortaleza',
  'gremio foot-ball porto alegrense': 'gremio',
  flamengo: 'flamengo',
  fluminense: 'fluminense',
  palmeiras: 'palmeiras',
  santos: 'santos',
  vasco: 'vasco',
  'vasco da gama': 'vasco',
  botafogo: 'botafogo',
  cruzeiro: 'cruzeiro',
  bahia: 'bahia',
  ceara: 'ceara',
  goias: 'goias',
  coritiba: 'coritiba',
  vitoria: 'vitoria',
  parana: 'parana',
  figueirense: 'figueirense',
  chapecoense: 'chapecoense',
  america: 'america-mg',
};

export function normalizeTeam(name: string | undefined | null): string {
  if (!name) return '';
  let s = String(name).trim();
  s = s.replace(/^"|"$/g, '');
  s = s.replace(/\s*\(antigo[^)]*\)/i, '');

  let suffixState: string | undefined;
  const suffixMatch = s.match(STATE_SUFFIX_RE);
  if (suffixMatch) {
    suffixState = suffixMatch[1].toLowerCase();
    s = s.replace(STATE_SUFFIX_RE, '').trim();
  }

  s = s.replace(/\s*-\s*$/g, '').trim();

  for (const [re, rep] of REPLACEMENTS) {
    s = s.replace(re, rep);
  }

  s = s.toLowerCase().replace(/\s+/g, ' ').trim();

  if (ALIASES[s]) {
    return ALIASES[s];
  }

  if (s === 'america' && suffixState === 'mg') return 'america-mg';
  if (s === 'atletico' && suffixState) return `atletico-${suffixState}`;

  if (suffixState && /^(atletico|america)$/.test(s)) {
    return `${s}-${suffixState}`;
  }

  return s;
}

export function teamMatches(query: string, teamName: string): boolean {
  const q = normalizeTeam(query);
  const t = normalizeTeam(teamName);
  if (!q || !t) return false;
  if (q === t) return true;
  if (t.includes(q) || q.includes(t)) return true;
  return false;
}

export function displayTeam(name: string): string {
  return name.replace(/^"|"$/g, '').trim();
}
