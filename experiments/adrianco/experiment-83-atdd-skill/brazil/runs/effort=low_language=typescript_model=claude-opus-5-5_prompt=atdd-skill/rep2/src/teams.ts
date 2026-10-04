// Team-name normalisation across datasets with differing conventions.
const AMBIGUOUS = new Set(["atletico", "botafogo", "america", "athletico"]);

const ALIASES: Record<string, string> = {
  "atletico mineiro": "atletico-mg",
  "atletico paranaense": "atletico-pr",
  "athletico paranaense": "atletico-pr",
  "athletico-pr": "atletico-pr",
  "athletico": "atletico-pr",
  "atletico goianiense": "atletico-go",
  "america mineiro": "america-mg",
  "sport club corinthians paulista": "corinthians",
  "sc corinthians paulista": "corinthians",
  "vasco da gama": "vasco",
  "cr vasco da gama": "vasco",
  "sao paulo fc": "sao paulo",
  "red bull bragantino": "bragantino",
  "rb bragantino": "bragantino",
  "gremio fbpa": "gremio",
  "sport recife": "sport",
  "ceara sc": "ceara",
  "goias ec": "goias",
};

export function stripAccents(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/** Canonical key for a team name, e.g. "Palmeiras-SP" / "Palmeiras" -> "palmeiras". */
export function teamKey(raw: string): string {
  let s = stripAccents(raw).toLowerCase().trim();
  s = s.replace(/\(.*?\)/g, " ").replace(/\s+/g, " ").trim();
  let state = "";
  const m = s.match(/^(.*?)(\s*-\s*|\s+)([a-z]{2})$/);
  if (m && (m[2].includes("-") || !["fc", "ec", "sc", "ac"].includes(m[3]))) { s = m[1].trim(); state = m[3]; }
  s = s.replace(/\s+(fc|ec|sc|fbpa)$/, "").replace(/^(ec|sc|fc|se|cr|ca|ac) /, "").trim();
  if (ALIASES[s]) return ALIASES[s];
  const withState = state ? `${s}-${state}` : s;
  if (ALIASES[withState]) return ALIASES[withState];
  if (AMBIGUOUS.has(s) && state) return `${s === "athletico" ? "atletico" : s}-${state}`;
  return s;
}

/** Does a team (canonical key) match a user's query? */
export function teamMatches(key: string, query: string): boolean {
  const q = teamKey(query);
  return key === q || key.startsWith(q + "-");
}

const displayNames = new Map<string, string>();

export function displayName(key: string): string {
  return displayNames.get(key) ?? key;
}

export function registerDisplay(raw: string): string {
  const key = teamKey(raw);
  // Keep the state suffix where the bare name is ambiguous (Atlético-MG vs Atlético-GO).
  let clean = raw.replace(/\(.*?\)/g, "").trim();
  clean = key.includes("-") ? clean.replace(/\s*-\s*([A-Z]{2})$/, "-$1") : clean.replace(/\s*-\s*[A-Z]{2}$/, "");
  if (key.includes("-") && !/-[A-Z]{2}$/.test(clean) && clean.split(" ").length < 2) clean = `${clean}-${key.slice(-2).toUpperCase()}`;
  const cur = displayNames.get(key);
  const accented = (x: string) => x !== stripAccents(x);
  const upper = (x: string) => (x.match(/[A-Z]/g) ?? []).length;
  const better = !cur || (accented(clean) && !accented(cur)) || (accented(clean) === accented(cur) && upper(clean) > upper(cur) && clean.length <= cur.length);
  if (better) displayNames.set(key, clean);
  return key;
}
