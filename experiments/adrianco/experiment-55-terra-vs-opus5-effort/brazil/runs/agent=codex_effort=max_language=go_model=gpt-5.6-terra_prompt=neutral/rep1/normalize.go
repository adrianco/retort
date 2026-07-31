package main

import (
	"regexp"
	"strings"
	"unicode"
)

var nonWord = regexp.MustCompile(`[^a-z0-9]+`)

// normalizeText makes comparison accent-insensitive while keeping word
// boundaries. It is deliberately small and dependency-free so the server can
// run with only the Go standard library.
func normalizeText(value string) string {
	var b strings.Builder
	for _, r := range strings.ToLower(strings.TrimSpace(value)) {
		switch r {
		case 'á', 'à', 'â', 'ã', 'ä', 'å':
			b.WriteByte('a')
		case 'é', 'è', 'ê', 'ë':
			b.WriteByte('e')
		case 'í', 'ì', 'î', 'ï':
			b.WriteByte('i')
		case 'ó', 'ò', 'ô', 'õ', 'ö':
			b.WriteByte('o')
		case 'ú', 'ù', 'û', 'ü':
			b.WriteByte('u')
		case 'ç':
			b.WriteByte('c')
		case 'ñ':
			b.WriteByte('n')
		default:
			if r <= unicode.MaxASCII {
				b.WriteRune(r)
			} else if unicode.IsLetter(r) || unicode.IsDigit(r) {
				b.WriteRune(r)
			} else {
				b.WriteByte(' ')
			}
		}
	}
	return strings.TrimSpace(nonWord.ReplaceAllString(b.String(), " "))
}

var teamAliases = map[string]string{
	"america mg":                      "america mineiro",
	"america mineiro":                 "america mineiro",
	"america futebol clube mg":        "america mineiro",
	"athletico pr":                    "athletico paranaense",
	"athletico paranaense":            "athletico paranaense",
	"atletico pr":                     "athletico paranaense",
	"atletico mg":                     "atletico mineiro",
	"atletico mineiro":                "atletico mineiro",
	"clube atletico mineiro":          "atletico mineiro",
	"atletico go":                     "atletico goianiense",
	"atletico goianiense":             "atletico goianiense",
	"atletico goianiense go":          "atletico goianiense",
	"botafogo rj":                     "botafogo",
	"botafogo de futebol e regatas":   "botafogo",
	"ceara ce":                        "ceara",
	"corinthians sp":                  "corinthians",
	"corinthians paulista":            "corinthians",
	"sport club corinthians paulista": "corinthians",
	"cruzeiro mg":                     "cruzeiro",
	"cruzeiro esporte clube":          "cruzeiro",
	"flamengo rj":                     "flamengo",
	"clube de regatas do flamengo":    "flamengo",
	"fluminense rj":                   "fluminense",
	"fortaleza ce":                    "fortaleza",
	"gremio rs":                       "gremio",
	"gremio fbpa":                     "gremio",
	"gremio porto alegrense":          "gremio",
	"internacional rs":                "internacional",
	"sport club internacional":        "internacional",
	"palmeiras sp":                    "palmeiras",
	"sociedade esportiva palmeiras":   "palmeiras",
	"santos sp":                       "santos",
	"santos fc":                       "santos",
	"sao paulo sp":                    "sao paulo",
	"sao paulo fc":                    "sao paulo",
	"sao paulo futebol clube":         "sao paulo",
	"sport pe":                        "sport recife",
	"sport recife":                    "sport recife",
	"vasco rj":                        "vasco da gama",
	"vasco da gama":                   "vasco da gama",
	"club de regatas vasco da gama":   "vasco da gama",
	"vitoria ba":                      "vitoria",
}

var brazilianStateSuffixes = map[string]bool{
	"ac": true, "al": true, "ap": true, "am": true, "ba": true, "ce": true,
	"df": true, "es": true, "go": true, "ma": true, "mt": true, "ms": true,
	"mg": true, "pa": true, "pb": true, "pr": true, "pe": true, "pi": true,
	"rj": true, "rn": true, "rs": true, "ro": true, "rr": true, "sc": true,
	"sp": true, "se": true, "to": true,
}

// normalizeTeam resolves the common cross-file variants described in the task
// (state suffixes, accents, and formal club names) into one match key.
func normalizeTeam(team string) string {
	key := normalizeText(team)
	if alias, ok := teamAliases[key]; ok {
		return alias
	}
	parts := strings.Fields(key)
	if len(parts) > 1 && brazilianStateSuffixes[parts[len(parts)-1]] {
		key = strings.Join(parts[:len(parts)-1], " ")
		if alias, ok := teamAliases[key]; ok {
			return alias
		}
	}
	return key
}

func normalizeCompetition(competition string) string {
	key := normalizeText(competition)
	switch {
	case key == "", key == "all", key == "any":
		return ""
	case strings.Contains(key, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(key, "copa do brasil") || key == "brazilian cup":
		return "Copa do Brasil"
	case strings.Contains(key, "brasileirao") || strings.Contains(key, "brasileiro serie a") || key == "serie a" || key == "seriea":
		return "Brasileirão Série A"
	case strings.Contains(key, "serie b") || key == "serieb":
		return "Série B"
	case strings.Contains(key, "serie c") || key == "seriec":
		return "Série C"
	default:
		return strings.TrimSpace(competition)
	}
}

func teamNameMatches(candidateKey, requested string) bool {
	requestedKey := normalizeTeam(requested)
	if requestedKey == "" {
		return true
	}
	if candidateKey == requestedKey {
		return true
	}
	// This accommodates inputs such as "São Paulo FC" and data that contains
	// a harmless remaining formal-name suffix without treating arbitrary words
	// as matches.
	return strings.HasPrefix(candidateKey, requestedKey+" ") || strings.HasPrefix(requestedKey, candidateKey+" ")
}

func competitionMatches(candidate, requested string) bool {
	requested = normalizeCompetition(requested)
	return requested == "" || normalizeCompetition(candidate) == requested
}
