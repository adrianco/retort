// Team name normalisation across datasets ("Palmeiras-SP", "Palmeiras", "Sao Paulo", "São Paulo", ...).

export function stripAccents(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

const UF = new Set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split(" "));

// Canonical key aliases (applied to accent-free, lowercase, single-spaced names, with state kept).
const ALIASES: Record<string, string> = {
  "atletico mg": "atletico mineiro", "atletico mineiro": "atletico mineiro", "clube atletico mineiro": "atletico mineiro",
  "atletico go": "atletico goianiense", "atletico goianiense": "atletico goianiense",
  "atletico pr": "athletico paranaense", "athletico pr": "athletico paranaense", "atletico paranaense": "athletico paranaense",
  "athletico paranaense": "athletico paranaense", "athletico": "athletico paranaense",
  "america mg": "america mineiro", "america mineiro": "america mineiro",
  "botafogo rj": "botafogo", "vasco da gama": "vasco", "vasco da gama rj": "vasco", "cr vasco da gama": "vasco",
  "red bull bragantino": "bragantino", "rb bragantino": "bragantino", "red bull bragantino sp": "bragantino",
  "sport recife": "sport", "sport club do recife": "sport",
  "sport club corinthians paulista": "corinthians", "sc corinthians": "corinthians",
  "sociedade esportiva palmeiras": "palmeiras", "se palmeiras": "palmeiras",
  "clube de regatas do flamengo": "flamengo", "cr flamengo": "flamengo",
  "fluminense fc": "fluminense", "sao paulo fc": "sao paulo", "santos fc": "santos",
  "gremio fbpa": "gremio", "gremio foot ball porto alegrense": "gremio",
  "sc internacional": "internacional", "cruzeiro ec": "cruzeiro", "fortaleza esporte clube": "fortaleza",
  "fortaleza ec": "fortaleza", "esporte clube bahia": "bahia", "ec bahia": "bahia", "ec vitoria": "vitoria",
  "goias ec": "goias", "coritiba fc": "coritiba", "ceara sc": "ceara", "csa": "csa", "cs alagoano": "csa",
};

const DISPLAY: Record<string, string> = {
  "atletico mineiro": "Atlético-MG", "atletico goianiense": "Atlético-GO", "athletico paranaense": "Athletico-PR",
  "america mineiro": "América-MG", "sao paulo": "São Paulo", "gremio": "Grêmio", "vasco": "Vasco da Gama",
  "ceara": "Ceará", "goias": "Goiás", "avai": "Avaí", "vitoria": "Vitória", "criciuma": "Criciúma",
  "cuiaba": "Cuiabá", "parana": "Paraná", "nautico": "Náutico",
};

export function teamKey(raw: string): string {
  let s = stripAccents(raw).toLowerCase().trim();
  s = s.replace(/\(([^)]*)\)/g, (m, inner) => (/antigo/.test(inner) ? "" : m)); // drop "(antigo ...)" notes
  s = s.replace(/[-_.\/]+/g, " ").replace(/\s+/g, " ").trim();
  if (ALIASES[s]) return ALIASES[s];
  const parts = s.split(" ");
  if (parts.length > 1 && UF.has(parts[parts.length - 1].toUpperCase())) {
    const base = parts.slice(0, -1).join(" ");
    if (ALIASES[base]) return ALIASES[base];
    return base;
  }
  return s;
}

const seenDisplay = new Map<string, string>();

export function registerDisplay(raw: string): string {
  const key = teamKey(raw);
  if (DISPLAY[key]) return key;
  const cleaned = raw.replace(/\s*\(antigo[^)]*\)/i, "").replace(/\s*-\s*[A-Z]{2}$/, "").replace(/\s+[A-Z]{2}$/, "").trim();
  const prev = seenDisplay.get(key);
  // Prefer the accented (more correct Portuguese) spelling.
  if (!prev || (prev === stripAccents(prev) && cleaned !== stripAccents(cleaned))) seenDisplay.set(key, cleaned);
  return key;
}

export function displayName(key: string): string {
  return DISPLAY[key] ?? seenDisplay.get(key) ?? key;
}

// Traditional rivalries (derbies), as canonical key pairs.
export const DERBIES: [string, string, string][] = [
  ["flamengo", "fluminense", "Fla-Flu"], ["flamengo", "vasco", "Clássico dos Milhões"],
  ["flamengo", "botafogo", "Clássico da Rivalidade"], ["fluminense", "vasco", "Clássico dos Gigantes"],
  ["botafogo", "fluminense", "Clássico Vovô"], ["botafogo", "vasco", "Clássico da Amizade"],
  ["corinthians", "palmeiras", "Derby Paulista"], ["corinthians", "sao paulo", "Majestoso"],
  ["palmeiras", "sao paulo", "Choque-Rei"], ["santos", "corinthians", "Clássico Alvinegro"],
  ["santos", "palmeiras", "Clássico da Saudade"], ["santos", "sao paulo", "San-São"],
  ["gremio", "internacional", "Gre-Nal"], ["atletico mineiro", "cruzeiro", "Clássico Mineiro"],
  ["bahia", "vitoria", "Ba-Vi"], ["athletico paranaense", "coritiba", "Atletiba"],
  ["ceara", "fortaleza", "Clássico-Rei"], ["sport", "nautico", "Clássico dos Clássicos"],
];
