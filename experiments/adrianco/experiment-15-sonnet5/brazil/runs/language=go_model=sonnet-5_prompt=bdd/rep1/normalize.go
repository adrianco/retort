package main

import (
	"regexp"
	"strings"
)

// accentReplacer strips the diacritics commonly found in Brazilian
// Portuguese team and player names so that names can be compared without
// depending on exact accent usage across datasets.
var accentReplacer = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u",
	"ç", "c", "ñ", "n",
	"Á", "A", "À", "A", "Â", "A", "Ã", "A", "Ä", "A",
	"É", "E", "È", "E", "Ê", "E", "Ë", "E",
	"Í", "I", "Ì", "I", "Î", "I", "Ï", "I",
	"Ó", "O", "Ò", "O", "Ô", "O", "Õ", "O", "Ö", "O",
	"Ú", "U", "Ù", "U", "Û", "U", "Ü", "U",
	"Ç", "C", "Ñ", "N",
)

// brazilianStateCodes lists the 27 official UF abbreviations. Only these are
// treated as a "decorative" state suffix to strip from a team name (e.g.
// "Palmeiras-SP" -> "Palmeiras"); this avoids accidentally truncating
// unrelated two-letter word endings.
const brazilianStateCodes = `AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO`

var (
	parenRe       = regexp.MustCompile(`\([^)]*\)`)
	stateSuffixRe = regexp.MustCompile(`(?i)[\s-]+(` + brazilianStateCodes + `)\s*$`)
	nonAlnumRe    = regexp.MustCompile(`[^a-z0-9 ]+`)
	whitespaceRe  = regexp.MustCompile(`\s+`)
)

// teamAliases maps a normalized name (accents stripped, lower-cased,
// punctuation collapsed to spaces) to a canonical display name, for the
// major clubs that appear across the provided datasets under many spellings:
// with/without their home-state suffix, full legal name, abbreviations, etc.
//
// Entries that include a state code (e.g. "palmeiras sp", "atletico mg") are
// deliberately matched BEFORE the generic state-suffix stripper runs, so
// that clubs whose identity itself embeds a state code (Atletico-MG vs
// Atletico-PR vs Atletico-GO are three different clubs) are not collapsed
// into one another by naive suffix stripping.
var teamAliases = map[string]string{
	"flamengo":                     "Flamengo",
	"flamengo rj":                  "Flamengo",
	"clube de regatas do flamengo": "Flamengo",
	"cr flamengo":                  "Flamengo",

	"fluminense":               "Fluminense",
	"fluminense rj":            "Fluminense",
	"fluminense fc":            "Fluminense",
	"fluminense football club": "Fluminense",

	"palmeiras":                     "Palmeiras",
	"palmeiras sp":                  "Palmeiras",
	"sociedade esportiva palmeiras": "Palmeiras",

	"corinthians":                     "Corinthians",
	"corinthians sp":                  "Corinthians",
	"sport club corinthians paulista": "Corinthians",
	"sc corinthians paulista":         "Corinthians",

	"sao paulo":               "Sao Paulo",
	"sao paulo sp":            "Sao Paulo",
	"sao paulo fc":            "Sao Paulo",
	"sao paulo futebol clube": "Sao Paulo",

	"santos":               "Santos",
	"santos sp":            "Santos",
	"santos fc":            "Santos",
	"santos futebol clube": "Santos",

	"gremio":                           "Gremio",
	"gremio rs":                        "Gremio",
	"gremio foot-ball porto alegrense": "Gremio",
	"gremio foot ball porto alegrense": "Gremio",

	"internacional":            "Internacional",
	"internacional rs":         "Internacional",
	"sport club internacional": "Internacional",

	"cruzeiro":               "Cruzeiro",
	"cruzeiro mg":            "Cruzeiro",
	"cruzeiro esporte clube": "Cruzeiro",

	"atletico-mg":            "Atletico-MG",
	"atletico mg":            "Atletico-MG",
	"atletico mineiro":       "Atletico-MG",
	"clube atletico mineiro": "Atletico-MG",

	"atletico-pr":               "Athletico-PR",
	"athletico-pr":              "Athletico-PR",
	"atletico pr":               "Athletico-PR",
	"athletico pr":              "Athletico-PR",
	"athletico paranaense":      "Athletico-PR",
	"club athletico paranaense": "Athletico-PR",
	"atletico paranaense":       "Athletico-PR",

	"vasco":                         "Vasco da Gama",
	"vasco rj":                      "Vasco da Gama",
	"vasco da gama":                 "Vasco da Gama",
	"vasco da gama rj":              "Vasco da Gama",
	"cr vasco da gama":              "Vasco da Gama",
	"club de regatas vasco da gama": "Vasco da Gama",

	"botafogo":                      "Botafogo",
	"botafogo rj":                   "Botafogo",
	"botafogo de futebol e regatas": "Botafogo",
	"botafogo fr":                   "Botafogo",

	"bahia":               "Bahia",
	"bahia ba":            "Bahia",
	"ec bahia":            "Bahia",
	"esporte clube bahia": "Bahia",

	"sport":                "Sport Recife",
	"sport pe":             "Sport Recife",
	"sport recife":         "Sport Recife",
	"sport club do recife": "Sport Recife",

	"fortaleza":               "Fortaleza",
	"fortaleza ce":            "Fortaleza",
	"fortaleza ec":            "Fortaleza",
	"fortaleza fc":            "Fortaleza",
	"fortaleza esporte clube": "Fortaleza",

	"ceara":               "Ceara",
	"ceara ce":            "Ceara",
	"ceara sc":            "Ceara",
	"ceara sporting club": "Ceara",

	"coritiba":                "Coritiba",
	"coritiba pr":             "Coritiba",
	"coritiba foot ball club": "Coritiba",

	"goias":               "Goias",
	"goias go":            "Goias",
	"goias ec":            "Goias",
	"goias esporte clube": "Goias",

	"atletico-go":         "Atletico-GO",
	"atletico go":         "Atletico-GO",
	"atletico goianiense": "Atletico-GO",

	"chapecoense":                       "Chapecoense",
	"chapecoense sc":                    "Chapecoense",
	"associacao chapecoense de futebol": "Chapecoense",

	"avai":    "Avai",
	"avai sc": "Avai",
	"avai fc": "Avai",

	"figueirense":    "Figueirense",
	"figueirense sc": "Figueirense",
	"figueirense fc": "Figueirense",

	"ponte preta":                     "Ponte Preta",
	"ponte preta sp":                  "Ponte Preta",
	"associacao atletica ponte preta": "Ponte Preta",

	"guarani":    "Guarani",
	"guarani sp": "Guarani",
	"guarani fc": "Guarani",

	"red bull bragantino":       "Bragantino",
	"bragantino":                "Bragantino",
	"bragantino sp":             "Bragantino",
	"clube atletico bragantino": "Bragantino",

	"cuiaba":               "Cuiaba",
	"cuiaba mt":            "Cuiaba",
	"cuiaba ec":            "Cuiaba",
	"cuiaba esporte clube": "Cuiaba",

	"america-mg":      "America-MG",
	"america mg":      "America-MG",
	"america mineiro": "America-MG",
	"america fc":      "America-MG",

	"criciuma":    "Criciuma",
	"criciuma sc": "Criciuma",
	"criciuma ec": "Criciuma",

	"juventude":    "Juventude",
	"juventude rs": "Juventude",
	"ec juventude": "Juventude",

	"vitoria":               "Vitoria",
	"vitoria ba":            "Vitoria",
	"ec vitoria":            "Vitoria",
	"esporte clube vitoria": "Vitoria",

	"parana":       "Parana",
	"parana pr":    "Parana",
	"parana clube": "Parana",

	"nautico":                  "Nautico",
	"nautico pe":               "Nautico",
	"clube nautico capibaribe": "Nautico",

	"portuguesa":                         "Portuguesa",
	"portuguesa sp":                      "Portuguesa",
	"associacao portuguesa de desportos": "Portuguesa",
}

func normalizeKey(s string) string {
	ascii := accentReplacer.Replace(s)
	lower := strings.ToLower(ascii)
	lower = nonAlnumRe.ReplaceAllString(lower, " ")
	lower = whitespaceRe.ReplaceAllString(lower, " ")
	return strings.TrimSpace(lower)
}

// reservedCanonicalKeys holds every key a curated alias can resolve to (e.g.
// "botafogo" for the Rio giant Botafogo). Stripping a state suffix off an
// unaliased name must never produce one of these keys, or an unrelated
// lower-tier club sharing that base name (e.g. a Sao Paulo "Botafogo SP")
// would silently merge into the major club's stats.
var reservedCanonicalKeys = buildReservedCanonicalKeys()

func buildReservedCanonicalKeys() map[string]bool {
	reserved := make(map[string]bool)
	for _, canonical := range teamAliases {
		reserved[normalizeKey(canonical)] = true
	}
	return reserved
}

// NormalizeTeamName produces a canonical (key, display) pair for a raw team
// name as it appears in any of the provided datasets. It strips accents and
// parenthetical notes, then checks the curated alias table for the major
// clubs (including their proper state code, so identity-bearing suffixes
// like "Atletico-MG" are preserved). If there is no alias match, it strips a
// trailing Brazilian state-abbreviation suffix as decoration (e.g.
// "Palmeiras-SP" -> "Palmeiras") and uses the cleaned name as-is.
//
// Note: for clubs outside the curated alias table, two different lower-tier
// clubs that share a base name but play in different states (e.g. a
// "Botafogo" from Sao Paulo vs. the well-known Botafogo from Rio de Janeiro)
// may collapse to the same key once their state suffix is stripped. This is
// an inherent ambiguity in the source data's naming conventions; the alias
// table resolves it for every major, frequently-queried club.
func NormalizeTeamName(raw string) (key string, display string) {
	cleaned := strings.TrimSpace(raw)
	cleaned = parenRe.ReplaceAllString(cleaned, "")
	cleaned = strings.TrimSpace(cleaned)
	if cleaned == "" {
		cleaned = strings.TrimSpace(raw)
	}

	if canonical, ok := teamAliases[normalizeKey(cleaned)]; ok {
		return normalizeKey(canonical), canonical
	}

	// Not in the alias table under its full form: strip a trailing
	// Brazilian state code as decoration and use the result directly. If
	// stripping would collide with a reserved major-club key (e.g. an
	// unrelated "Botafogo SP" stripping down to "Botafogo"), keep the
	// suffix instead so the two clubs stay distinguished.
	stripped := strings.TrimSpace(stateSuffixRe.ReplaceAllString(cleaned, ""))
	if stripped == "" || reservedCanonicalKeys[normalizeKey(stripped)] {
		stripped = cleaned
	}

	return normalizeKey(stripped), whitespaceRe.ReplaceAllString(stripped, " ")
}
