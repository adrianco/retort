/**
 * Team-name normalisation and resolution.
 *
 * The datasets name the same club in many ways:
 *   "Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "SE Palmeiras",
 *   "Sao Paulo" / "São Paulo", "Atletico-MG" / "Atlético Mineiro",
 *   "Sport Club do Recife" / "Sport Recife" / "Sport-PE", "A.b.c. - RN" / "ABC" ...
 *
 * Every raw name is parsed into { base, state, qualifier } and then resolved to
 * a canonical team id. Well-known clubs are listed in KNOWN_CLUBS with their
 * home state so that ambiguous bases ("Atlético", "América", "Botafogo") are
 * disambiguated by state, and same-named smaller clubs from other states
 * ("Flamengo - PI", "Santos AP") stay separate.
 */
import { foldText, stripAccents } from "./normalize.js";

export const BRAZILIAN_STATES = new Set([
  "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa",
  "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
]);

/** Country qualifiers used for foreign clubs in the Libertadores file. */
const COUNTRY_CODES = new Set([
  "uru", "par", "per", "equ", "ecu", "ven", "bol", "chi", "col", "arg", "mex", "bra",
]);

const NOISE_PREFIXES = new Set(["ec", "fc", "sc", "ad", "ae", "ge", "se", "ce", "cr", "se"]);
const NOISE_SUFFIXES = [
  "futebol clube", "esporte clube", "sport club", "football club", "fc", "ec", "sc", "fr", "clube", "ltda",
];

export interface ParsedTeamName {
  /** folded base name without state / club-type noise, e.g. "sao paulo" */
  base: string;
  /** lower-case Brazilian state code, e.g. "sp" */
  state?: string;
  /** lower-case country qualifier for foreign clubs, e.g. "uru" */
  qualifier?: string;
  /** original name with state/qualifier suffix removed (accents kept) */
  displayBase: string;
}

/** Collapse runs of single letters produced by abbreviations: "c r b" -> "crb". */
function mergeInitials(s: string): string {
  const tokens = s.split(" ").filter(Boolean);
  const out: string[] = [];
  let run = "";
  for (const t of tokens) {
    if (t.length === 1 && /[a-z]/.test(t)) {
      run += t;
    } else {
      if (run) out.push(run);
      run = "";
      out.push(t);
    }
  }
  if (run) out.push(run);
  return out.join(" ");
}

function cleanBase(s: string): string {
  let b = s
    .replace(/\([^)]*\)/g, " ")
    .replace(/[.]/g, " ")
    .replace(/[-_/]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  b = mergeInitials(b);
  return b;
}

function stripNoise(b: string): string {
  let changed = true;
  while (changed) {
    changed = false;
    const parts = b.split(" ");
    if (parts.length > 1 && NOISE_PREFIXES.has(parts[0])) {
      b = parts.slice(1).join(" ");
      changed = true;
      continue;
    }
    for (const suf of NOISE_SUFFIXES) {
      if (b.endsWith(" " + suf) && b.length > suf.length + 1) {
        b = b.slice(0, b.length - suf.length - 1).trim();
        changed = true;
        break;
      }
    }
  }
  return b;
}

/** Parse a raw team name into its components. */
export function parseTeamName(raw: string): ParsedTeamName & { rawBase: string } {
  let original = raw.trim().replace(/\s+/g, " ");
  let folded = foldText(original);
  let state: string | undefined;
  let qualifier: string | undefined;

  // Trailing "(XX)" / "(XXX)"
  let m = folded.match(/\s*\(([a-z]{2,3})\)$/);
  if (m && (BRAZILIAN_STATES.has(m[1]) || COUNTRY_CODES.has(m[1]))) {
    if (BRAZILIAN_STATES.has(m[1])) state = m[1];
    else qualifier = m[1];
    folded = folded.slice(0, m.index).trim();
    original = original.slice(0, m.index).trim();
  } else {
    // Trailing "-SP", " - SP", " SP"
    m = folded.match(/(?:\s*-\s*|\s+)([a-z]{2})$/);
    if (m && BRAZILIAN_STATES.has(m[1])) {
      state = m[1];
      folded = folded.slice(0, m.index).trim();
      original = original.slice(0, m.index).trim();
    } else {
      // Trailing country code "-URU", "-EQU"
      m = folded.match(/-([a-z]{3})$/);
      if (m && COUNTRY_CODES.has(m[1])) {
        qualifier = m[1];
        folded = folded.slice(0, m.index).trim();
        original = original.slice(0, m.index).trim();
      }
    }
  }
  const rawBase = cleanBase(folded);
  const base = stripNoise(rawBase);
  return { base, rawBase, state, qualifier, displayBase: original };
}

export interface KnownClub {
  id: string;
  name: string;
  state?: string;
  /** folded alias bases (state handled separately) */
  aliases: string[];
  /** Club nickname(s) used for display, e.g. "Fla-Flu" derbies */
}

/**
 * Canonical clubs. Order matters: when a base alias is shared ("atletico",
 * "america") and no state is given, the first entry wins.
 */
export const KNOWN_CLUBS: KnownClub[] = [
  { id: "flamengo", name: "Flamengo", state: "rj", aliases: ["flamengo", "cr flamengo", "clube de regatas do flamengo", "mengao"] },
  { id: "fluminense", name: "Fluminense", state: "rj", aliases: ["fluminense", "fluminense football club"] },
  { id: "vasco", name: "Vasco da Gama", state: "rj", aliases: ["vasco", "vasco da gama", "cr vasco da gama", "club de regatas vasco da gama"] },
  { id: "botafogo", name: "Botafogo", state: "rj", aliases: ["botafogo", "botafogo de futebol e regatas"] },
  { id: "palmeiras", name: "Palmeiras", state: "sp", aliases: ["palmeiras", "sociedade esportiva palmeiras", "verdao"] },
  { id: "corinthians", name: "Corinthians", state: "sp", aliases: ["corinthians", "sport club corinthians paulista", "corinthians paulista", "timao"] },
  { id: "sao-paulo", name: "São Paulo", state: "sp", aliases: ["sao paulo", "spfc", "sao paulo futebol clube", "tricolor paulista"] },
  { id: "santos", name: "Santos", state: "sp", aliases: ["santos", "santos futebol clube", "peixe"] },
  { id: "gremio", name: "Grêmio", state: "rs", aliases: ["gremio", "gremio fbpa", "gremio foot ball porto alegrense"] },
  { id: "internacional", name: "Internacional", state: "rs", aliases: ["internacional", "inter", "sport club internacional", "colorado"] },
  { id: "cruzeiro", name: "Cruzeiro", state: "mg", aliases: ["cruzeiro", "cruzeiro esporte clube"] },
  { id: "atletico-mg", name: "Atlético Mineiro", state: "mg", aliases: ["atletico mineiro", "atletico", "clube atletico mineiro", "galo", "atletico mg"] },
  { id: "athletico-pr", name: "Athletico Paranaense", state: "pr", aliases: ["athletico paranaense", "atletico paranaense", "athletico", "atletico", "clube atletico paranaense", "furacao", "atletico pr", "athletico pr"] },
  { id: "atletico-go", name: "Atlético Goianiense", state: "go", aliases: ["atletico goianiense", "atletico", "atletico go"] },
  { id: "america-mg", name: "América Mineiro", state: "mg", aliases: ["america mineiro", "america", "america fc minas gerais", "america mg"] },
  { id: "america-rn", name: "América-RN", state: "rn", aliases: ["america de natal", "america natal", "america fc natal", "america", "america rn"] },
  { id: "bahia", name: "Bahia", state: "ba", aliases: ["bahia", "esporte clube bahia"] },
  { id: "vitoria", name: "Vitória", state: "ba", aliases: ["vitoria", "esporte clube vitoria"] },
  { id: "sport", name: "Sport Recife", state: "pe", aliases: ["sport", "sport recife", "sport club do recife", "sport club recife"] },
  { id: "nautico", name: "Náutico", state: "pe", aliases: ["nautico", "nautico capibaribe", "clube nautico capibaribe"] },
  { id: "santa-cruz", name: "Santa Cruz", state: "pe", aliases: ["santa cruz", "santa cruz futebol clube"] },
  { id: "ceara", name: "Ceará", state: "ce", aliases: ["ceara", "ceara sporting club", "ceara sporting"] },
  { id: "fortaleza", name: "Fortaleza", state: "ce", aliases: ["fortaleza", "fortaleza esporte clube"] },
  { id: "coritiba", name: "Coritiba", state: "pr", aliases: ["coritiba", "coritiba foot ball club", "coxa"] },
  { id: "parana", name: "Paraná Clube", state: "pr", aliases: ["parana", "parana clube"] },
  { id: "goias", name: "Goiás", state: "go", aliases: ["goias", "goias esporte clube"] },
  { id: "chapecoense", name: "Chapecoense", state: "sc", aliases: ["chapecoense", "associacao chapecoense de futebol", "chape"] },
  { id: "avai", name: "Avaí", state: "sc", aliases: ["avai", "avai futebol clube"] },
  { id: "figueirense", name: "Figueirense", state: "sc", aliases: ["figueirense"] },
  { id: "criciuma", name: "Criciúma", state: "sc", aliases: ["criciuma"] },
  { id: "joinville", name: "Joinville", state: "sc", aliases: ["joinville"] },
  { id: "juventude", name: "Juventude", state: "rs", aliases: ["juventude"] },
  { id: "ponte-preta", name: "Ponte Preta", state: "sp", aliases: ["ponte preta", "associacao atletica ponte preta"] },
  { id: "portuguesa", name: "Portuguesa", state: "sp", aliases: ["portuguesa", "portuguesa desportos", "associacao portuguesa de desportos"] },
  { id: "bragantino", name: "Red Bull Bragantino", state: "sp", aliases: ["red bull bragantino", "bragantino", "rb bragantino"] },
  { id: "csa", name: "CSA", state: "al", aliases: ["csa", "cs alagoano", "centro sportivo alagoano"] },
  { id: "crb", name: "CRB", state: "al", aliases: ["crb", "clube de regatas brasil"] },
  { id: "cuiaba", name: "Cuiabá", state: "mt", aliases: ["cuiaba", "cuiaba esporte clube"] },
  { id: "guarani", name: "Guarani", state: "sp", aliases: ["guarani"] },
  { id: "paysandu", name: "Paysandu", state: "pa", aliases: ["paysandu"] },
  { id: "remo", name: "Remo", state: "pa", aliases: ["remo", "clube do remo"] },
  { id: "santo-andre", name: "Santo André", state: "sp", aliases: ["santo andre"] },
  { id: "sao-caetano", name: "São Caetano", state: "sp", aliases: ["sao caetano"] },
  { id: "barueri", name: "Grêmio Barueri", state: "sp", aliases: ["barueri", "gremio barueri"] },
  { id: "abc", name: "ABC", state: "rn", aliases: ["abc"] },
  { id: "sampaio-correa", name: "Sampaio Corrêa", state: "ma", aliases: ["sampaio correa"] },
  { id: "vila-nova", name: "Vila Nova", state: "go", aliases: ["vila nova"] },
  { id: "brasiliense", name: "Brasiliense", state: "df", aliases: ["brasiliense"] },
  { id: "ipatinga", name: "Ipatinga", state: "mg", aliases: ["ipatinga"] },
  // Foreign clubs whose names appear both with and without a country qualifier.
  { id: "delfin", name: "Delfín (EQU)", aliases: ["delfin", "delfin (equ)"] },
  { id: "libertad", name: "Libertad (PAR)", aliases: ["libertad", "libertad (par)"] },
  { id: "independiente-del-valle", name: "Independiente del Valle (EQU)", aliases: ["independiente del valle"] },
];

/** Traditional derbies (clássicos) between canonical club ids. */
export const DERBIES: { name: string; teams: [string, string] }[] = [
  { name: "Fla-Flu", teams: ["flamengo", "fluminense"] },
  { name: "Clássico dos Milhões", teams: ["flamengo", "vasco"] },
  { name: "Clássico da Rivalidade", teams: ["flamengo", "botafogo"] },
  { name: "Clássico Vovô", teams: ["fluminense", "botafogo"] },
  { name: "Clássico dos Gigantes", teams: ["fluminense", "vasco"] },
  { name: "Clássico da Amizade", teams: ["botafogo", "vasco"] },
  { name: "Derby Paulista", teams: ["corinthians", "palmeiras"] },
  { name: "Majestoso", teams: ["corinthians", "sao-paulo"] },
  { name: "Choque-Rei", teams: ["palmeiras", "sao-paulo"] },
  { name: "Clássico Alvinegro", teams: ["corinthians", "santos"] },
  { name: "San-São", teams: ["santos", "sao-paulo"] },
  { name: "Clássico da Saudade", teams: ["palmeiras", "santos"] },
  { name: "Grenal", teams: ["gremio", "internacional"] },
  { name: "Clássico Mineiro", teams: ["atletico-mg", "cruzeiro"] },
  { name: "Atletiba", teams: ["athletico-pr", "coritiba"] },
  { name: "Ba-Vi", teams: ["bahia", "vitoria"] },
  { name: "Clássico-Rei (Ceará)", teams: ["ceara", "fortaleza"] },
  { name: "Clássico dos Clássicos", teams: ["sport", "nautico"] },
  { name: "Clássico das Multidões", teams: ["sport", "santa-cruz"] },
  { name: "Clássico Goiano", teams: ["goias", "atletico-go"] },
  { name: "Clássico Catarinense", teams: ["avai", "figueirense"] },
  { name: "Re-Pa", teams: ["remo", "paysandu"] },
  { name: "Clássico Alagoano", teams: ["csa", "crb"] },
];

export function derbyName(a: string, b: string): string | undefined {
  for (const d of DERBIES) {
    if ((d.teams[0] === a && d.teams[1] === b) || (d.teams[0] === b && d.teams[1] === a)) return d.name;
  }
  return undefined;
}

export interface Team {
  id: string;
  name: string;
  state?: string;
  known: boolean;
  /** Raw spellings seen in the data */
  rawNames: Set<string>;
}

type Origin = "domestic" | "international";

interface Observation {
  parsed: ReturnType<typeof parseTeamName>;
  origin: Origin;
  count: number;
}

const aliasIndex = new Map<string, KnownClub[]>();
for (const club of KNOWN_CLUBS) {
  for (const a of club.aliases) {
    const list = aliasIndex.get(a) ?? [];
    list.push(club);
    aliasIndex.set(a, list);
  }
}

function lookupKnown(base: string, state?: string, qualifier?: string): KnownClub | undefined {
  const keys = qualifier ? [`${base} (${qualifier})`] : [base];
  for (const key of keys) {
    const candidates = aliasIndex.get(key);
    if (!candidates) continue;
    if (state) {
      const hit = candidates.find((c) => c.state === state);
      if (hit) return hit;
      continue;
    }
    // Foreign-qualified names never resolve to Brazilian clubs.
    if (qualifier) return candidates.find((c) => !c.state);
    return candidates[0];
  }
  return undefined;
}

/** Remove leading/trailing club-type words ("FC", "EC", "GE") from a display name. */
function stripDisplayNoise(name: string): string {
  const words = name.split(" ");
  const isNoise = (w: string) => {
    const f = foldText(w).replace(/[.]/g, "");
    return NOISE_PREFIXES.has(f) || NOISE_SUFFIXES.includes(f);
  };
  while (words.length > 1 && isNoise(words[0])) words.shift();
  while (words.length > 1 && isNoise(words[words.length - 1])) words.pop();
  return words.join(" ");
}

function slug(s: string): string {
  return stripAccents(s).toLowerCase().replace(/[^a-z0-9()]+/g, "-").replace(/^-|-$/g, "");
}

function titleCase(s: string): string {
  return s.replace(/\b([a-zà-ÿ])([a-zà-ÿ]*)/gi, (_m, a: string, b: string) => a.toUpperCase() + b.toLowerCase());
}

/**
 * Collects every raw team name seen while loading, then assigns canonical ids.
 * Use `observe()` during loading and `finalize()` once all files are read.
 */
export class TeamRegistry {
  private observations = new Map<string, Observation>();
  private rawToId = new Map<string, string>();
  readonly teams = new Map<string, Team>();
  private finalized = false;

  observe(raw: string, origin: Origin): void {
    const key = `${origin}|${raw}`;
    const obs = this.observations.get(key);
    if (obs) {
      obs.count++;
      return;
    }
    this.observations.set(key, { parsed: parseTeamName(raw), origin, count: 1 });
  }

  /** Resolve a raw name (observed earlier) to its canonical id. */
  idFor(raw: string, origin: Origin): string {
    if (!this.finalized) throw new Error("TeamRegistry.finalize() not called");
    const id = this.rawToId.get(`${origin}|${raw}`);
    if (!id) throw new Error(`Unobserved team name: ${raw}`);
    return id;
  }

  finalize(): void {
    // 1) Unregistered domestic names: gather stateful variants per base so that
    //    "Tombense" can merge into "Tombense-MG" when it's unambiguous.
    const statesByBase = new Map<string, Set<string>>();
    for (const obs of this.observations.values()) {
      const p = obs.parsed;
      if (obs.origin !== "domestic" || !p.state) continue;
      if (lookupKnown(p.base, p.state) || lookupKnown(p.rawBase, p.state)) continue;
      const set = statesByBase.get(p.base) ?? new Set();
      set.add(p.state);
      statesByBase.set(p.base, set);
    }

    const displayVotes = new Map<string, Map<string, number>>();
    for (const [key, obs] of this.observations) {
      const p = obs.parsed;
      const known = lookupKnown(p.rawBase, p.state, p.qualifier) ?? lookupKnown(p.base, p.state, p.qualifier);
      let id: string;
      let state = p.state;
      if (known) {
        id = known.id;
        state = known.state;
      } else {
        if (!state && obs.origin === "domestic") {
          const states = statesByBase.get(p.base);
          if (states && states.size === 1) state = [...states][0];
        }
        id = slug(p.base) + (state ? `-${state}` : "") + (p.qualifier ? `-${p.qualifier}` : "");
        if (obs.origin === "international" && !p.qualifier && !state) id = `${slug(p.base)}`;
      }
      this.rawToId.set(key, id);

      let team = this.teams.get(id);
      if (!team) {
        team = { id, name: known?.name ?? "", state, known: !!known, rawNames: new Set() };
        this.teams.set(id, team);
      }
      const raw = key.slice(key.indexOf("|") + 1);
      team.rawNames.add(raw);
      if (!known) {
        const votes = displayVotes.get(id) ?? new Map<string, number>();
        let disp = stripDisplayNoise(p.displayBase.replace(/\s*\([^)]*\)\s*/g, " ").trim());
        if (p.qualifier) disp += ` (${p.qualifier.toUpperCase()})`;
        // Spellings without club-type noise ("FC", "EC", ...) get a bonus.
        const weight = obs.count + (p.rawBase === p.base ? 1_000_000 : 0);
        votes.set(disp, (votes.get(disp) ?? 0) + weight);
        displayVotes.set(id, votes);
      }
    }

    // 2) Pick a display name for unregistered teams: prefer accented, then
    //    shortest, then most frequent spelling.
    for (const [id, votes] of displayVotes) {
      const team = this.teams.get(id)!;
      const best = [...votes.entries()].sort((a, b) => {
        const cleanA = a[1] >= 1_000_000 ? 0 : 1;
        const cleanB = b[1] >= 1_000_000 ? 0 : 1;
        if (cleanA !== cleanB) return cleanA - cleanB;
        const accA = /[^\x00-\x7f]/.test(a[0]) ? 0 : 1;
        const accB = /[^\x00-\x7f]/.test(b[0]) ? 0 : 1;
        if (accA !== accB) return accA - accB;
        if (a[0].length !== b[0].length) return a[0].length - b[0].length;
        return b[1] - a[1];
      })[0][0];
      let name = best === best.toLowerCase() || best === best.toUpperCase() && best.length > 4 ? titleCase(best) : best;
      if (team.state) name += `-${team.state.toUpperCase()}`;
      team.name = name;
    }
    this.finalized = true;
  }

  get(id: string): Team | undefined {
    return this.teams.get(id);
  }

  /**
   * Resolve a free-text team query from a user. Tries exact canonical
   * resolution first, then accent-insensitive substring matching across
   * canonical names and every raw spelling. `popularity` ranks fuzzy hits.
   */
  search(query: string, popularity: (id: string) => number = () => 0): Team[] {
    const q = query.trim();
    if (!q) return [];
    const p = parseTeamName(q);
    const known = lookupKnown(p.rawBase, p.state, p.qualifier) ?? lookupKnown(p.base, p.state, p.qualifier);
    if (known && this.teams.has(known.id)) return [this.teams.get(known.id)!];

    const direct = slug(p.base) + (p.state ? `-${p.state}` : "") + (p.qualifier ? `-${p.qualifier}` : "");
    if (this.teams.has(direct)) return [this.teams.get(direct)!];
    if (this.teams.has(slug(q))) return [this.teams.get(slug(q))!];

    const fq = foldText(q);
    const hits: Team[] = [];
    for (const team of this.teams.values()) {
      if (p.state && team.state && team.state !== p.state) continue;
      const names = [team.name, ...team.rawNames].map(foldText);
      if (names.some((n) => n.includes(fq) || (p.base.length >= 3 && n.includes(p.base)))) hits.push(team);
    }
    return hits.sort((a, b) => {
      if (a.known !== b.known) return a.known ? -1 : 1;
      return popularity(b.id) - popularity(a.id);
    });
  }
}
