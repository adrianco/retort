/**
 * Team identity resolution.
 *
 * The five match files spell the same club five ways:
 *
 *   Brasileirao_Matches.csv        "Atletico-PR", "Sao Paulo-SP", "Vasco da Gama-RJ"
 *   novo_campeonato_brasileiro.csv "Athletico-PR", "São Paulo",   "Vasco"
 *   BR-Football-Dataset.csv        "Athletico Paranaense", "Sao Paulo", "Vasco Da Gama RJ"
 *   Brazilian_Cup_Matches.csv      "América - MG", "Boavista Sport Club (antigo ...) - RJ"
 *   Libertadores_Matches.csv       "Athletico", "Nacional (URU)", "Guaraní-PAR"
 *
 * Resolution happens in two layers:
 *
 *  1. A structural parse splits a raw label into `{ base, state, country }` by
 *     peeling off state suffixes ("-MG", " - MG", " MG"), country codes
 *     ("(URU)", "-PAR") and club-type noise ("EC", "FC", "Esporte Clube").
 *  2. A curated table pins the clubs where the structural parse alone is
 *     ambiguous -- above all the homonyms where the state is the *only* thing
 *     separating two real clubs (Botafogo-RJ / Botafogo-SP / Botafogo-PB,
 *     América-MG / América-RN, Atlético-MG / Atlético-GO / Athletico-PR).
 *
 * Labels the table does not cover still receive a stable canonical id from the
 * structural parse, so lower-division and South American clubs stay queryable
 * without being enumerated one by one.
 */

import { normalizeName, similarity, slugify } from '../util/text.js';

/** The 26 states plus the Federal District, used to recognise a state suffix. */
export const BRAZILIAN_STATES = new Set([
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
  'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
]);

/** Country codes that appear as suffixes in the Libertadores file. */
export const COUNTRY_CODES = new Set([
  'ARG', 'BOL', 'BRA', 'CHI', 'COL', 'EQU', 'ECU', 'MEX', 'PAR', 'PER', 'URU', 'VEN', 'USA',
]);

const COUNTRY_NAMES: Record<string, string> = {
  ARG: 'Argentina', BOL: 'Bolivia', BRA: 'Brazil', CHI: 'Chile', COL: 'Colombia',
  EQU: 'Ecuador', ECU: 'Ecuador', MEX: 'Mexico', PAR: 'Paraguay', PER: 'Peru',
  URU: 'Uruguay', VEN: 'Venezuela', USA: 'United States',
};

/**
 * Words that decorate a club name without naming it: the initialisms the
 * datasets prefix ("EC Bahia", "CA Taguatinga") and the spelled-out corporate
 * form ("Ceará Sporting Club", "Sport Club do Recife").
 *
 * "sport" is deliberately absent -- Sport Recife's name *is* Sport.
 */
const CLUB_TYPE_TOKENS = new Set([
  'ec', 'fc', 'sc', 'cr', 'ca', 'ad', 'aa', 'se', 'cs', 'cd', 'sd', 'af', 'ce', 'ac', 'esc',
  'club', 'clube', 'futebol', 'sporting', 'esporte', 'esportivo', 'esportiva',
  'associacao', 'sociedade', 'desportivo', 'desportiva', 'desportos', 'atletica', 'regatas',
  'recreativo',
]);

/** Portuguese articles, dropped once the club-type words around them are gone. */
const ARTICLES = new Set(['do', 'da', 'de', 'dos', 'das', 'e']);

export interface ParsedTeamName {
  /** Normalized club name with qualifiers and club-type noise removed. */
  base: string;
  /** Two-letter Brazilian state, when the label carried one. */
  state?: string;
  /** Three-letter country code, when the label carried one. */
  country?: string;
  /** The raw label minus qualifiers, keeping original casing and accents. */
  display: string;
}

export interface Team {
  /** Stable kebab-case identifier, e.g. `flamengo-rj`, `nacional-uru`. */
  id: string;
  /** Display name, e.g. "Flamengo", "Nacional (URU)". */
  name: string;
  state?: string;
  country?: string;
  /** Every raw spelling seen in the source data, for provenance and debugging. */
  aliases: Set<string>;
}

interface CanonicalTeamSpec {
  id: string;
  name: string;
  state?: string;
  country?: string;
  /**
   * Name forms that belong to this club, written as they appear in the wild.
   * They are pushed through `parseTeamName` at build time, so they normalise by
   * exactly the same rules as incoming data.
   */
  bases: string[];
  /**
   * Bases this club answers to *only* when the label also carries its own
   * state or country qualifier.
   *
   * This is how a club shares a base with another without competing for the
   * bare form: Athletico-PR must match "Atletico-PR", but "Atlético" alone
   * belongs to Atlético Mineiro. Listing it here rather than in `bases` makes
   * that independent of declaration order.
   */
  qualifiedOnlyBases?: string[];
  /**
   * When true this club claims bare, state-less labels for its `bases`. At most
   * one club may claim any given base; a second claimant is a configuration
   * error and is rejected at construction.
   */
  primaryForBase?: boolean;
}

/**
 * Curated clubs: every Serie A participant across the datasets, plus the
 * homonym families that need state disambiguation.
 *
 * The generated id for an unlisted `{base, qualifier}` pair is
 * `slug(base)-qualifier`, so listing a club under that exact id (e.g.
 * `botafogo-sp`) is enough to give it a proper display name even when no base
 * form is enumerated for it.
 */
const CANONICAL_TEAMS: CanonicalTeamSpec[] = [
  { id: 'flamengo-rj', name: 'Flamengo', state: 'RJ', bases: ['flamengo'], primaryForBase: true },
  { id: 'fluminense-rj', name: 'Fluminense', state: 'RJ', bases: ['fluminense'], primaryForBase: true },
  { id: 'vasco-rj', name: 'Vasco da Gama', state: 'RJ', bases: ['vasco', 'vasco da gama'], primaryForBase: true },
  { id: 'botafogo-rj', name: 'Botafogo', state: 'RJ', bases: ['botafogo'], primaryForBase: true },
  { id: 'botafogo-sp', name: 'Botafogo-SP', state: 'SP', bases: ['botafogo ribeirao preto'] },
  { id: 'botafogo-pb', name: 'Botafogo-PB', state: 'PB', bases: [] },
  { id: 'corinthians-sp', name: 'Corinthians', state: 'SP', bases: ['corinthians', 'Sport Club Corinthians Paulista'], primaryForBase: true },
  { id: 'palmeiras-sp', name: 'Palmeiras', state: 'SP', bases: ['palmeiras'], primaryForBase: true },
  { id: 'sao-paulo-sp', name: 'São Paulo', state: 'SP', bases: ['sao paulo'], primaryForBase: true },
  { id: 'santos-sp', name: 'Santos', state: 'SP', bases: ['santos'], primaryForBase: true },
  { id: 'ponte-preta-sp', name: 'Ponte Preta', state: 'SP', bases: ['ponte preta'], primaryForBase: true },
  { id: 'portuguesa-sp', name: 'Portuguesa', state: 'SP', bases: ['portuguesa', 'Portuguesa Desportos'], primaryForBase: true },
  { id: 'guarani-sp', name: 'Guarani', state: 'SP', bases: ['guarani'], primaryForBase: true },
  { id: 'sao-caetano-sp', name: 'São Caetano', state: 'SP', bases: ['sao caetano'], primaryForBase: true },
  { id: 'santo-andre-sp', name: 'Santo André', state: 'SP', bases: ['santo andre'], primaryForBase: true },
  { id: 'bragantino-sp', name: 'Red Bull Bragantino', state: 'SP', bases: ['bragantino', 'red bull bragantino', 'rb bragantino'], primaryForBase: true },
  { id: 'audax-sp', name: 'Audax', state: 'SP', bases: ['audax'], primaryForBase: true },
  { id: 'gremio-rs', name: 'Grêmio', state: 'RS', bases: ['gremio'], primaryForBase: true },
  { id: 'internacional-rs', name: 'Internacional', state: 'RS', bases: ['internacional'], primaryForBase: true },
  { id: 'juventude-rs', name: 'Juventude', state: 'RS', bases: ['juventude'], primaryForBase: true },
  { id: 'atletico-mg', name: 'Atlético Mineiro', state: 'MG', bases: ['atletico mineiro', 'atletico'], primaryForBase: true },
  { id: 'cruzeiro-mg', name: 'Cruzeiro', state: 'MG', bases: ['cruzeiro'], primaryForBase: true },
  { id: 'america-mg', name: 'América Mineiro', state: 'MG', bases: ['america mineiro', 'america', 'América FC (Minas Gerais)'], primaryForBase: true },
  { id: 'america-rn', name: 'América-RN', state: 'RN', bases: ['america natal'] },
  { id: 'ipatinga-mg', name: 'Ipatinga', state: 'MG', bases: ['ipatinga'], primaryForBase: true },
  // "Atletico-PR" must land here, but a bare "Atlético" belongs to Mineiro --
  // hence `qualifiedOnlyBases` rather than a second claim on the bare base.
  {
    id: 'athletico-pr',
    name: 'Athletico Paranaense',
    state: 'PR',
    bases: ['athletico', 'athletico paranaense', 'atletico paranaense'],
    qualifiedOnlyBases: ['atletico'],
    primaryForBase: true,
  },
  { id: 'coritiba-pr', name: 'Coritiba', state: 'PR', bases: ['coritiba'], primaryForBase: true },
  { id: 'parana-pr', name: 'Paraná', state: 'PR', bases: ['parana'], primaryForBase: true },
  { id: 'atletico-go', name: 'Atlético Goianiense', state: 'GO', bases: ['atletico goianiense'] },
  { id: 'goias-go', name: 'Goiás', state: 'GO', bases: ['goias'], primaryForBase: true },
  { id: 'vila-nova-go', name: 'Vila Nova', state: 'GO', bases: ['vila nova'], primaryForBase: true },
  { id: 'bahia-ba', name: 'Bahia', state: 'BA', bases: ['bahia'], primaryForBase: true },
  { id: 'vitoria-ba', name: 'Vitória', state: 'BA', bases: ['vitoria'], primaryForBase: true },
  { id: 'sport-pe', name: 'Sport Recife', state: 'PE', bases: ['sport', 'Sport Club do Recife'], primaryForBase: true },
  { id: 'nautico-pe', name: 'Náutico', state: 'PE', bases: ['nautico', 'Nautico Capibaribe'], primaryForBase: true },
  { id: 'santa-cruz-pe', name: 'Santa Cruz', state: 'PE', bases: ['santa cruz'], primaryForBase: true },
  { id: 'ceara-ce', name: 'Ceará', state: 'CE', bases: ['ceara', 'Ceará Sporting Club'], primaryForBase: true },
  { id: 'fortaleza-ce', name: 'Fortaleza', state: 'CE', bases: ['fortaleza'], primaryForBase: true },
  { id: 'csa-al', name: 'CSA', state: 'AL', bases: ['csa'], primaryForBase: true },
  { id: 'crb-al', name: 'CRB', state: 'AL', bases: ['crb'], primaryForBase: true },
  { id: 'avai-sc', name: 'Avaí', state: 'SC', bases: ['avai'], primaryForBase: true },
  { id: 'figueirense-sc', name: 'Figueirense', state: 'SC', bases: ['figueirense'], primaryForBase: true },
  { id: 'chapecoense-sc', name: 'Chapecoense', state: 'SC', bases: ['chapecoense'], primaryForBase: true },
  { id: 'criciuma-sc', name: 'Criciúma', state: 'SC', bases: ['criciuma'], primaryForBase: true },
  { id: 'joinville-sc', name: 'Joinville', state: 'SC', bases: ['joinville'], primaryForBase: true },
  { id: 'cuiaba-mt', name: 'Cuiabá', state: 'MT', bases: ['cuiaba'], primaryForBase: true },
  { id: 'paysandu-pa', name: 'Paysandu', state: 'PA', bases: ['paysandu'], primaryForBase: true },
  { id: 'remo-pa', name: 'Remo', state: 'PA', bases: ['remo'], primaryForBase: true },
  { id: 'brasiliense-df', name: 'Brasiliense', state: 'DF', bases: ['brasiliense'], primaryForBase: true },
  { id: 'barueri-sp', name: 'Grêmio Barueri', state: 'SP', bases: ['barueri', 'gremio barueri', 'gremio prudente'], primaryForBase: true },
  { id: 'abc-rn', name: 'ABC', state: 'RN', bases: ['abc'], primaryForBase: true },
  { id: 'boavista-rj', name: 'Boavista', state: 'RJ', bases: ['boavista', 'Boavista SC Saquarema', 'Boavista Sport Club (antigo Esporte Clube Barreira)'], primaryForBase: true },
];

const NON_BRAZILIAN_TEAMS: CanonicalTeamSpec[] = [
  { id: 'nacional-uru', name: 'Nacional (URU)', country: 'URU', bases: ['nacional'], primaryForBase: true },
  { id: 'penarol-uru', name: 'Peñarol', country: 'URU', bases: ['penarol'], primaryForBase: true },
  { id: 'boca-juniors-arg', name: 'Boca Juniors', country: 'ARG', bases: ['boca juniors'], primaryForBase: true },
  { id: 'river-plate-arg', name: 'River Plate', country: 'ARG', bases: ['river plate'], primaryForBase: true },
  { id: 'colo-colo-chi', name: 'Colo-Colo', country: 'CHI', bases: ['colo colo'], primaryForBase: true },
  { id: 'atletico-nacional-col', name: 'Atlético Nacional', country: 'COL', bases: ['atletico nacional'], primaryForBase: true },
];

const ALL_SPECS = [...CANONICAL_TEAMS, ...NON_BRAZILIAN_TEAMS];

/** Named derbies, used by the "show me the derbies" style of question. */
export interface Rivalry {
  name: string;
  teams: [string, string];
}

export const RIVALRIES: Rivalry[] = [
  { name: 'Fla-Flu', teams: ['flamengo-rj', 'fluminense-rj'] },
  { name: 'Clássico dos Milhões', teams: ['flamengo-rj', 'vasco-rj'] },
  { name: 'Clássico da Rivalidade', teams: ['flamengo-rj', 'botafogo-rj'] },
  { name: 'Clássico Vovô', teams: ['botafogo-rj', 'fluminense-rj'] },
  { name: 'Clássico dos Gigantes', teams: ['botafogo-rj', 'vasco-rj'] },
  { name: 'Clássico dos Clássicos (RJ)', teams: ['fluminense-rj', 'vasco-rj'] },
  { name: 'Derby Paulista', teams: ['corinthians-sp', 'palmeiras-sp'] },
  { name: 'Majestoso', teams: ['corinthians-sp', 'sao-paulo-sp'] },
  { name: 'Choque-Rei', teams: ['palmeiras-sp', 'sao-paulo-sp'] },
  { name: 'San-São', teams: ['santos-sp', 'sao-paulo-sp'] },
  { name: 'Clássico Alvinegro', teams: ['corinthians-sp', 'santos-sp'] },
  { name: 'Clássico da Saudade', teams: ['palmeiras-sp', 'santos-sp'] },
  { name: 'Grenal', teams: ['gremio-rs', 'internacional-rs'] },
  { name: 'Clássico Mineiro', teams: ['atletico-mg', 'cruzeiro-mg'] },
  { name: 'Atletiba', teams: ['athletico-pr', 'coritiba-pr'] },
  { name: 'Ba-Vi', teams: ['bahia-ba', 'vitoria-ba'] },
  { name: 'Clássico Rei', teams: ['ceara-ce', 'fortaleza-ce'] },
  { name: 'Clássico dos Clássicos (PE)', teams: ['sport-pe', 'nautico-pe'] },
];

/**
 * Collapse a run of single letters back into the acronym it was punctuated out
 * of: "C. R. B." normalises to `["c","r","b"]`, which must rejoin as "crb" to
 * meet the plain "CRB" spelling used everywhere else.
 */
function joinInitialRuns(tokens: string[]): string[] {
  const out: string[] = [];
  for (let i = 0; i < tokens.length; ) {
    let end = i;
    while (end < tokens.length && tokens[end]!.length === 1) end++;
    if (end - i >= 2) {
      out.push(tokens.slice(i, end).join(''));
      i = end;
    } else {
      out.push(tokens[i]!);
      i++;
    }
  }
  return out;
}

/** Peel state / country qualifiers and club-type noise off a raw label. */
export function parseTeamName(raw: string): ParsedTeamName {
  let working = raw.trim();
  let state: string | undefined;
  let country: string | undefined;

  // "(URU)" / "(PAR)" anywhere in the label. Parenthesised text that is not a
  // country code (e.g. "(antigo Esporte Clube Barreira)") is left in place and
  // handled by the club-type stripping below.
  const parenthesised = /\(([A-Za-z]{3})\)/.exec(working);
  if (parenthesised && COUNTRY_CODES.has(parenthesised[1]!.toUpperCase())) {
    country = parenthesised[1]!.toUpperCase();
    working = `${working.slice(0, parenthesised.index)} ${working.slice(parenthesised.index + parenthesised[0].length)}`;
  }

  // Trailing "-MG", " - MG", " MG", "-PAR", " PAR". Loops because a label can
  // carry both a state and a country code.
  for (let i = 0; i < 2; i++) {
    const suffix = /([\s-]+)([A-Za-z]{2,3})\s*$/.exec(working);
    if (!suffix) break;
    const separator = suffix[1]!;
    const code = suffix[2]!.toUpperCase();

    // "SC", "CE", "SE" and "AC" are both state codes and club-type
    // abbreviations (Sport Club, Atlético Clube). Across all five files a real
    // state suffix is always set off by a hyphen -- "Avaí-SC", "Ceará - CE" --
    // while the club-type sense appears space-separated: "Central SC" is
    // Central Sport Club of Pernambuco, "River AC" is Ríver Atlético Clube of
    // Piauí. Reading those as states split each club in two.
    const ambiguous = CLUB_TYPE_TOKENS.has(code.toLowerCase());
    const hyphenated = separator.includes('-');

    if (code.length === 2 && BRAZILIAN_STATES.has(code) && (!ambiguous || hyphenated)) {
      state ??= code;
    } else if (code.length === 3 && COUNTRY_CODES.has(code)) {
      country ??= code;
    } else if (ambiguous) {
      // Leave it in place; the club-type stripping below removes it.
      break;
    } else {
      break;
    }
    working = working.slice(0, suffix.index);
  }

  const display = working.replace(/\s+/g, ' ').trim() || raw.trim();

  // Drop club-type words and articles wherever they sit, but never the last
  // token standing -- "CSA", "CRB" and "ABC" *are* the whole name.
  let tokens = normalizeName(working).replace(/[()]/g, ' ').split(/\s+/).filter(Boolean);
  if (tokens.length > 1) {
    const kept = tokens.filter((t) => !CLUB_TYPE_TOKENS.has(t) && !ARTICLES.has(t));
    if (kept.length > 0) tokens = kept;
  }
  const base = joinInitialRuns(tokens).join(' ');

  const parsed: ParsedTeamName = { base, display };
  if (state) parsed.state = state;
  if (country && country !== 'BRA') parsed.country = country;
  return parsed;
}

/**
 * Interns raw team labels into canonical `Team` records.
 *
 * Built incrementally while the CSVs are read, so the team set is exactly what
 * the data contains -- the curated table only decides *how* labels merge, it
 * never invents clubs that never played.
 */
export class TeamRegistry {
  private readonly teams = new Map<string, Team>();
  /** `base|qualifier` -> team id, where qualifier is a state or country code. */
  private readonly byQualifiedBase = new Map<string, string>();
  /** `base` -> team id for the club that owns bare, unqualified labels. */
  private readonly byBase = new Map<string, string>();
  /** Raw label -> team id; short-circuits the parse for repeated labels. */
  private readonly rawCache = new Map<string, string>();
  private readonly specById = new Map<string, CanonicalTeamSpec>();

  constructor() {
    // Curated name forms go through the same parse as incoming data, so a base
    // written as "Sport Club do Recife" indexes under exactly the key that the
    // FIFA file's spelling of it produces.
    const normalise = (forms: string[]) =>
      [...new Set(forms.map((form) => parseTeamName(form).base))].filter(Boolean);

    for (const spec of ALL_SPECS) {
      this.specById.set(spec.id, spec);
      const qualifier = spec.state ?? spec.country;
      if (!qualifier) continue;
      for (const base of normalise([...spec.bases, ...(spec.qualifiedOnlyBases ?? [])])) {
        const key = `${base}|${qualifier}`;
        if (!this.byQualifiedBase.has(key)) this.byQualifiedBase.set(key, spec.id);
      }
    }

    // Bare-label ownership. Declared primaries claim first and a double claim
    // is an error rather than a silent, order-dependent win; specs that declare
    // no primary then pick up any base still unclaimed.
    for (const spec of ALL_SPECS) {
      if (!spec.primaryForBase) continue;
      for (const base of normalise(spec.bases)) {
        const owner = this.byBase.get(base);
        if (owner && owner !== spec.id) {
          throw new Error(
            `Team table conflict: "${base}" is claimed as a primary base by both ${owner} and ${spec.id}. ` +
              'Move it to `qualifiedOnlyBases` on whichever club should not own the bare name.',
          );
        }
        this.byBase.set(base, spec.id);
      }
    }
    for (const spec of ALL_SPECS) {
      for (const base of normalise(spec.bases)) {
        if (!this.byBase.has(base)) this.byBase.set(base, spec.id);
      }
    }
  }

  /** Resolve a raw dataset label to a canonical team, creating it if new. */
  intern(raw: string): Team {
    const cached = this.rawCache.get(raw);
    if (cached !== undefined) {
      const team = this.teams.get(cached)!;
      team.aliases.add(raw);
      return team;
    }

    const parsed = parseTeamName(raw);
    const id = this.lookupId(parsed) ?? this.mintId(parsed, raw);

    let team = this.teams.get(id);
    if (!team) {
      const spec = this.specById.get(id);
      team = {
        id,
        name: spec?.name ?? displayNameFor(parsed),
        aliases: new Set(),
      };
      const state = spec?.state ?? parsed.state;
      const country = spec?.country ?? parsed.country;
      if (state) team.state = state;
      if (country) team.country = country;
      this.teams.set(id, team);
    }
    // A team first seen under a bare label has no qualifier, which would let
    // it absorb every state-qualified homonym (Real-RR and Real-RO both
    // landing on "Real"). Adopting the first qualifier seen means the next,
    // different one mints its own club.
    if (!team.state && !team.country) {
      if (parsed.state) team.state = parsed.state;
      else if (parsed.country) team.country = parsed.country;
    }

    team.aliases.add(raw);
    this.rawCache.set(raw, id);
    return team;
  }

  /**
   * Map a parsed label onto an existing team id.
   *
   * A qualified label first tries its exact `base|qualifier` key, then falls
   * back to the bare-base owner -- but only if that owner's own qualifier is
   * absent or identical, which is what keeps Botafogo-PB from collapsing into
   * Botafogo-RJ.
   */
  private lookupId(parsed: ParsedTeamName): string | undefined {
    const qualifier = parsed.state ?? parsed.country;
    if (qualifier) {
      const exact = this.byQualifiedBase.get(`${parsed.base}|${qualifier}`);
      if (exact) return exact;
    }
    const bare = this.byBase.get(parsed.base);
    if (!bare) return undefined;
    if (!qualifier) return bare;

    const ownerQualifier = this.qualifierOf(bare);
    return !ownerQualifier || ownerQualifier === qualifier ? bare : undefined;
  }

  private qualifierOf(id: string): string | undefined {
    const team = this.teams.get(id);
    if (team) return team.state ?? team.country;
    const spec = this.specById.get(id);
    return spec?.state ?? spec?.country;
  }

  private mintId(parsed: ParsedTeamName, raw: string): string {
    const qualifier = parsed.state ?? parsed.country;
    const slug = slugify(parsed.base);
    let id = qualifier ? `${slug}-${qualifier.toLowerCase()}` : slug;
    if (id === '' || id === '-') id = slugify(raw) || 'unknown-team';

    if (qualifier) this.byQualifiedBase.set(`${parsed.base}|${qualifier}`, id);
    if (!this.byBase.has(parsed.base)) this.byBase.set(parsed.base, id);
    return id;
  }

  get(id: string): Team | undefined {
    return this.teams.get(id);
  }

  all(): Team[] {
    return [...this.teams.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  get size(): number {
    return this.teams.size;
  }

  /**
   * Resolve a user's free-text team name.
   *
   * Tries, in order: canonical id, exact name/alias match, the alias table,
   * unique substring match, then fuzzy similarity above 0.8. Returns the best
   * match plus near-ties so callers can report ambiguity instead of guessing
   * silently.
   */
  resolveQuery(input: string): { team?: Team; candidates: Team[] } {
    const trimmed = input.trim();
    if (trimmed === '') return { candidates: [] };
    // "???" normalises to the empty string, which is a substring of every
    // team name and would otherwise resolve to an arbitrary club.
    if (parseTeamName(trimmed).base === '') return { candidates: [] };

    const direct = this.teams.get(trimmed.toLowerCase());
    if (direct) return { team: direct, candidates: [direct] };

    const normalizedInput = normalizeName(trimmed);
    for (const team of this.teams.values()) {
      if (normalizeName(team.name) === normalizedInput) return { team, candidates: [team] };
    }
    for (const team of this.teams.values()) {
      for (const alias of team.aliases) {
        if (normalizeName(alias) === normalizedInput) return { team, candidates: [team] };
      }
    }

    const parsed = parseTeamName(trimmed);
    const viaTable = this.lookupId(parsed);
    if (viaTable) {
      const team = this.teams.get(viaTable);
      if (team) return { team, candidates: [team] };
    }

    const substringHits = [...this.teams.values()].filter((team) => {
      const haystacks = [normalizeName(team.name), ...[...team.aliases].map(normalizeName)];
      return haystacks.some((h) => h.includes(parsed.base) || parsed.base.includes(h));
    });
    if (substringHits.length === 1) return { team: substringHits[0]!, candidates: substringHits };
    if (substringHits.length > 1) {
      const ranked = rankBySimilarity(substringHits, parsed.base);
      return { team: ranked[0]!, candidates: ranked.slice(0, 5) };
    }

    const ranked = rankBySimilarity([...this.teams.values()], parsed.base);
    const best = ranked[0];
    if (best && bestSimilarity(best, parsed.base) >= 0.8) {
      return { team: best, candidates: ranked.slice(0, 5) };
    }
    return { candidates: ranked.slice(0, 5) };
  }

  /**
   * Link a FIFA club label to a Brazilian club in the match data.
   *
   * Deliberately narrow. The FIFA file is worldwide, and base names collide
   * across continents -- "FC Barcelona" reduces to the same base as the
   * Ecuadorian Barcelona that plays the Libertadores, and Portugal's CD
   * Nacional collides with Uruguay's. Restricting the link to clubs that this
   * module curates *and* places in a Brazilian state keeps the player-to-match
   * join trustworthy; unlinked clubs are still fully searchable by their raw
   * label, which is all the non-Brazilian ones need.
   */
  resolveClubLabel(club: string): Team | undefined {
    const parsed = parseTeamName(club);
    if (!parsed.base) return undefined;
    const id = this.lookupId(parsed);
    if (!id) return undefined;

    const spec = this.specById.get(id);
    if (!spec?.state) return undefined;

    const team = this.teams.get(id);
    if (!team) return undefined;

    // Guard against a bare label borrowing a curated club's base while naming
    // somewhere else entirely ("Barcelona SC" vs "Bahia").
    const known = new Set(spec.bases.map((form) => parseTeamName(form).base));
    return known.has(parsed.base) ? team : undefined;
  }

  /** Named derby covering this pair of teams, if any. */
  rivalryFor(teamA: string, teamB: string): Rivalry | undefined {
    return RIVALRIES.find(
      (r) =>
        (r.teams[0] === teamA && r.teams[1] === teamB) ||
        (r.teams[0] === teamB && r.teams[1] === teamA),
    );
  }
}

function bestSimilarity(team: Team, target: string): number {
  const haystacks = [normalizeName(team.name), ...[...team.aliases].map(normalizeName)];
  return Math.max(...haystacks.map((h) => similarity(h, target)), 0);
}

function rankBySimilarity(teams: Team[], target: string): Team[] {
  return [...teams]
    .map((team) => ({ team, score: bestSimilarity(team, target) }))
    .sort((a, b) => b.score - a.score)
    .map((entry) => entry.team);
}

/** Display name for a club with no curated entry, preserving source accents. */
function displayNameFor(parsed: ParsedTeamName): string {
  if (parsed.country && parsed.country !== 'BRA') return `${parsed.display} (${parsed.country})`;
  if (parsed.state) return `${parsed.display}-${parsed.state}`;
  return parsed.display;
}

export function countryName(code: string | undefined): string {
  if (!code) return 'Brazil';
  return COUNTRY_NAMES[code] ?? code;
}
