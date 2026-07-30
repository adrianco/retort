package main

import (
	"strings"
	"unicode"
)

// canonicalText performs case, accent, punctuation, and whitespace folding.
// It deliberately keeps words intact: it is also used for player and club
// substring searches, where aggressive token removal would be surprising.
func canonicalText(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	var b strings.Builder
	lastSpace := false
	for _, r := range value {
		switch r {
		case 'á', 'à', 'â', 'ã', 'ä':
			r = 'a'
		case 'ç':
			r = 'c'
		case 'é', 'ê', 'ë':
			r = 'e'
		case 'í', 'ï':
			r = 'i'
		case 'ó', 'ô', 'õ', 'ö':
			r = 'o'
		case 'ú', 'ü':
			r = 'u'
		case 'ñ':
			r = 'n'
		}
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			b.WriteRune(r)
			lastSpace = false
		} else if !lastSpace {
			b.WriteByte(' ')
			lastSpace = true
		}
	}
	return strings.TrimSpace(b.String())
}

// canonicalTeam makes the common short and long versions of Brazilian club
// names comparable. Unknown teams still receive a stable accent-insensitive
// form, which keeps the loader useful for international competitions too.
func canonicalTeam(value string) string {
	v := canonicalText(value)
	// Resolve state-qualified Atlético names before removing the state suffix.
	// The spelling changed over time, so both forms occur in the supplied CSVs.
	switch v {
	case "atletico mg":
		return "atletico mineiro"
	case "atletico pr", "athletico pr":
		return "athletico paranaense"
	}
	words := strings.Fields(v)
	if len(words) > 1 && len(words[len(words)-1]) == 2 {
		// Dataset one appends a state code, e.g. Palmeiras-SP.
		allLetters := true
		for _, r := range words[len(words)-1] {
			if !unicode.IsLetter(r) {
				allLetters = false
			}
		}
		if allLetters {
			v = strings.Join(words[:len(words)-1], " ")
		}
	}
	aliases := []struct{ contains, name string }{
		{"corinthians", "corinthians"}, {"flamengo", "flamengo"},
		{"fluminense", "fluminense"}, {"palmeiras", "palmeiras"},
		{"sao paulo", "sao paulo"}, {"santos", "santos"},
		{"vasco", "vasco da gama"}, {"botafogo", "botafogo"},
		{"gremio", "gremio"}, {"internacional", "internacional"},
		{"cruzeiro", "cruzeiro"}, {"atletico mineiro", "atletico mineiro"},
		{"athletico paranaense", "athletico paranaense"}, {"atletico paranaense", "athletico paranaense"},
		{"athletico", "athletico paranaense"},
		{"bahia", "bahia"}, {"fortaleza", "fortaleza"}, {"sport recife", "sport"},
		{"goias", "goias"}, {"coritiba", "coritiba"}, {"vitoria", "vitoria"},
	}
	for _, alias := range aliases {
		if strings.Contains(v, alias.contains) {
			return alias.name
		}
	}
	return v
}

func canonicalCompetition(value string) string {
	v := canonicalText(value)
	switch {
	case strings.Contains(v, "libertadores"):
		return "libertadores"
	case strings.Contains(v, "copa do brasil"):
		return "copa do brasil"
	case strings.Contains(v, "brasileirao"), strings.Contains(v, "brasileiro"), v == "serie a":
		return "brasileirao"
	default:
		return v
	}
}

func displayCompetition(canonical string) string {
	switch canonical {
	case "brasileirao":
		return "Brasileirão"
	case "copa do brasil":
		return "Copa do Brasil"
	case "libertadores":
		return "Copa Libertadores"
	default:
		return canonical
	}
}

func canonicalNationality(value string) string {
	v := canonicalText(value)
	switch v {
	case "brazil", "brazilian", "brasileiro", "brasileira":
		return "brazil"
	default:
		return v
	}
}
