const BRAZILIAN_STATES = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
  "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]);

const TEAM_ALIASES: Record<string, string> = {
  "atletico mineiro": "atletico mineiro",
  "clube atletico mineiro": "atletico mineiro",
  "atletico mg": "atletico mineiro",
  "atletico mineiro mg": "atletico mineiro",
  "athletico paranaense": "athletico paranaense",
  "atletico paranaense": "athletico paranaense",
  "athletico pr": "athletico paranaense",
  "atletico pr": "athletico paranaense",
  "atletico go": "atletico goianiense",
  "atletico goianiense": "atletico goianiense",
  "corinthians paulista": "corinthians",
  "sport club corinthians paulista": "corinthians",
  "corinthians sp": "corinthians",
  "ec bahia": "bahia",
  "esporte clube bahia": "bahia",
  "ceara sc": "ceara",
  "ceara sporting club": "ceara",
  "fortaleza ec": "fortaleza",
  "fortaleza fc": "fortaleza",
  "fortaleza esporte clube": "fortaleza",
  "goias ec": "goias",
  "goias esporte clube": "goias",
  "ec juventude": "juventude",
  "esporte clube juventude": "juventude",
  "sport recife": "sport",
  "sport club do recife": "sport",
  "sao paulo fc": "sao paulo",
  "sao paulo futebol clube": "sao paulo",
  "flamengo rj": "flamengo",
  "clube de regatas do flamengo": "flamengo",
  "fluminense football club": "fluminense",
  "gremio foot ball porto alegrense": "gremio",
  "gremio fbpa": "gremio",
  "internacional porto alegre": "internacional",
  "sport club internacional": "internacional",
  "vasco da gama": "vasco",
  "club de regatas vasco da gama": "vasco",
  "cr vasco da gama": "vasco",
  "red bull bragantino": "bragantino",
  "rb bragantino": "bragantino",
  "america mineiro": "america mg",
  "america mg": "america mg",
};

const PREFERRED_TEAM_NAMES: Record<string, string> = {
  "atletico mineiro": "Atlético Mineiro",
  "athletico paranaense": "Athletico Paranaense",
  "america mg": "América Mineiro",
  "corinthians": "Corinthians",
  "sao paulo": "São Paulo",
  "flamengo": "Flamengo",
  "fluminense": "Fluminense",
  "gremio": "Grêmio",
  "internacional": "Internacional",
  "vasco": "Vasco da Gama",
  "bragantino": "Red Bull Bragantino",
};

export function foldText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/&/g, " e ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function stripTeamQualifier(value: string): string {
  let cleaned = value.trim();
  const stateMatch = cleaned.match(/(?:\s*-\s*|\s+)([A-Z]{2})$/i);
  if (stateMatch?.[1] && BRAZILIAN_STATES.has(stateMatch[1].toUpperCase())) {
    cleaned = cleaned.slice(0, stateMatch.index).trim();
  }
  return cleaned.replace(/\s+\((?:antigo|formerly)[^)]+\)\s*/gi, " ").trim();
}

export function teamKey(value: string): string {
  const qualifiedAlias = TEAM_ALIASES[foldText(value)];
  if (qualifiedAlias) return qualifiedAlias;
  const folded = foldText(stripTeamQualifier(value));
  return TEAM_ALIASES[folded] ?? folded;
}

export function displayTeamName(value: string): string {
  const key = teamKey(value);
  return PREFERRED_TEAM_NAMES[key] ?? stripTeamQualifier(value).trim();
}

export function competitionKey(value: string): string {
  return foldText(value)
    .replace(/serie a/g, "")
    .replace(/campeonato/g, "")
    .replace(/copa/g, "")
    .trim();
}

export function normalizeCompetition(value: string): string {
  const key = foldText(value);
  if (key.includes("libertadores")) return "Copa Libertadores";
  if (key.includes("copa do brasil")) return "Copa do Brasil";
  if (key.includes("brasileir") || key.includes("serie a")) return "Brasileirão Série A";
  return value.trim();
}

export function parseDate(value: string): string | null {
  const raw = value.trim();
  const brazilian = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (brazilian) {
    const [, day, month, year] = brazilian;
    return `${year}-${month!.padStart(2, "0")}-${day!.padStart(2, "0")}`;
  }
  const iso = raw.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (iso) {
    const [, year, month, day] = iso;
    return `${year}-${month!.padStart(2, "0")}-${day!.padStart(2, "0")}`;
  }
  return null;
}

export function optionalNumber(value: unknown): number | undefined {
  if (value === undefined || value === null || value === "") return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

export function requiredNumber(value: unknown): number | null {
  const number = optionalNumber(value);
  return number === undefined ? null : number;
}

export function matchesTeam(candidateKey: string, query: string): boolean {
  const queryKey = teamKey(query);
  return candidateKey === queryKey ||
    (queryKey.length >= 4 && (candidateKey.includes(queryKey) || queryKey.includes(candidateKey)));
}

export function matchesCompetition(candidate: string, query: string): boolean {
  const left = competitionKey(candidate);
  const right = competitionKey(query);
  return left === right || left.includes(right) || right.includes(left);
}
