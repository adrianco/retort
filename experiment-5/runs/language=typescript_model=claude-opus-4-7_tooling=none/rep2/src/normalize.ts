// Normalize team names so the same club matches across files,
// regardless of state suffixes, accents, full-name vs short-name, etc.

const STATE_SUFFIX_RE = /[-\s]+(AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO|UF|EQU|URU|ARG|COL|PAR|CHI|BOL|MEX|VEN|PER)$/i;

// Map of synonyms / alternate names → canonical short name
const SYNONYM_MAP: Record<string, string> = {
  "atletico mineiro": "atletico-mg",
  "atletico-mg": "atletico-mg",
  "atletico mg": "atletico-mg",
  "clube atletico mineiro": "atletico-mg",
  "atletico paranaense": "athletico-pr",
  "athletico paranaense": "athletico-pr",
  "athletico-pr": "athletico-pr",
  "athletico pr": "athletico-pr",
  "atletico-pr": "athletico-pr",
  "atletico goianiense": "atletico-go",
  "atletico-go": "atletico-go",
  "atletico go": "atletico-go",
  "america-mg": "america-mg",
  "america mg": "america-mg",
  "america mineiro": "america-mg",
  "america-rn": "america-rn",
  "america rn": "america-rn",
  "flamengo": "flamengo",
  "clube de regatas do flamengo": "flamengo",
  "fluminense": "fluminense",
  "fluminense football club": "fluminense",
  "vasco": "vasco da gama",
  "vasco da gama": "vasco da gama",
  "club de regatas vasco da gama": "vasco da gama",
  "botafogo": "botafogo",
  "botafogo de futebol e regatas": "botafogo",
  "botafogo-rj": "botafogo",
  "palmeiras": "palmeiras",
  "se palmeiras": "palmeiras",
  "sociedade esportiva palmeiras": "palmeiras",
  "santos": "santos",
  "santos fc": "santos",
  "santos futebol clube": "santos",
  "sao paulo": "sao paulo",
  "sao paulo fc": "sao paulo",
  "sao paulo futebol clube": "sao paulo",
  "corinthians": "corinthians",
  "sport club corinthians paulista": "corinthians",
  "gremio": "gremio",
  "gremio fbpa": "gremio",
  "internacional": "internacional",
  "sport club internacional": "internacional",
  "inter": "internacional",
  "cruzeiro": "cruzeiro",
  "cruzeiro ec": "cruzeiro",
  "bahia": "bahia",
  "ec bahia": "bahia",
  "fortaleza": "fortaleza",
  "fortaleza ec": "fortaleza",
  "ceara": "ceara",
  "ceara sc": "ceara",
  "vitoria": "vitoria",
  "ec vitoria": "vitoria",
  "sport": "sport recife",
  "sport recife": "sport recife",
  "coritiba": "coritiba",
  "coritiba fc": "coritiba",
  "goias": "goias",
  "goias ec": "goias",
  "avai": "avai",
  "chapecoense": "chapecoense",
  "ponte preta": "ponte preta",
  "aa ponte preta": "ponte preta",
  "guarani": "guarani",
  "portuguesa": "portuguesa",
  "associacao portuguesa de desportos": "portuguesa",
  "figueirense": "figueirense",
  "nautico": "nautico",
  "criciuma": "criciuma",
  "bragantino": "bragantino",
  "red bull bragantino": "bragantino",
  "rb bragantino": "bragantino",
  "athletico paranaense - pr": "athletico-pr",
};

export function stripAccents(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

export function normalizeTeam(name: string | undefined | null): string {
  if (!name) return "";
  let s = String(name).trim();
  // Strip wrapped quotes if any survived parsing
  s = s.replace(/^"+|"+$/g, "").trim();
  // Strip explicit parenthesized country codes like "Nacional (URU)"
  s = s.replace(/\s*\([^)]*\)\s*/g, " ").trim();
  // Lowercase & strip accents for comparison
  let key = stripAccents(s.toLowerCase());
  key = key.replace(/[.,]/g, "").replace(/\s+/g, " ").trim();
  // Synonym lookup BEFORE stripping the trailing state suffix
  // so e.g. "Athletico-PR" resolves to "athletico-pr" instead of "athletico".
  if (SYNONYM_MAP[key]) return SYNONYM_MAP[key];
  // Otherwise drop trailing state-like suffix and try again
  key = key.replace(STATE_SUFFIX_RE, "").trim();
  key = key.replace(/\s+/g, " ").trim();
  if (SYNONYM_MAP[key]) return SYNONYM_MAP[key];
  return key;
}

export function teamMatches(needle: string, hay: string): boolean {
  const n = normalizeTeam(needle);
  const h = normalizeTeam(hay);
  if (!n || !h) return false;
  if (n === h) return true;
  return h.includes(n) || n.includes(h);
}

export function extractStateSuffix(name: string): string | null {
  const m = STATE_SUFFIX_RE.exec(stripAccents(name).trim());
  return m ? m[1].toUpperCase() : null;
}
