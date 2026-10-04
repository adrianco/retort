/**
 * Team-name normalisation.
 *
 * The datasets spell clubs in many ways: "Palmeiras-SP", "Palmeiras - SP",
 * "Palmeiras", "Sport Club Corinthians Paulista", "Atlético Paranaense - PR",
 * "Athletico", "C. R. B. - AL", "Guaraní (PAR)" ... This module turns any of
 * those spellings into a stable team key (e.g. "athletico-pr") so that matches
 * from different files can be joined, de-duplicated and queried consistently.
 *
 * Strategy:
 *   1. Strip accents/punctuation, detect a trailing Brazilian state code.
 *   2. Remove filler tokens such as "FC", "EC", "Esporte Clube".
 *   3. Look the result up in a curated table of the major Brazilian clubs
 *      (with aliases and their home state). A state suffix that contradicts
 *      the curated club's state (e.g. "Flamengo - PI") yields a distinct key.
 *   4. Anything else gets a generic key: "<base>" or "<base>-<state>".
 */

export const BR_STATES = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
  "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]);

export interface ClubInfo {
  key: string;
  name: string;
  state: string;
  aliases: string[];
}

/** Curated table of major Brazilian clubs. Aliases are compared after normalizeText(). */
export const CLUBS: ClubInfo[] = [
  { key: "flamengo", name: "Flamengo", state: "RJ", aliases: ["flamengo", "cr flamengo", "clube de regatas do flamengo"] },
  { key: "fluminense", name: "Fluminense", state: "RJ", aliases: ["fluminense", "fluminense fc"] },
  { key: "botafogo", name: "Botafogo", state: "RJ", aliases: ["botafogo", "botafogo fr"] },
  { key: "vasco", name: "Vasco da Gama", state: "RJ", aliases: ["vasco", "vasco da gama", "cr vasco da gama"] },
  { key: "palmeiras", name: "Palmeiras", state: "SP", aliases: ["palmeiras", "se palmeiras", "sociedade esportiva palmeiras"] },
  { key: "corinthians", name: "Corinthians", state: "SP", aliases: ["corinthians", "sport club corinthians paulista", "sc corinthians"] },
  { key: "santos", name: "Santos", state: "SP", aliases: ["santos", "santos fc"] },
  { key: "sao-paulo", name: "São Paulo", state: "SP", aliases: ["sao paulo", "sao paulo fc", "spfc"] },
  { key: "gremio", name: "Grêmio", state: "RS", aliases: ["gremio", "gremio fbpa", "gremio foot ball porto alegrense"] },
  { key: "internacional", name: "Internacional", state: "RS", aliases: ["internacional", "sc internacional", "inter"] },
  { key: "atletico-mg", name: "Atlético Mineiro", state: "MG", aliases: ["atletico mg", "atletico mineiro", "clube atletico mineiro", "galo"] },
  { key: "athletico-pr", name: "Athletico Paranaense", state: "PR", aliases: ["athletico", "athletico pr", "athletico paranaense", "atletico pr", "atletico paranaense", "club athletico paranaense"] },
  { key: "atletico-go", name: "Atlético Goianiense", state: "GO", aliases: ["atletico go", "atletico goianiense"] },
  { key: "cruzeiro", name: "Cruzeiro", state: "MG", aliases: ["cruzeiro", "cruzeiro ec"] },
  { key: "america-mg", name: "América Mineiro", state: "MG", aliases: ["america mg", "america mineiro", "america fc minas gerais"] },
  { key: "america-rn", name: "América de Natal", state: "RN", aliases: ["america rn", "america fc natal", "america de natal"] },
  { key: "bahia", name: "Bahia", state: "BA", aliases: ["bahia", "ec bahia"] },
  { key: "vitoria", name: "Vitória", state: "BA", aliases: ["vitoria", "ec vitoria"] },
  { key: "sport", name: "Sport Recife", state: "PE", aliases: ["sport", "sport recife", "sport club do recife"] },
  { key: "nautico", name: "Náutico", state: "PE", aliases: ["nautico", "nautico capibaribe", "clube nautico capibaribe"] },
  { key: "santa-cruz", name: "Santa Cruz", state: "PE", aliases: ["santa cruz"] },
  { key: "ceara", name: "Ceará", state: "CE", aliases: ["ceara", "ceara sporting club", "ceara sc"] },
  { key: "fortaleza", name: "Fortaleza", state: "CE", aliases: ["fortaleza", "fortaleza ec", "fortaleza esporte clube"] },
  { key: "goias", name: "Goiás", state: "GO", aliases: ["goias", "goias ec"] },
  { key: "coritiba", name: "Coritiba", state: "PR", aliases: ["coritiba", "coritiba fbc"] },
  { key: "parana", name: "Paraná", state: "PR", aliases: ["parana", "parana clube"] },
  { key: "chapecoense", name: "Chapecoense", state: "SC", aliases: ["chapecoense", "associacao chapecoense"] },
  { key: "avai", name: "Avaí", state: "SC", aliases: ["avai"] },
  { key: "figueirense", name: "Figueirense", state: "SC", aliases: ["figueirense"] },
  { key: "criciuma", name: "Criciúma", state: "SC", aliases: ["criciuma"] },
  { key: "joinville", name: "Joinville", state: "SC", aliases: ["joinville"] },
  { key: "juventude", name: "Juventude", state: "RS", aliases: ["juventude", "ec juventude"] },
  { key: "ponte-preta", name: "Ponte Preta", state: "SP", aliases: ["ponte preta", "aa ponte preta"] },
  { key: "portuguesa", name: "Portuguesa", state: "SP", aliases: ["portuguesa", "portuguesa desportos"] },
  { key: "guarani", name: "Guarani", state: "SP", aliases: ["guarani"] },
  { key: "bragantino", name: "Red Bull Bragantino", state: "SP", aliases: ["bragantino", "red bull bragantino", "rb bragantino"] },
  { key: "cuiaba", name: "Cuiabá", state: "MT", aliases: ["cuiaba"] },
  { key: "csa", name: "CSA", state: "AL", aliases: ["csa", "cs alagoano"] },
  { key: "crb", name: "CRB", state: "AL", aliases: ["crb"] },
  { key: "sao-caetano", name: "São Caetano", state: "SP", aliases: ["sao caetano"] },
  { key: "santo-andre", name: "Santo André", state: "SP", aliases: ["santo andre"] },
  { key: "barueri", name: "Grêmio Barueri", state: "SP", aliases: ["barueri", "gremio barueri"] },
  { key: "gremio-prudente", name: "Grêmio Prudente", state: "SP", aliases: ["gremio prudente"] },
  { key: "paysandu", name: "Paysandu", state: "PA", aliases: ["paysandu"] },
  { key: "remo", name: "Remo", state: "PA", aliases: ["remo", "clube do remo"] },
  { key: "ipatinga", name: "Ipatinga", state: "MG", aliases: ["ipatinga"] },
  { key: "brasiliense", name: "Brasiliense", state: "DF", aliases: ["brasiliense"] },
  { key: "novorizontino", name: "Novorizontino", state: "SP", aliases: ["novorizontino", "gremio novorizontino"] },
];

export const CLUB_BY_KEY = new Map(CLUBS.map((c) => [c.key, c]));

/** alias -> club. Aliases with an embedded state ("atletico mg") are explicit. */
const ALIAS_INDEX = new Map<string, ClubInfo>();
for (const club of CLUBS) for (const a of club.aliases) ALIAS_INDEX.set(a, club);

/** Remove diacritics (São -> Sao, Grêmio -> Gremio, Avaí -> Avai, ç -> c). */
export function stripAccents(s: string): string {
  return s.normalize("NFD").replace(/\p{M}/gu, "");
}

/**
 * Lower-case, accent-free, punctuation-free text with single spaces.
 * Runs of single letters ("c r b", from "C. R. B.") are joined ("crb").
 */
export function normalizeText(s: string): string {
  const tokens = stripAccents(s)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean);
  const out: string[] = [];
  let run = "";
  for (const t of tokens) {
    if (t.length === 1 && /[a-z]/.test(t)) {
      run += t;
      continue;
    }
    if (run) {
      out.push(run);
      run = "";
    }
    out.push(t);
  }
  if (run) out.push(run);
  return out.join(" ");
}

const LEADING_FILLER = new Set(["ec", "fc", "sc", "ca", "ad", "ae", "ce", "ge", "se", "cr", "aa", "clube", "club"]);
const TRAILING_FILLER = ["esporte clube", "futebol clube", "fc", "ec", "sc", "clube", "club"];

function stripFiller(base: string): string {
  let tokens = base.split(" ");
  while (tokens.length > 1 && LEADING_FILLER.has(tokens[0])) tokens = tokens.slice(1);
  let s = tokens.join(" ");
  let changed = true;
  while (changed) {
    changed = false;
    for (const f of TRAILING_FILLER) {
      if (s.endsWith(" " + f) && s.length > f.length + 1) {
        s = s.slice(0, -(f.length + 1));
        changed = true;
      }
    }
  }
  return s;
}

export interface ParsedTeam {
  /** Normalised base name without state or filler, e.g. "sao paulo". */
  base: string;
  /** Brazilian state code if one was present, e.g. "SP". */
  state?: string;
  /** Stable team key, e.g. "sao-paulo", "flamengo-pi", "nacional-uru". */
  key: string;
  /** Curated club, when the name refers to one of the major clubs. */
  club?: ClubInfo;
  /** Raw name with any state suffix removed (keeps accents), for display. */
  displayBase: string;
}

/** Spelling variants of foreign (Libertadores) clubs that appear in the data. */
const FOREIGN_ALIASES: Record<string, { key: string; name: string }> = {
  "libertad par": { key: "libertad", name: "Libertad" },
  "delfin equ": { key: "delfin", name: "Delfín" },
  "barcelona equ": { key: "barcelona-sc", name: "Barcelona SC (Ecuador)" },
  "independiente del valle": { key: "independiente-del-valle", name: "Independiente del Valle" },
  "olimpia par": { key: "olimpia", name: "Olimpia" },
};

const slug = (s: string) => s.replace(/\s+/g, "-");

/** Parse any dataset/user spelling of a team into a stable key. */
export function parseTeamName(raw: string): ParsedTeam {
  let name = raw.trim();

  // "Nacional (URU)" -> "Nacional URU"; drop long explanatory parentheticals
  // such as "(antigo Esporte Clube Barreira)", but keep "(Minas Gerais)" style
  // qualifiers for alias lookup by trying the full text first.
  const fullNorm = normalizeText(name);
  const fullAlias = ALIAS_INDEX.get(fullNorm);
  if (fullAlias && !/[-\s]([A-Z]{2})$/.test(name)) {
    return { base: fullNorm, key: fullAlias.key, club: fullAlias, state: fullAlias.state, displayBase: fullAlias.name };
  }
  name = name.replace(/\(([^)]*)\)/g, (_m, inner: string) => (inner.trim().length <= 4 ? ` ${inner} ` : " ")).trim();

  let state: string | undefined;
  const m = /^(.*?)\s*(?:-|\s)\s*([A-Z]{2})$/.exec(stripAccents(name));
  if (m && BR_STATES.has(m[2]) && m[1].trim().length > 0) {
    state = m[2];
    // Cut the same number of characters off the accented original.
    name = name.slice(0, m[1].length).trim().replace(/[-\s]+$/, "");
  }
  const displayBase = name.replace(/\s+/g, " ").trim();
  const base = stripFiller(normalizeText(name));

  // Explicit "<alias> <state>" aliases (e.g. "atletico mg").
  if (state) {
    const explicit = ALIAS_INDEX.get(`${base} ${state.toLowerCase()}`);
    if (explicit) return { base, state, key: explicit.key, club: explicit, displayBase };
  }
  const club = ALIAS_INDEX.get(base) ?? ALIAS_INDEX.get(normalizeText(name));
  if (club && (!state || state === club.state)) {
    return { base, state: club.state, key: club.key, club, displayBase };
  }
  const foreign = FOREIGN_ALIASES[base];
  if (foreign && !state) return { base, key: foreign.key, displayBase: foreign.name };
  const key = state ? `${slug(base)}-${state.toLowerCase()}` : slug(base);
  return { base, state, key, displayBase };
}

/** Pretty display name for a key (curated name, else title-cased raw name). */
export function clubDisplayName(key: string): string | undefined {
  return CLUB_BY_KEY.get(key)?.name;
}

// ---------------------------------------------------------------------------
// Traditional rivalries ("clássicos"), used for derby queries.
// ---------------------------------------------------------------------------

export interface Rivalry {
  name: string;
  teams: [string, string];
}

export const RIVALRIES: Rivalry[] = [
  { name: "Fla-Flu", teams: ["flamengo", "fluminense"] },
  { name: "Clássico dos Milhões", teams: ["flamengo", "vasco"] },
  { name: "Clássico da Rivalidade", teams: ["flamengo", "botafogo"] },
  { name: "Clássico Vovô", teams: ["fluminense", "botafogo"] },
  { name: "Clássico dos Gigantes", teams: ["fluminense", "vasco"] },
  { name: "Clássico da Amizade", teams: ["vasco", "botafogo"] },
  { name: "Derby Paulista", teams: ["corinthians", "palmeiras"] },
  { name: "Choque-Rei", teams: ["palmeiras", "sao-paulo"] },
  { name: "Majestoso", teams: ["corinthians", "sao-paulo"] },
  { name: "San-São", teams: ["santos", "sao-paulo"] },
  { name: "Clássico Alvinegro", teams: ["corinthians", "santos"] },
  { name: "Clássico da Saudade", teams: ["palmeiras", "santos"] },
  { name: "Grenal", teams: ["gremio", "internacional"] },
  { name: "Clássico Mineiro", teams: ["atletico-mg", "cruzeiro"] },
  { name: "Atletiba", teams: ["athletico-pr", "coritiba"] },
  { name: "Ba-Vi", teams: ["bahia", "vitoria"] },
  { name: "Clássico-Rei", teams: ["ceara", "fortaleza"] },
  { name: "Clássico dos Clássicos", teams: ["sport", "nautico"] },
  { name: "Clássico das Multidões", teams: ["sport", "santa-cruz"] },
  { name: "Clássico das Emoções", teams: ["nautico", "santa-cruz"] },
  { name: "Re-Pa", teams: ["remo", "paysandu"] },
  { name: "Derby Campineiro", teams: ["guarani", "ponte-preta"] },
  { name: "Clássico da Ilha", teams: ["avai", "figueirense"] },
  { name: "Derby Goiano", teams: ["goias", "atletico-go"] },
];

export function findRivalry(a: string, b: string): Rivalry | undefined {
  return RIVALRIES.find((r) => (r.teams[0] === a && r.teams[1] === b) || (r.teams[0] === b && r.teams[1] === a));
}
