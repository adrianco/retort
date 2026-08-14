package main

import (
	"regexp"
	"strings"
	"unicode"
)

var stateSuffix = regexp.MustCompile(`(?i)(?:\s*-\s*|\s+)(AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO)$`)
var punctuation = regexp.MustCompile(`[^a-z0-9]+`)
var multiSpace = regexp.MustCompile(`\s+`)

var accentReplacer = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "å", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u",
	"ç", "c", "ñ", "n", "ý", "y", "ÿ", "y",
)

// normalizeText folds the Portuguese characters found in the supplied data,
// removes punctuation, and makes matching case-insensitive.
func normalizeText(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	value = accentReplacer.Replace(value)
	value = strings.Map(func(r rune) rune {
		if unicode.IsMark(r) {
			return -1
		}
		return r
	}, value)
	value = punctuation.ReplaceAllString(value, " ")
	return strings.TrimSpace(multiSpace.ReplaceAllString(value, " "))
}

var teamAliases = map[string]string{
	"america mg":                       "america mg",
	"america mineiro":                  "america mg",
	"america futebol clube":            "america mg",
	"america rn":                       "america rn",
	"athletico":                        "athletico pr",
	"athletico pr":                     "athletico pr",
	"atletico pr":                      "athletico pr",
	"athletico paranaense":             "athletico pr",
	"atletico paranaense":              "athletico pr",
	"atletico mg":                      "atletico mg",
	"atletico mineiro":                 "atletico mg",
	"atletico go":                      "atletico go",
	"atletico goianiense":              "atletico go",
	"bahia":                            "bahia ba",
	"bahia ba":                         "bahia ba",
	"botafogo":                         "botafogo rj",
	"botafogo rj":                      "botafogo rj",
	"botafogo pb":                      "botafogo pb",
	"corinthians":                      "corinthians sp",
	"corinthians sp":                   "corinthians sp",
	"corinthians paulista":             "corinthians sp",
	"sport club corinthians paulista":  "corinthians sp",
	"cruzeiro":                         "cruzeiro mg",
	"cruzeiro mg":                      "cruzeiro mg",
	"flamengo":                         "flamengo rj",
	"flamengo rj":                      "flamengo rj",
	"club de regatas do flamengo":      "flamengo rj",
	"clube de regatas flamengo":        "flamengo rj",
	"fluminense":                       "fluminense rj",
	"fluminense rj":                    "fluminense rj",
	"fortaleza":                        "fortaleza ce",
	"fortaleza ce":                     "fortaleza ce",
	"gremio":                           "gremio rs",
	"gremio rs":                        "gremio rs",
	"gremio foot ball porto alegrense": "gremio rs",
	"internacional":                    "internacional rs",
	"internacional rs":                 "internacional rs",
	"sport club internacional":         "internacional rs",
	"nautico":                          "nautico pe",
	"nautico pe":                       "nautico pe",
	"nautico capibaribe":               "nautico pe",
	"palmeiras":                        "palmeiras sp",
	"palmeiras sp":                     "palmeiras sp",
	"sociedade esportiva palmeiras":    "palmeiras sp",
	"santos":                           "santos sp",
	"santos sp":                        "santos sp",
	"santos futebol clube":             "santos sp",
	"sao paulo":                        "sao paulo sp",
	"sao paulo sp":                     "sao paulo sp",
	"sao paulo futebol clube":          "sao paulo sp",
	"sao paulo fc":                     "sao paulo sp",
	"sport":                            "sport pe",
	"sport pe":                         "sport pe",
	"sport recife":                     "sport pe",
	"vasco":                            "vasco rj",
	"vasco rj":                         "vasco rj",
	"vasco da gama":                    "vasco rj",
	"vitoria":                          "vitoria ba",
	"vitoria ba":                       "vitoria ba",
}

// preferredTeamDisplays keeps concise labels for unambiguous, well-known
// clubs while retaining a state qualifier where the bare label could identify
// a different club. This matters for data such as Botafogo-PB and Santos-AP:
// a search may normalize a name, but its returned rows must not conceal which
// club actually played.
var preferredTeamDisplays = map[string]string{
	"america mg":       "América-MG",
	"america rn":       "América-RN",
	"athletico pr":     "Athletico-PR",
	"atletico go":      "Atlético-GO",
	"atletico mg":      "Atlético-MG",
	"bahia ba":         "Bahia",
	"botafogo pb":      "Botafogo-PB",
	"botafogo rj":      "Botafogo-RJ",
	"corinthians sp":   "Corinthians",
	"cruzeiro mg":      "Cruzeiro",
	"flamengo rj":      "Flamengo",
	"fluminense rj":    "Fluminense",
	"fortaleza ce":     "Fortaleza",
	"gremio rs":        "Grêmio",
	"internacional rs": "Internacional-RS",
	"nautico pe":       "Náutico-PE",
	"palmeiras sp":     "Palmeiras",
	"santos sp":        "Santos",
	"sao paulo sp":     "São Paulo",
	"sport pe":         "Sport",
	"vasco rj":         "Vasco",
	"vitoria ba":       "Vitória",
}

// normalizeTeam makes name matching stable across data sources without erasing
// a team's geographic identity. A bare common name maps to its well-known club
// (for example Flamengo -> Flamengo-RJ), but an explicit Flamengo-PI remains a
// distinct key instead of being silently folded into the Rio club.
func normalizeTeam(value string) string {
	value = strings.TrimSpace(value)
	rawKey := normalizeText(value)
	if alias, ok := teamAliases[rawKey]; ok {
		return alias
	}

	key := rawKey
	for _, suffix := range []string{" futebol clube", " football club", " fc"} {
		if strings.HasSuffix(key, suffix) {
			candidate := strings.TrimSpace(strings.TrimSuffix(key, suffix))
			if alias, ok := teamAliases[candidate]; ok {
				return alias
			}
			key = candidate
		}
	}
	if alias, ok := teamAliases[key]; ok {
		return alias
	}
	return key
}

func normalizeCompetition(value string) string {
	key := normalizeText(value)
	switch {
	case strings.Contains(key, "libertadores"):
		return "libertadores"
	case strings.Contains(key, "copa do brasil") || strings.Contains(key, "brazilian cup"):
		return "copa do brasil"
	case strings.Contains(key, "histor") && strings.Contains(key, "brasileir"):
		return "brasileirao historical"
	case strings.Contains(key, "brasileir") || strings.Contains(key, "serie a") || strings.Contains(key, "campeonato brasileiro"):
		return "brasileirao"
	default:
		return key
	}
}

func cleanDisplayTeam(value string) string {
	return strings.TrimSpace(stateSuffix.ReplaceAllString(value, ""))
}

func displayTeam(value string) string {
	key := normalizeTeam(value)
	if display, ok := preferredTeamDisplays[key]; ok {
		return display
	}
	// Preserve an explicit suffix for clubs not covered by the known alias map
	// instead of turning Flamengo-PI or Santos-AP into an ambiguous Flamengo or
	// Santos in an answer.
	if stateSuffix.MatchString(value) {
		return strings.TrimSpace(value)
	}
	return cleanDisplayTeam(value)
}
