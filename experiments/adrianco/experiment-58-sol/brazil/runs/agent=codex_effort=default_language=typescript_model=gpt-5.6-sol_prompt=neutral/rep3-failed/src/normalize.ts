const TEAM_ALIASES: Record<string, string> = {
  "clube de regatas do flamengo": "flamengo",
  "flamengo futebol clube": "flamengo",
  "fluminense football club": "fluminense",
  "sociedade esportiva palmeiras": "palmeiras",
  "sport club corinthians paulista": "corinthians",
  "sao paulo futebol clube": "sao paulo",
  "santos futebol clube": "santos",
  "club de regatas vasco da gama": "vasco",
  "vasco da gama": "vasco",
  "gremio foot ball porto alegrense": "gremio",
  "sport club internacional": "internacional",
  "clube atletico mineiro": "atletico mineiro",
  "atletico": "atletico mineiro",
  "clube atletico paranaense": "athletico paranaense",
  "atletico paranaense": "athletico paranaense",
  "athletico": "athletico paranaense",
  "ec bahia": "bahia",
  "esporte clube bahia": "bahia",
  "fortaleza fc": "fortaleza",
  "fortaleza esporte clube": "fortaleza",
  "botafogo de futebol e regatas": "botafogo",
  "cruzeiro esporte clube": "cruzeiro"
};

export function foldText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/^\uFEFF/, "")
    .toLocaleLowerCase("pt-BR")
    .replace(/&/g, " e ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

export function normalizeTeamName(value: string): string {
  const original = foldText(value);
  if (/^atletico (?:-|– )?mg$/.test(original) || original === "clube atletico mineiro") return "atletico mineiro";
  if (/^(?:atletico|athletico) (?:-|– )?pr$/.test(original) || /paranaense/.test(original)) return "athletico paranaense";
  if (/^atletico (?:-|– )?go$/.test(original) || original === "atletico goianiense") return "atletico goianiense";
  if (/^america (?:-|– )?mg$/.test(original)) return "america mineiro";
  if (/^america (?:-|– )?rn$/.test(original)) return "america natal";
  let key = original
    .replace(/\s+(?:-|–)?\s*(?:ac|al|am|ap|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to)$/i, "")
    .replace(/\s+futebol clube$/i, "")
    .trim();
  return TEAM_ALIASES[key] ?? key;
}

export function teamMatches(actualKey: string, query: string): boolean {
  const key = normalizeTeamName(query);
  if (!key) return true;
  if (actualKey === key) return true;
  const actualTokens = new Set(actualKey.split(" "));
  const queryTokens = key.split(" ");
  return queryTokens.length > 0 && queryTokens.every((token) => actualTokens.has(token));
}

export function normalizeCompetition(value: string): string {
  const key = foldText(value);
  if (/brasileir|serie a|campeonato brasileiro/.test(key)) return "Brasileirão Serie A";
  if (/copa do brasil/.test(key)) return "Copa do Brasil";
  if (/libertadores/.test(key)) return "Copa Libertadores";
  return value.trim() || "Unknown competition";
}

export function competitionMatches(actual: string, query: string): boolean {
  return foldText(normalizeCompetition(actual)).includes(foldText(normalizeCompetition(query)));
}

export function parseDate(value: string): string | null {
  const text = value.trim();
  if (!text) return null;
  const brazilian = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (brazilian) {
    const [, day, month, year] = brazilian;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }
  const iso = text.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (iso) {
    const [, year, month, day] = iso;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }
  return null;
}

export function optionalNumber(value: unknown): number | undefined {
  if (value === null || value === undefined || String(value).trim() === "") return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function requiredNumber(value: unknown): number | null {
  const parsed = optionalNumber(value);
  return parsed === undefined ? null : parsed;
}
