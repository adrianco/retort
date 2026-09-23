export function stripAccents(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/** Bases shared by several clubs; these keep their state suffix as disambiguator. */
const AMBIGUOUS = new Set(["atletico", "america", "botafogo", "bragantino", "sao jose", "sao raimundo", "sao francisco", "operario", "guarani", "nacional", "juventude"]);

/** Full/alternate names -> canonical base (optionally with state). */
const ALIASES: Record<string, string> = {
  "atletico mineiro": "atletico-mg",
  "atletico paranaense": "atletico-pr",
  "athletico": "atletico",
  "athletico paranaense": "atletico-pr",
  "atletico goianiense": "atletico-go",
  "america de natal": "america-rn",
  "america fc natal": "america-rn",
  "vasco da gama": "vasco",
  "cr vasco da gama": "vasco",
  "red bull bragantino": "bragantino-sp",
  "sport recife": "sport",
  "sport club do recife": "sport",
  "sao paulo fc": "sao paulo",
  "sc corinthians paulista": "corinthians",
  "sport club corinthians paulista": "corinthians",
  "se palmeiras": "palmeiras",
  "sociedade esportiva palmeiras": "palmeiras",
  "cr flamengo": "flamengo",
  "clube de regatas do flamengo": "flamengo",
  "fluminense fc": "fluminense",
  "santos fc": "santos",
  "gremio fbpa": "gremio",
  "sc internacional": "internacional",
  "cruzeiro ec": "cruzeiro",
  "ec bahia": "bahia",
  "ec vitoria": "vitoria",
  "fortaleza esporte clube": "fortaleza",
  "fortaleza ec": "fortaleza",
  "ceara sc": "ceara",
  "portuguesa desportos": "portuguesa",
  "csa": "csa",
  "fla": "flamengo",
  "flu": "fluminense",
  "timao": "corinthians",
  "verdao": "palmeiras",
  "tricolor paulista": "sao paulo",
  "galo": "atletico-mg",
};

// Clubs whose unsuffixed name refers to the big club in national competitions.
const DEFAULT_STATE: Record<string, string> = {
  botafogo: "rj", bragantino: "sp", guarani: "sp", juventude: "rs",
};

/**
 * Normalize a team name to a canonical key, e.g.
 * "Palmeiras-SP" / "Palmeiras" / "SE Palmeiras" -> "palmeiras";
 * "Atlético - MG" / "Atletico Mineiro" -> "atletico-mg".
 */
export function normalizeTeam(raw: string): string {
  let s = raw.replace(/\(.*?\)/g, " ").trim();
  let state = "";
  const m = s.match(/^(.*?)(?:\s*-\s*|\s+)([A-Z]{2,3})$/);
  if (m && !/^(FC|EC|SC|AC|CR|SE)$/.test(m[2])) { s = m[1]; state = m[2].toLowerCase(); }
  let base = stripAccents(s).toLowerCase().replace(/[.']/g, "").replace(/\s+/g, " ").trim();
  if (ALIASES[base]) base = ALIASES[base];
  else {
    base = base.replace(/^(?:(?:ec|fc|sc|ac|ad|cr|se|aa|ca|cse|ee)\s+)+|(?:\s+(?:ec|fc|sc|ac|ad|cr|se|aa|ca|fbpa))+$/g, "").trim();
    if (ALIASES[base]) base = ALIASES[base];
  }
  if (base.includes("-")) return base;
  if (AMBIGUOUS.has(base)) {
    const st = state || DEFAULT_STATE[base];
    if (st && DEFAULT_STATE[base] === st) return base;
    return st ? `${base}-${st}` : base;
  }
  return base;
}

/** Does a record's team key match a (normalized) query key? "atletico" matches "atletico-mg". */
export function teamMatches(recordKey: string, queryKey: string): boolean {
  return recordKey === queryKey || recordKey.startsWith(queryKey + "-");
}

/** Display name: strip state suffix / parentheticals, keep accents. */
export function displayTeam(raw: string): string {
  return raw.replace(/\(.*?\)/g, " ").replace(/(?:\s*-\s*|\s+)[A-Z]{2,3}$/, "").replace(/\s+/g, " ").trim();
}

const MONTHS: Record<string, string> = { jan: "01", feb: "02", mar: "03", apr: "04", may: "05", jun: "06", jul: "07", aug: "08", sep: "09", oct: "10", nov: "11", dec: "12" };

/** Parse ISO, ISO+time, DD/MM/YYYY or "Mon D, YYYY" into YYYY-MM-DD ("" if unknown). */
export function parseDate(raw: string): string {
  const s = (raw ?? "").trim();
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  m = s.match(/^([A-Za-z]{3})\w* (\d{1,2}), (\d{4})/);
  if (m && MONTHS[m[1].toLowerCase()]) return `${m[3]}-${MONTHS[m[1].toLowerCase()]}-${m[2].padStart(2, "0")}`;
  return "";
}
