const STATE_CODES = new Set([
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
  "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
  "SP", "SE", "TO",
]);

const TEAM_ALIASES: Record<string, string> = {
  "atletico mineiro": "atletico mg",
  "clube atletico mineiro": "atletico mg",
  "atletico mg": "atletico mg",
  "atletico paranaense": "athletico pr",
  "athletico paranaense": "athletico pr",
  "athletico pr": "athletico pr",
  "botafogo de futebol e regatas": "botafogo",
  "club de regatas vasco da gama": "vasco",
  "cr vasco da gama": "vasco",
  "fluminense football club": "fluminense",
  "gremio foot ball porto alegrense": "gremio",
  "internacional porto alegre": "internacional",
  "red bull bragantino": "bragantino",
  "sport club corinthians paulista": "corinthians",
  "sport club do recife": "sport",
  "sao paulo fc": "sao paulo",
  "sao paulo futebol clube": "sao paulo",
  "sociedade esportiva palmeiras": "palmeiras",
  "vasco da gama": "vasco",
};

export function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\uFEFF/g, "")
    .toLowerCase()
    .replace(/&/g, " e ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

export function normalizeTeamName(value: string): string {
  let cleaned = value.trim();
  cleaned = cleaned.replace(/\s*\([^)]*(?:antigo|[A-Z]{3})[^)]*\)\s*/giu, " ");
  const stateMatch = /\s*-\s*([A-Z]{2})\s*$/u.exec(cleaned);
  const state = stateMatch?.[1]?.toUpperCase();
  cleaned = cleaned.replace(/\s+-\s*([A-Z]{2,3})\s*$/u, (_, suffix: string) =>
    STATE_CODES.has(suffix.toUpperCase()) || suffix.length === 3 ? "" : ` ${suffix}`,
  );
  cleaned = cleaned.replace(/-([A-Z]{2})$/u, (_, state: string) =>
    STATE_CODES.has(state.toUpperCase()) ? "" : ` ${state}`,
  );
  const normalized = normalizeText(cleaned);
  if (state) {
    if (normalized === "atletico" || normalized === "athletico") {
      if (state === "MG") return "atletico mg";
      if (state === "PR") return "athletico pr";
      return `atletico ${state.toLowerCase()}`;
    }
    if (normalized === "america" && ["MG", "RN"].includes(state)) return `america ${state.toLowerCase()}`;
    if (normalized === "botafogo" && state !== "RJ") return `botafogo ${state.toLowerCase()}`;
  }
  return TEAM_ALIASES[normalized] ?? normalized;
}

export function normalizeCompetition(value: string): string {
  const key = normalizeText(value);
  if (/brasileir|serie a|campeonato brasileiro/.test(key)) return "brasileirao";
  if (/copa do brasil|brazilian cup/.test(key)) return "copa do brasil";
  if (/libertadores/.test(key)) return "libertadores";
  return key;
}

export function parseNumber(value: unknown): number | undefined {
  if (value === undefined || value === null || value === "") return undefined;
  const result = Number(String(value).replace(",", "."));
  return Number.isFinite(result) ? result : undefined;
}

export function parseRequiredNumber(value: unknown, field: string): number {
  const result = parseNumber(value);
  if (result === undefined) throw new Error(`Invalid numeric value for ${field}: ${String(value)}`);
  return result;
}

export function parseSoccerDate(value: string): { date: string; timestamp: number } {
  const trimmed = value.trim();
  const brazilian = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(trimmed);
  if (brazilian) {
    const [, day = "1", month = "1", year = "1970"] = brazilian;
    const date = `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
    return { date, timestamp: Date.parse(`${date}T00:00:00Z`) };
  }

  const iso = /^(\d{4}-\d{2}-\d{2})/.exec(trimmed)?.[1];
  if (!iso) throw new Error(`Unsupported date format: ${value}`);
  return { date: iso, timestamp: Date.parse(`${iso}T00:00:00Z`) };
}

export function displayTeamName(raw: string): string {
  const stateMatch = /\s*-\s*([A-Z]{2})\s*$/u.exec(raw);
  const state = stateMatch?.[1];
  const base = raw.replace(/\s*-\s*[A-Z]{2}\s*$/u, "").trim();
  const normalizedBase = normalizeText(base);
  if (state && normalizedBase === "atletico") {
    if (state === "MG") return "Atlético Mineiro";
    if (state === "PR") return "Athletico Paranaense";
    return `${base}-${state}`;
  }
  if (state && normalizedBase === "america" && ["MG", "RN"].includes(state)) return `${base}-${state}`;
  if (state && normalizedBase === "botafogo" && state !== "RJ") return `${base}-${state}`;
  return raw
    .replace(/\s+-\s*[A-Z]{2,3}\s*$/u, "")
    .replace(/-([A-Z]{2})$/u, "")
    .trim();
}

export function includesNormalized(haystack: string | undefined, needle: string): boolean {
  return haystack !== undefined && normalizeText(haystack).includes(normalizeText(needle));
}
