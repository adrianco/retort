package main

import (
	"regexp"
	"strings"
	"unicode"
)

var accentFold = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "å", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u",
	"ý", "y", "ÿ", "y", "ç", "c", "ñ", "n",
)

var stateSuffixes = map[string]struct{}{
	"ac": {}, "al": {}, "ap": {}, "am": {}, "ba": {}, "ce": {}, "df": {}, "es": {}, "go": {},
	"ma": {}, "mt": {}, "ms": {}, "mg": {}, "pa": {}, "pb": {}, "pr": {}, "pe": {}, "pi": {},
	"rj": {}, "rn": {}, "rs": {}, "ro": {}, "rr": {}, "sc": {}, "sp": {}, "se": {}, "to": {},
}

var teamAliases = map[string]string{
	"sport club corinthians paulista":  "corinthians",
	"sc corinthians paulista":          "corinthians",
	"corinthians paulista":             "corinthians",
	"clube de regatas do flamengo":     "flamengo",
	"cr flamengo":                      "flamengo",
	"sociedade esportiva palmeiras":    "palmeiras",
	"sao paulo futebol clube":          "sao paulo",
	"sao paulo fc":                     "sao paulo",
	"santos futebol clube":             "santos",
	"gremio fbpa":                      "gremio",
	"gremio foot ball porto alegrense": "gremio",
	"athletico pr":                     "athletico paranaense",
	"athletico paranaense":             "athletico paranaense",
	"atletico paranaense":              "athletico paranaense",
	"club athletico paranaense":        "athletico paranaense",
	"atletico mg":                      "atletico mineiro",
	"atletico mineiro":                 "atletico mineiro",
	"clube atletico mineiro":           "atletico mineiro",
	"atletico go":                      "atletico goianiense",
	"atletico goianiense":              "atletico goianiense",
	"america mg":                       "america mineiro",
	"america mineiro":                  "america mineiro",
	"america futebol clube mg":         "america mineiro",
	"red bull bragantino":              "bragantino",
	"red bull bragantino sp":           "bragantino",
	"clube de regatas vasco da gama":   "vasco da gama",
	"vasco":                            "vasco da gama",
	"botafogo de futebol e regatas":    "botafogo",
	"esporte clube bahia":              "bahia",
	"esporte clube vitoria":            "vitoria",
	"coritiba foot ball club":          "coritiba",
	"figueirense futebol clube":        "figueirense",
	"avai futebol clube":               "avai",
}

var trailingStatePattern = regexp.MustCompile(`(?i)(?:\s*[-–]\s*|\s+)([a-z]{2})\s*$`)

// normalizeText makes user input and CSV values comparable while preserving the
// original value separately for display. It deliberately does not do fuzzy matching.
func normalizeText(value string) string {
	value = strings.ToLower(strings.TrimSpace(strings.TrimPrefix(value, "\ufeff")))
	value = accentFold.Replace(value)
	var out strings.Builder
	for _, r := range value {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			out.WriteRune(r)
		} else {
			out.WriteByte(' ')
		}
	}
	return strings.Join(strings.Fields(out.String()), " ")
}

// normalizeTeam collapses the known variants used across the supplied datasets.
// It intentionally leaves international club suffixes such as "(URU)" intact.
func normalizeTeam(value string) string {
	key := normalizeText(value)
	if key == "" {
		return ""
	}
	if alias, ok := teamAliases[key]; ok {
		return alias
	}
	parts := strings.Fields(key)
	if len(parts) > 1 {
		if _, isState := stateSuffixes[parts[len(parts)-1]]; isState {
			withoutState := strings.Join(parts[:len(parts)-1], " ")
			if alias, ok := teamAliases[key]; ok {
				return alias
			}
			if alias, ok := teamAliases[withoutState]; ok {
				return alias
			}
			return withoutState
		}
	}
	if alias, ok := teamAliases[key]; ok {
		return alias
	}
	return key
}

func displayTeam(value string) string {
	value = strings.TrimSpace(value)
	match := trailingStatePattern.FindStringSubmatch(value)
	if len(match) == 2 {
		if _, ok := stateSuffixes[strings.ToLower(match[1])]; ok {
			value = strings.TrimSpace(value[:len(value)-len(match[0])])
		}
	}
	return value
}

func teamKeysMatch(a, b string) bool {
	if a == "" || b == "" {
		return false
	}
	if a == b {
		return true
	}
	// A one-word search such as "Atletico" should find the explicitly
	// distinguished Atlético clubs, but longer inputs remain exact to avoid
	// accidental fuzzy matches.
	if !strings.Contains(a, " ") && strings.HasPrefix(b, a+" ") {
		return true
	}
	if !strings.Contains(b, " ") && strings.HasPrefix(a, b+" ") {
		return true
	}
	return false
}

func canonicalCompetition(value string) string {
	key := normalizeText(value)
	switch {
	case strings.Contains(key, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(key, "copa do brasil") || strings.Contains(key, "brazilian cup"):
		return "Copa do Brasil"
	case strings.Contains(key, "brasileirao") || strings.Contains(key, "brasileiro") || key == "serie a":
		return "Brasileirão Série A"
	case key == "serie b":
		return "Brasileirão Série B"
	case key == "serie c":
		return "Brasileirão Série C"
	default:
		return strings.TrimSpace(value)
	}
}

func competitionMatches(actual, requested string) bool {
	if strings.TrimSpace(requested) == "" {
		return true
	}
	want := canonicalCompetition(requested)
	if want == actual {
		return true
	}
	return normalizeText(actual) == normalizeText(requested)
}
