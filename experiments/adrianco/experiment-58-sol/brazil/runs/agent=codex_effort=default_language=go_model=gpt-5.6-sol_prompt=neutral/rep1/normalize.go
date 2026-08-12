package main

import (
	"regexp"
	"strings"
	"time"
	"unicode"
)

var stateSuffix = regexp.MustCompile(`(?i)\s*(?:-|\s-\s)[A-Z]{2}$`)

var teamAliases = map[string]string{
	"sport club corinthians paulista":  "corinthians",
	"sport club corinthians":           "corinthians",
	"corinthians paulista":             "corinthians",
	"sao paulo fc":                     "sao paulo",
	"sao paulo futebol clube":          "sao paulo",
	"clube de regatas do flamengo":     "flamengo",
	"fluminense football club":         "fluminense",
	"sociedade esportiva palmeiras":    "palmeiras",
	"santos fc":                        "santos",
	"club de regatas vasco da gama":    "vasco",
	"vasco da gama":                    "vasco",
	"gremio foot-ball porto alegrense": "gremio",
	"clube atletico mineiro":           "atletico mineiro",
	"atletico mg":                      "atletico mineiro",
	"atletico go":                      "atletico goianiense",
	"atletico clube goianiense":        "atletico goianiense",
	"athletico paranaense":             "athletico pr",
	"atletico paranaense":              "athletico pr",
	"athletico pr":                     "athletico pr",
	"america mg":                       "america mineiro",
	"america rn":                       "america natal",
}

func fold(s string) string {
	s = strings.ToLower(strings.TrimSpace(strings.TrimPrefix(s, "\ufeff")))
	replacer := strings.NewReplacer(
		"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
		"é", "e", "è", "e", "ê", "e", "ë", "e",
		"í", "i", "ì", "i", "î", "i", "ï", "i",
		"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
		"ú", "u", "ù", "u", "û", "u", "ü", "u", "ç", "c",
	)
	s = replacer.Replace(s)
	return strings.Join(strings.FieldsFunc(s, func(r rune) bool {
		return !(unicode.IsLetter(r) || unicode.IsDigit(r))
	}), " ")
}

func normalizeTeam(s string) string {
	s = strings.TrimSpace(s)
	// Resolve aliases whose state suffix disambiguates clubs before removing it.
	if alias, ok := teamAliases[fold(s)]; ok {
		return alias
	}
	// State suffixes occur both as "Flamengo-RJ" and "Flamengo - RJ".
	s = stateSuffix.ReplaceAllString(s, "")
	n := fold(s)
	if alias, ok := teamAliases[n]; ok {
		return alias
	}
	return n
}

func teamMatches(actual, query string) bool {
	a, q := normalizeTeam(actual), normalizeTeam(query)
	return q != "" && (a == q || strings.Contains(a, q) || strings.Contains(q, a))
}

func normalizeCompetition(s string) string {
	n := fold(s)
	switch {
	case strings.Contains(n, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(n, "copa do brasil") || strings.Contains(n, "brazilian cup"):
		return "Copa do Brasil"
	case n == "serie a" || strings.Contains(n, "brasileir"):
		return "Brasileirão Serie A"
	case n == "serie b":
		return "Brasileirão Serie B"
	case n == "serie c":
		return "Brasileirão Serie C"
	default:
		return strings.TrimSpace(s)
	}
}

func competitionMatches(actual, query string) bool {
	if strings.TrimSpace(query) == "" {
		return true
	}
	a, q := fold(normalizeCompetition(actual)), fold(normalizeCompetition(query))
	return a == q || strings.Contains(a, q) || strings.Contains(q, a)
}

func nationalityMatches(actual, query string) bool {
	a, q := fold(actual), fold(query)
	aliases := map[string]string{"brasil": "brazil", "brasileiro": "brazil", "brasileira": "brazil"}
	if v := aliases[a]; v != "" {
		a = v
	}
	if v := aliases[q]; v != "" {
		q = v
	}
	return a == q || strings.Contains(a, q) || strings.Contains(q, a)
}

func parseDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	for _, layout := range []string{
		"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", time.RFC3339,
	} {
		if t, err := time.Parse(layout, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, &time.ParseError{Value: s, Layout: "supported soccer date"}
}
