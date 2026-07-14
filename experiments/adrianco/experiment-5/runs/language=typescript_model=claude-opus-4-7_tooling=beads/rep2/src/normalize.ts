// Team name normalization for matching across heterogeneous CSV sources.
// Strips diacritics, state suffixes, common qualifiers, and lowercases.

const STATE_ABBREVS = new Set([
  "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
  "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
]);

// Country codes seen in Libertadores data (e.g. "Nacional (URU)", "Barcelona-EQU")
const COUNTRY_CODES = new Set([
  "ARG","URU","CHI","COL","PER","BOL","EQU","ECU","PAR","VEN","BRA",
  "MEX","USA","ESP","ITA","POR","GER","FRA","ENG",
]);

const ALIASES: Record<string, string> = {
  "atletico paranaense": "athletico paranaense",
  "atletico pr": "athletico paranaense",
  "athletico pr": "athletico paranaense",
  "atletico mineiro": "atletico mineiro",
  "atletico mg": "atletico mineiro",
  "atletico goianiense": "atletico goianiense",
  "atletico go": "atletico goianiense",
  "athletico go": "atletico goianiense",
  "sao paulo": "sao paulo",
  "sao paulo fc": "sao paulo",
  "flamengo rj": "flamengo",
  "flamengo": "flamengo",
  "palmeiras sp": "palmeiras",
  "palmeiras": "palmeiras",
  "corinthians sp": "corinthians",
  "corinthians": "corinthians",
  "fluminense rj": "fluminense",
  "fluminense": "fluminense",
  "vasco rj": "vasco",
  "vasco da gama": "vasco",
  "santos sp": "santos",
  "santos": "santos",
  "gremio rs": "gremio",
  "gremio": "gremio",
  "internacional rs": "internacional",
  "internacional": "internacional",
  "cruzeiro mg": "cruzeiro",
  "cruzeiro": "cruzeiro",
  "botafogo rj": "botafogo",
  "botafogo": "botafogo",
  "bahia ba": "bahia",
  "bahia": "bahia",
  "fortaleza ce": "fortaleza",
  "fortaleza": "fortaleza",
  "ceara ce": "ceara",
  "ceara": "ceara",
  "sport pe": "sport",
  "sport recife": "sport",
  "sport": "sport",
  "coritiba pr": "coritiba",
  "coritiba": "coritiba",
  "goias go": "goias",
  "goias": "goias",
  "vitoria ba": "vitoria",
  "vitoria": "vitoria",
};

export function stripDiacritics(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

export function normalizeTeam(raw: string | null | undefined): string {
  if (!raw) return "";
  let s = stripDiacritics(String(raw)).toLowerCase().trim();

  // Strip parenthesized qualifiers like " (uru)" / " (rj)"
  s = s.replace(/\([^)]*\)/g, " ");

  // Common qualifiers
  s = s.replace(/\b(esporte clube|sport club|clube|club|futebol clube|fc|cf|ec|sc|aa|ea|esporte)\b/g, " ");

  // Collapse separators to single spaces; normalize hyphens
  s = s.replace(/[-_/\\.,]/g, " ").replace(/\s+/g, " ").trim();

  // Drop trailing state / country code tokens (one or more)
  let tokens = s.split(" ").filter(Boolean);
  while (tokens.length > 1) {
    const last = tokens[tokens.length - 1].toUpperCase();
    if (STATE_ABBREVS.has(last) || COUNTRY_CODES.has(last)) {
      tokens.pop();
    } else {
      break;
    }
  }

  const candidate = tokens.join(" ");
  if (ALIASES[candidate]) return ALIASES[candidate];

  // Apply prefix-replacements for common spelling variants on the bare name
  // (e.g. "athletico" / "atletico" both refer to the same family of clubs in
  // Brazil; without a disambiguating state token we treat them as equivalent).
  if (tokens.length > 0) {
    const first = tokens[0];
    if (first === "athletico") tokens[0] = "atletico";
    return tokens.join(" ");
  }

  return candidate;
}

export function teamsMatch(a: string, b: string): boolean {
  if (!a || !b) return false;
  return normalizeTeam(a) === normalizeTeam(b);
}

export function normalizeQuery(q: string): string {
  return normalizeTeam(q);
}
