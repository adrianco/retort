const STATE_SUFFIXES = /[- ]+(?:SP|RJ|MG|RS|PR|BA|SC|PE|CE|GO|PA|MA|SE|AL|MT|MS|RN|PB|PI|ES|AM|DF|RO|AC|AP|RR|TO)$/;
const TEAM_ALIASES = {
    "sport club corinthians paulista": "Corinthians",
    "corinthians": "Corinthians",
    "se palmeiras": "Palmeiras",
    "palmeiras": "Palmeiras",
    "cr flamengo": "Flamengo",
    "flamengo": "Flamengo",
    "fluminense fc": "Fluminense",
    "fluminense": "Fluminense",
    "sao paulo fc": "São Paulo",
    "sao paulo": "São Paulo",
    "são paulo fc": "São Paulo",
    "são paulo": "São Paulo",
    "santos fc": "Santos",
    "santos": "Santos",
    "sc internacional": "Internacional",
    "internacional": "Internacional",
    "gremio": "Grêmio",
    "grêmio": "Grêmio",
    "gremio fbpa": "Grêmio",
    "cr vasco da gama": "Vasco",
    "vasco da gama": "Vasco",
    "vasco": "Vasco",
    "clube de regatas do flamengo": "Flamengo",
    "botafogo fr": "Botafogo",
    "botafogo": "Botafogo",
    "atletico mineiro": "Atlético Mineiro",
    "atlético mineiro": "Atlético Mineiro",
    "atletico-mg": "Atlético Mineiro",
    "atlético-mg": "Atlético Mineiro",
    "athletico paranaense": "Athletico-PR",
    "athletico-pr": "Athletico-PR",
    "atletico paranaense": "Athletico-PR",
    "atlético paranaense": "Athletico-PR",
    "athletico": "Athletico-PR",
    "sport": "Sport",
    "sport recife": "Sport",
    "fortaleza": "Fortaleza",
    "fortaleza ec": "Fortaleza",
    "ceara": "Ceará",
    "ceará": "Ceará",
    "bahia": "Bahia",
    "ec bahia": "Bahia",
    "coritiba": "Coritiba",
    "coritiba fc": "Coritiba",
    "cruzeiro": "Cruzeiro",
    "goias": "Goiás",
    "goiás": "Goiás",
    "avai": "Avaí",
    "avaí": "Avaí",
    "chapecoense": "Chapecoense",
    "america-mg": "América-MG",
    "américa-mg": "América-MG",
    "america mineiro": "América-MG",
    "américa mineiro": "América-MG",
    "cuiaba": "Cuiabá",
    "cuiabá": "Cuiabá",
    "bragantino": "Bragantino",
    "red bull bragantino": "Bragantino",
    "juventude": "Juventude",
    "ponte preta": "Ponte Preta",
    "guarani": "Guarani",
    "vitoria": "Vitória",
    "vitória": "Vitória",
    "nautico": "Náutico",
    "náutico": "Náutico",
    "portuguesa": "Portuguesa",
    "figueirense": "Figueirense",
    "criciuma": "Criciúma",
    "criciúma": "Criciúma",
    "parana": "Paraná",
    "paraná": "Paraná",
    "paraná clube": "Paraná",
};
export function normalizeTeamName(raw) {
    if (!raw)
        return raw;
    let name = raw.trim();
    // Check alias before stripping suffix (handles "Atletico-MG" as a unit)
    const lowerFull = name.toLowerCase();
    if (TEAM_ALIASES[lowerFull]) {
        return TEAM_ALIASES[lowerFull];
    }
    name = name.replace(STATE_SUFFIXES, "").trim();
    const lower = name.toLowerCase();
    if (TEAM_ALIASES[lower]) {
        return TEAM_ALIASES[lower];
    }
    return name;
}
export function teamsMatch(query, candidate) {
    const normalizedQuery = normalizeTeamName(query).toLowerCase();
    const normalizedCandidate = normalizeTeamName(candidate).toLowerCase();
    if (normalizedQuery === normalizedCandidate)
        return true;
    return (normalizedCandidate.includes(normalizedQuery) ||
        normalizedQuery.includes(normalizedCandidate));
}
//# sourceMappingURL=normalize.js.map