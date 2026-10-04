/**
 * Team name normalisation.
 *
 * The datasets spell the same club many ways ("Palmeiras-SP", "Palmeiras",
 * "Atlético - MG", "Atletico Mineiro", "EC Bahia"...) and reuse the same name
 * for different clubs ("Botafogo RJ" / "Botafogo PB"). A name is split into a
 * folded base plus an optional state/country tag; the most common tag for a
 * base becomes its default, so "Flamengo" and "Flamengo-RJ" are one team while
 * "Flamengo-PI" stays distinct.
 */

const UFS = new Set(
  'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split(' '),
);

/** Lowercase, strip accents and punctuation noise. */
export function fold(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[.'’]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

type Alias = [base: string, tag?: string];

/** Folded name (optionally "name|TAG") -> canonical base and tag. */
const ALIASES: Record<string, Alias> = {
  'atletico mineiro': ['atletico', 'MG'],
  'clube atletico mineiro': ['atletico', 'MG'],
  'atletico goianiense': ['atletico', 'GO'],
  'atletico paranaense': ['athletico', 'PR'],
  'athletico paranaense': ['athletico', 'PR'],
  'club athletico paranaense': ['athletico', 'PR'],
  athletico: ['athletico', 'PR'],
  'atletico|PR': ['athletico', 'PR'],
  'america fc (minas gerais)': ['america', 'MG'],
  'america mineiro': ['america', 'MG'],
  'america fc natal': ['america', 'RN'],
  'america natal': ['america', 'RN'],
  'vasco da gama': ['vasco'],
  'club de regatas vasco da gama': ['vasco'],
  'sport recife': ['sport'],
  'sport club do recife': ['sport'],
  'nautico capibaribe': ['nautico'],
  'red bull bragantino': ['bragantino', 'SP'],
  'portuguesa desportos': ['portuguesa', 'SP'],
  'cs alagoano': ['csa'],
  'ceara sporting club': ['ceara'],
  'clube do remo': ['remo'],
  'brasil de pelotas': ['brasil', 'RS'],
  'gremio barueri': ['barueri'],
  'moto clube': ['moto club'],
  'moto club de sao luis': ['moto club'],
  'boavista sport club': ['boavista', 'RJ'],
  'macae esporte': ['macae'],
  'flamengo do piaui': ['flamengo', 'PI'],
  'sao jose|POA': ['sao jose', 'RS'],
  'iv de julho': ['4 de julho'],
  'atletico acreano': ['atletico', 'AC'],
  'atletico alagoinhas': ['atletico', 'BA'],
  'afogados da ingazeira': ['afogados'],
  'boavista sc saquarema': ['boavista', 'RJ'],
  'river|AC': ['river', 'PI'],
  'metropolitano maringa': ['maringa'],
  'palmas fr': ['palmas'],
  'palmas ltda': ['palmas'],
  'xv piracicaba': ['xv de piracicaba'],
  'retro fc brasil': ['retro'],
  'independente de tucurui': ['independente', 'PA'],
  'sport club corinthians paulista': ['corinthians'],
  'corinthians paulista': ['corinthians'],
  'clube de regatas do flamengo': ['flamengo', 'RJ'],
  'sociedade esportiva palmeiras': ['palmeiras'],
  'sao paulo futebol clube': ['sao paulo'],
  'santos futebol clube': ['santos', 'SP'],
  'gremio foot-ball porto alegrense': ['gremio'],
  'sport club internacional': ['internacional', 'RS'],
  'cruzeiro esporte clube': ['cruzeiro'],
  'fluminense football club': ['fluminense', 'RJ'],
  'botafogo de futebol e regatas': ['botafogo', 'RJ'],
  'esporte clube bahia': ['bahia'],
  'esporte clube vitoria': ['vitoria', 'BA'],
};

/** Bases where an untagged name is a different club from every tagged one. */
const NO_DEFAULT_TAG = new Set(['river plate']);

const DISPLAY_OVERRIDE: Record<string, string> = {
  atletico: 'Atlético-MG',
  america: 'América-MG',
  athletico: 'Athletico-PR',
};

const LEADING_ORG = /^(ec|ad|ae|ca|ce|ge|se|sc|cs|fc) /;
const TRAILING_ORG = / (fc|ec|futebol clube|esporte clube|clube)$/;

export interface ParsedName {
  base: string;
  tag?: string;
  /** Human readable form of the base, accents preserved. */
  label: string;
}

export function parseTeamName(raw: string): ParsedName {
  let s = raw.trim().replace(/\s+/g, ' ');
  const whole = ALIASES[fold(s)];
  if (whole) return { base: whole[0], tag: whole[1], label: s };

  let tag: string | undefined;
  const paren = s.match(/\(([A-Z]{2,3})\)\s*$/);
  if (paren) tag = paren[1];
  s = s.replace(/\s*\([^)]*\)/g, '').trim();
  const dashed = s.match(/^(.+?)\s*-\s*([A-Z]{2,3})$/);
  if (dashed) {
    s = dashed[1];
    tag = dashed[2];
  } else {
    const spaced = s.match(/^(.+) ([A-Z]{2})$/);
    if (spaced && UFS.has(spaced[2])) {
      s = spaced[1];
      tag = spaced[2];
    }
  }

  let base = fold(s);
  // Rejoin spelled-out initials: "c r b" (from "C. R. B.") -> "crb", "serra f c" -> "serra fc"
  base = base.replace(/\b(\w) (?=\w\b)/g, '$1');
  const alias =
    lookupAlias(base, tag) ?? lookupAlias(base.replace(LEADING_ORG, '').replace(TRAILING_ORG, ''), tag);
  if (alias) return { base: alias[0], tag: alias[1] ?? tag, label: s };
  const stripped = base.replace(LEADING_ORG, '').replace(TRAILING_ORG, '');
  if (stripped) base = stripped;
  return { base, tag, label: s };
}

function lookupAlias(base: string, tag?: string): Alias | undefined {
  return (tag ? ALIASES[`${base}|${tag}`] : undefined) ?? ALIASES[base];
}

export class TeamRegistry {
  private tagCounts = new Map<string, Map<string, number>>();
  private labels = new Map<string, Map<string, number>>();
  private defaults = new Map<string, string | undefined>();
  private names = new Map<string, string>();
  private weight = new Map<string, number>();

  /** Record one occurrence of a raw team name; call for every row before `idOf`. */
  observe(raw: string): ParsedName {
    const p = parseTeamName(raw);
    if (p.tag) bump(this.tagCounts, p.base, p.tag);
    if (fold(p.label) === p.base) bump(this.labels, `${p.base}|${p.tag ?? ''}`, p.label);
    return p;
  }

  private defaultTag(base: string): string | undefined {
    if (NO_DEFAULT_TAG.has(base)) return undefined;
    if (!this.defaults.has(base)) {
      const counts = [...(this.tagCounts.get(base) ?? [])].sort((a, b) => b[1] - a[1]);
      this.defaults.set(base, counts[0]?.[0]);
    }
    return this.defaults.get(base);
  }

  /** Stable team id; registers a display name and usage weight for it. */
  idOf(p: ParsedName, count = true): string {
    const def = this.defaultTag(p.base);
    const isDefault = !p.tag || p.tag === def;
    const id = isDefault ? p.base : `${p.base}-${p.tag!.toLowerCase()}`;
    if (count) this.weight.set(id, (this.weight.get(id) ?? 0) + 1);
    if (!this.names.has(id)) {
      const label = this.bestLabel(p.base, p.tag ?? def) ?? p.label;
      this.names.set(id, isDefault ? (DISPLAY_OVERRIDE[p.base] ?? label) : `${label}-${p.tag}`);
    }
    return id;
  }

  private bestLabel(base: string, tag?: string): string | undefined {
    // Spellings seen with this tag first, so "Guarani-SP" is not labelled like "Guaraní (PAR)".
    const counts = new Map<string, number>();
    for (const key of new Set([`${base}|${tag ?? ''}`, `${base}|`])) {
      for (const [form, n] of this.labels.get(key) ?? []) counts.set(form, (counts.get(form) ?? 0) + n);
    }
    const forms = [...counts];
    // Prefer accented spellings ("Grêmio" over "Gremio"), then the most frequent.
    forms.sort((a, b) => Number(hasAccent(b[0])) - Number(hasAccent(a[0])) || b[1] - a[1]);
    return forms[0]?.[0];
  }

  name(id: string): string {
    return this.names.get(id) ?? id;
  }

  has(id: string): boolean {
    return this.weight.has(id);
  }

  /** Resolve free-text user input to a known team id. */
  resolve(query: string): string | undefined {
    const p = parseTeamName(query);
    const exact = this.idOf(p, false);
    if (this.weight.has(exact)) return exact;
    if (this.weight.has(p.base)) return p.base;
    // Fall back to whole-word containment, preferring the most-played team.
    const words = ` ${p.base} `;
    let best: string | undefined;
    for (const [id, w] of this.weight) {
      const idBase = ` ${id.replace(/-[a-z]{2,3}$/, '')} `;
      if (idBase.includes(words) && w > (best ? this.weight.get(best)! : 0)) best = id;
    }
    return best;
  }
}

function bump(m: Map<string, Map<string, number>>, k: string, v: string) {
  let inner = m.get(k);
  if (!inner) m.set(k, (inner = new Map()));
  inner.set(v, (inner.get(v) ?? 0) + 1);
}

function hasAccent(s: string): boolean {
  return /[^\x00-\x7f]/.test(s);
}
