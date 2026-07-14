// Team name normalization - strips state suffixes and normalizes common variations

const STATE_SUFFIXES = /-(SP|RJ|MG|RS|PR|BA|PE|CE|GO|SC|PA|AM|MA|PI|AL|SE|RN|PB|ES|MS|MT|RO|AC|TO|AP|RR|DF)\b/i;

// Map of common name variations to canonical names
const TEAM_ALIASES: Record<string, string> = {
  'atletico mineiro': 'Atlético Mineiro',
  'atletico-mg': 'Atlético Mineiro',
  'atletico mg': 'Atlético Mineiro',
  'atletico': 'Atlético Mineiro',
  'galo': 'Atlético Mineiro',
  'atletico paranaense': 'Athletico Paranaense',
  'atletico-pr': 'Athletico Paranaense',
  'athletico-pr': 'Athletico Paranaense',
  'athletico paranaense': 'Athletico Paranaense',
  'atletico pr': 'Athletico Paranaense',
  'flamengo': 'Flamengo',
  'flamengo-rj': 'Flamengo',
  'fluminense': 'Fluminense',
  'fluminense-rj': 'Fluminense',
  'vasco': 'Vasco da Gama',
  'vasco da gama': 'Vasco da Gama',
  'vasco-rj': 'Vasco da Gama',
  'botafogo': 'Botafogo',
  'botafogo-rj': 'Botafogo',
  'palmeiras': 'Palmeiras',
  'palmeiras-sp': 'Palmeiras',
  'corinthians': 'Corinthians',
  'corinthians-sp': 'Corinthians',
  'sport club corinthians paulista': 'Corinthians',
  'santos': 'Santos',
  'santos-sp': 'Santos',
  'sao paulo': 'São Paulo',
  'são paulo': 'São Paulo',
  'sao paulo-sp': 'São Paulo',
  'sao paulo fc': 'São Paulo',
  'gremio': 'Grêmio',
  'grêmio': 'Grêmio',
  'gremio-rs': 'Grêmio',
  'internacional': 'Internacional',
  'internacional-rs': 'Internacional',
  'inter': 'Internacional',
  'cruzeiro': 'Cruzeiro',
  'cruzeiro-mg': 'Cruzeiro',
  'sport': 'Sport',
  'sport-pe': 'Sport',
  'sport recife': 'Sport',
  'fortaleza': 'Fortaleza',
  'ceara': 'Ceará',
  'ceará': 'Ceará',
  'bahia': 'Bahia',
  'vitoria': 'Vitória',
  'vitória': 'Vitória',
  'coritiba': 'Coritiba',
  'parana': 'Paraná',
  'goias': 'Goiás',
  'goiás': 'Goiás',
  'portuguesa': 'Portuguesa',
  'portuguesa-sp': 'Portuguesa',
  'santa cruz': 'Santa Cruz',
  'america mg': 'América Mineiro',
  'america mineiro': 'América Mineiro',
  'america-mg': 'América Mineiro',
  'américa mineiro': 'América Mineiro',
  'avai': 'Avaí',
  'avaí': 'Avaí',
  'figueirense': 'Figueirense',
  'guarani': 'Guarani',
  'juventude': 'Juventude',
  'chapecoense': 'Chapecoense',
  'nautico': 'Náutico',
  'náutico': 'Náutico',
  'sampaio correa': 'Sampaio Corrêa',
  'bragantino': 'RB Bragantino',
  'rb bragantino': 'RB Bragantino',
  'red bull bragantino': 'RB Bragantino',
  'cuiaba': 'Cuiabá',
  'cuiabá': 'Cuiabá',
};

export function normalizeTeamName(name: string): string {
  if (!name) return name;
  // Remove state suffix
  let normalized = name.trim().replace(STATE_SUFFIXES, '').trim();
  // Check alias map
  const key = normalized.toLowerCase().trim();
  if (TEAM_ALIASES[key]) {
    return TEAM_ALIASES[key];
  }
  return normalized;
}

export function teamsMatch(team1: string, team2: string): boolean {
  const n1 = normalizeTeamName(team1).toLowerCase();
  const n2 = normalizeTeamName(team2).toLowerCase();
  if (n1 === n2) return true;
  // Also check if one contains the other (for partial matches)
  return n1.includes(n2) || n2.includes(n1);
}

export function teamMatchesQuery(teamName: string, query: string): boolean {
  const normalizedTeam = normalizeTeamName(teamName).toLowerCase();
  const normalizedQuery = normalizeTeamName(query).toLowerCase();
  return normalizedTeam.includes(normalizedQuery) || normalizedQuery.includes(normalizedTeam);
}
