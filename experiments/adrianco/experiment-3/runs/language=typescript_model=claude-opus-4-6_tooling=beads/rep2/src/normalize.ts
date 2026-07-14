const STATE_SUFFIXES = /\s*-\s*(SP|RJ|MG|RS|PR|BA|SC|CE|PE|GO|PA|MA|RN|MT|MS|ES|DF|SE|AL|PB|PI|AM|RO|TO|AC|AP|RR)$/i;

const TEAM_ALIASES: Record<string, string> = {
  "sao paulo": "São Paulo",
  "sao paulo fc": "São Paulo",
  "são paulo fc": "São Paulo",
  "spfc": "São Paulo",
  "gremio": "Grêmio",
  "grêmio": "Grêmio",
  "gremio fbpa": "Grêmio",
  "atletico-mg": "Atlético-MG",
  "atlético-mg": "Atlético-MG",
  "atletico mineiro": "Atlético-MG",
  "atlético mineiro": "Atlético-MG",
  "atletico mg": "Atlético-MG",
  "club athletico paranaense": "Athletico-PR",
  "athletico-pr": "Athletico-PR",
  "athletico paranaense": "Athletico-PR",
  "atletico-pr": "Athletico-PR",
  "atlético-pr": "Athletico-PR",
  "atletico pr": "Athletico-PR",
  "atletico paranaense": "Athletico-PR",
  "atletico-go": "Atlético-GO",
  "atlético-go": "Atlético-GO",
  "atletico goianiense": "Atlético-GO",
  "flamengo-rj": "Flamengo",
  "flamengo": "Flamengo",
  "cr flamengo": "Flamengo",
  "fluminense-rj": "Fluminense",
  "fluminense": "Fluminense",
  "fluminense fc": "Fluminense",
  "palmeiras-sp": "Palmeiras",
  "palmeiras": "Palmeiras",
  "se palmeiras": "Palmeiras",
  "corinthians-sp": "Corinthians",
  "corinthians": "Corinthians",
  "sport club corinthians paulista": "Corinthians",
  "sc corinthians paulista": "Corinthians",
  "santos-sp": "Santos",
  "santos": "Santos",
  "santos fc": "Santos",
  "vasco-rj": "Vasco",
  "vasco": "Vasco",
  "vasco da gama": "Vasco",
  "cr vasco da gama": "Vasco",
  "botafogo-rj": "Botafogo",
  "botafogo": "Botafogo",
  "botafogo fr": "Botafogo",
  "internacional-rs": "Internacional",
  "internacional": "Internacional",
  "sc internacional": "Internacional",
  "cruzeiro-mg": "Cruzeiro",
  "cruzeiro": "Cruzeiro",
  "cruzeiro ec": "Cruzeiro",
  "sport-pe": "Sport",
  "sport": "Sport",
  "sport recife": "Sport",
  "sport club do recife": "Sport",
  "bahia-ba": "Bahia",
  "bahia": "Bahia",
  "ec bahia": "Bahia",
  "ceara-ce": "Ceará",
  "ceará-ce": "Ceará",
  "ceara": "Ceará",
  "ceará": "Ceará",
  "fortaleza-ce": "Fortaleza",
  "fortaleza": "Fortaleza",
  "fortaleza ec": "Fortaleza",
  "goias-go": "Goiás",
  "goiás-go": "Goiás",
  "goias": "Goiás",
  "goiás": "Goiás",
  "vitoria-ba": "Vitória",
  "vitória-ba": "Vitória",
  "vitoria": "Vitória",
  "vitória": "Vitória",
  "coritiba-pr": "Coritiba",
  "coritiba": "Coritiba",
  "avai-sc": "Avaí",
  "avaí-sc": "Avaí",
  "avai": "Avaí",
  "avaí": "Avaí",
  "chapecoense-sc": "Chapecoense",
  "chapecoense": "Chapecoense",
  "ponte preta-sp": "Ponte Preta",
  "ponte preta": "Ponte Preta",
  "portuguesa-sp": "Portuguesa",
  "portuguesa": "Portuguesa",
  "nautico-pe": "Náutico",
  "náutico-pe": "Náutico",
  "nautico": "Náutico",
  "náutico": "Náutico",
  "figueirense-sc": "Figueirense",
  "figueirense": "Figueirense",
  "america-mg": "América-MG",
  "américa-mg": "América-MG",
  "america mg": "América-MG",
  "américa mg": "América-MG",
  "america mineiro": "América-MG",
  "cuiaba-mt": "Cuiabá",
  "cuiabá-mt": "Cuiabá",
  "cuiaba": "Cuiabá",
  "cuiabá": "Cuiabá",
  "juventude-rs": "Juventude",
  "juventude": "Juventude",
  "bragantino-sp": "Bragantino",
  "bragantino": "Bragantino",
  "rb bragantino": "Bragantino",
  "red bull bragantino": "Bragantino",
  "guarani-sp": "Guarani",
  "guarani": "Guarani",
};

export function normalizeTeamName(name: string): string {
  if (!name) return name;

  let cleaned = name.trim();

  const withoutState = cleaned.replace(STATE_SUFFIXES, "");
  const key = withoutState.toLowerCase().trim();

  if (TEAM_ALIASES[key]) {
    return TEAM_ALIASES[key];
  }

  const fullKey = cleaned.toLowerCase().trim();
  if (TEAM_ALIASES[fullKey]) {
    return TEAM_ALIASES[fullKey];
  }

  return withoutState.trim() || cleaned;
}

export function teamsMatch(name1: string, name2: string): boolean {
  const n1 = normalizeTeamName(name1).toLowerCase();
  const n2 = normalizeTeamName(name2).toLowerCase();
  return n1 === n2 || n1.includes(n2) || n2.includes(n1);
}

export function parseDate(dateStr: string): Date {
  if (!dateStr) return new Date(0);

  if (dateStr.includes("/")) {
    const parts = dateStr.split("/");
    if (parts.length === 3) {
      const [day, month, year] = parts;
      return new Date(`${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`);
    }
  }

  return new Date(dateStr);
}

export function parseDateToISO(dateStr: string): string {
  const d = parseDate(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toISOString().split("T")[0];
}

export function safeParseInt(val: string | undefined): number {
  if (!val) return 0;
  const n = parseInt(val, 10);
  return isNaN(n) ? 0 : n;
}

export function safeParseFloat(val: string | undefined): number {
  if (!val) return 0;
  const n = parseFloat(val);
  return isNaN(n) ? 0 : n;
}
