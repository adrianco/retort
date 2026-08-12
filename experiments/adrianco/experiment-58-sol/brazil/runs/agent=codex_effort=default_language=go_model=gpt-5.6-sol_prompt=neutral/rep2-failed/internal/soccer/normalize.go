package soccer

import (
	"fmt"
	"strconv"
	"strings"
	"time"
	"unicode"
)

var accents = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u", "ç", "c",
)

var teamAliases = map[string]string{
	"clube de regatas do flamengo":     "flamengo",
	"flamengo rj":                      "flamengo",
	"fluminense football club":         "fluminense",
	"sport club corinthians paulista":  "corinthians",
	"corinthians paulista":             "corinthians",
	"sociedade esportiva palmeiras":    "palmeiras",
	"santos futebol clube":             "santos",
	"santos fc":                        "santos",
	"sao paulo futebol clube":          "sao paulo",
	"sao paulo fc":                     "sao paulo",
	"clube atletico mineiro":           "atletico mineiro",
	"atletico mg":                      "atletico mineiro",
	"club de regatas vasco da gama":    "vasco",
	"vasco da gama":                    "vasco",
	"gremio foot ball porto alegrense": "gremio",
	"internacional porto alegre":       "internacional",
	"sport club internacional":         "internacional",
	"athletico paranaense":             "athletico pr",
	"atletico paranaense":              "athletico pr",
	"atletico pr":                      "athletico pr",
	"america mg":                       "america",
	"atletico go":                      "atletico goianiense",
	"botafogo rj":                      "botafogo",
	"fortaleza fc":                     "fortaleza",
	"ec juventude":                     "juventude",
	"red bull bragantino sp":           "red bull bragantino",
	"bragantino":                       "red bull bragantino",
}

func searchKey(s string) string {
	s = accents.Replace(strings.ToLower(strings.TrimSpace(strings.TrimPrefix(s, "\ufeff"))))
	var b strings.Builder
	space := true
	for _, r := range s {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			b.WriteRune(r)
			space = false
		} else if !space {
			b.WriteByte(' ')
			space = true
		}
	}
	return strings.TrimSpace(b.String())
}

// NormalizeTeam makes names from all five match datasets comparable.
func NormalizeTeam(name string) string {
	name = strings.TrimSpace(name)
	if i := strings.Index(name, "("); i >= 0 {
		name = strings.TrimSpace(name[:i])
	}
	if alias, ok := teamAliases[searchKey(name)]; ok {
		return alias
	}
	// Dataset suffixes are state/country codes (Palmeiras-SP, América - MG).
	if i := strings.LastIndex(name, "-"); i > 0 {
		suffix := strings.TrimSpace(name[i+1:])
		if len([]rune(suffix)) >= 2 && len([]rune(suffix)) <= 3 && strings.ToUpper(suffix) == suffix {
			name = strings.TrimSpace(name[:i])
		}
	}
	key := searchKey(name)
	if alias, ok := teamAliases[key]; ok {
		return alias
	}
	return key
}

func normalizeCompetition(name string) string {
	key := searchKey(name)
	switch {
	case strings.Contains(key, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(key, "copa do brasil") || strings.Contains(key, "brazilian cup"):
		return "Copa do Brasil"
	case key == "serie a" || strings.Contains(key, "brasileirao") || strings.Contains(key, "brasileiro serie a"):
		return "Brasileirão Série A"
	case key == "serie b":
		return "Brasileirão Série B"
	case key == "serie c":
		return "Brasileirão Série C"
	default:
		return strings.TrimSpace(name)
	}
}

func competitionMatches(actual, query string) bool {
	if query == "" {
		return true
	}
	return searchKey(normalizeCompetition(actual)) == searchKey(normalizeCompetition(query))
}

var dateLayouts = []string{
	"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", "1/2/2006",
}

func parseDate(value string) (time.Time, error) {
	value = strings.TrimSpace(value)
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, value); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("unsupported date %q", value)
}

func parseInt(value string) (int, error) {
	value = strings.TrimSpace(value)
	if value == "" || value == "-" {
		return 0, nil
	}
	if i := strings.IndexByte(value, '.'); i >= 0 {
		value = value[:i]
	}
	return strconv.Atoi(value)
}

func rounded(value float64) float64 {
	return float64(int(value*10+0.5)) / 10
}
