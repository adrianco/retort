/** Team-name and date normalization across the heterogeneous datasets. */

const UFS = new Set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split(" "));

/** Clubs whose name is shared across states, so the state suffix must be kept. */
const AMBIGUOUS = new Set(["botafogo", "atletico", "america", "athletico", "boavista", "bragantino", "confianca", "caxias", "campinense", "aparecidense", "caldense", "brasil", "operario", "nacional", "juventus", "ypiranga", "sao bento", "real", "ferroviario", "sampaio correa", "palmas"]);

const ALIASES: Record<string, string> = {
  "athletico paranaense": "athletico pr",
  "atletico paranaense": "athletico pr",
  "atletico pr": "athletico pr",
  "athletico": "athletico pr",
  "atletico mineiro": "atletico mg",
  "atletico goianiense": "atletico go",
  "america mineiro": "america mg",
  "america fc natal": "america rn",
  "vasco da gama": "vasco",
  "cr vasco da gama": "vasco",
  "sport recife": "sport",
  "sport club do recife": "sport",
  "sport club corinthians paulista": "corinthians",
  "sc corinthians paulista": "corinthians",
  "sociedade esportiva palmeiras": "palmeiras",
  "se palmeiras": "palmeiras",
  "sao paulo fc": "sao paulo",
  "sao paulo futebol clube": "sao paulo",
  "clube de regatas do flamengo": "flamengo",
  "cr flamengo": "flamengo",
  "fluminense fc": "fluminense",
  "gremio fbpa": "gremio",
  "gremio foot ball porto alegrense": "gremio",
  "sc internacional": "internacional",
  "santos fc": "santos",
  "cruzeiro ec": "cruzeiro",
  "red bull bragantino": "bragantino sp",
  "rb bragantino": "bragantino sp",
  "bragantino": "bragantino sp",
  "botafogo": "botafogo rj",
  "ec bahia": "bahia",
  "ec vitoria": "vitoria",
  "clube do remo": "remo",
  "fla": "flamengo",
  "flu": "fluminense",
};

export function stripAccents(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/** Canonical comparison key for a team name, e.g. "Palmeiras-SP" -> "palmeiras". */
export function teamKey(name: string): string {
  let s = stripAccents(name).toLowerCase();
  s = s.replace(/\(.*?\)/g, " ").replace(/[^a-z0-9]+/g, " ").trim().replace(/\s+/g, " ");
  if (ALIASES[s]) return ALIASES[s];
  const parts = s.split(" ");
  const last = parts[parts.length - 1].toUpperCase();
  if (parts.length > 1 && UFS.has(last)) {
    const base = parts.slice(0, -1).join(" ");
    if (AMBIGUOUS.has(base)) return s;
    return ALIASES[base] ?? base;
  }
  return s;
}

/** Remove state suffixes for display: "Palmeiras-SP" -> "Palmeiras", keeps "Botafogo-RJ". */
export function displayName(name: string): string {
  const m = name.match(/^(.*?)(?:\s*-\s*|\s+)([A-Z]{2})$/);
  if (m && UFS.has(m[2]) && !AMBIGUOUS.has(teamKey(m[1]))) return m[1].trim();
  return name.trim();
}

/** True if the team key matches a user query (exact or whole-word prefix). */
export function teamMatches(key: string, query: string): boolean {
  const q = teamKey(query);
  if (!q) return false;
  if (key === q) return true;
  return (" " + key + " ").includes(" " + q + " ");
}

/** Parse "2023-09-24", "2012-05-19 18:30:00" or "29/03/2003" into ISO date "YYYY-MM-DD". */
export function parseDate(s: string): string {
  s = (s || "").trim();
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  return "";
}
