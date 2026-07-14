package main

import (
	"regexp"
	"strings"
	"time"
)

var stateSuffixRe = regexp.MustCompile(`-[A-Z]{2}$`)

// normalizeTeamName removes state suffix (e.g., "-SP") and trims whitespace.
func normalizeTeamName(name string) string {
	name = strings.TrimSpace(name)
	name = stateSuffixRe.ReplaceAllString(name, "")
	return strings.TrimSpace(name)
}

// teamShortNames maps short/alternate names to canonical base names (no state, lowercase).
var teamShortNames = map[string]string{
	"vasco":              "vasco da gama",
	"gremio":             "gremio",
	"atletico mineiro":   "atletico mineiro",
	"atletico paranaense": "atletico paranaense",
	"athletico paranaense": "atletico paranaense",
}

// teamNameKey returns a lowercase, accent-free, state-stripped key for fuzzy matching.
// This is used for match deduplication and team search.
func teamNameKey(name string) string {
	name = normalizeTeamName(name)
	name = removeAccents(name)
	name = strings.ToLower(name)
	// Normalize Athletico Paranaense name change (both spellings → "atletico")
	name = strings.ReplaceAll(name, "athletico", "atletico")
	// Resolve short names to canonical form
	if canonical, ok := teamShortNames[name]; ok {
		name = canonical
	}
	return name
}

// teamContains reports whether teamName contains query (case/accent/state-insensitive).
func teamContains(teamName, query string) bool {
	return strings.Contains(teamNameKey(teamName), teamNameKey(query))
}

// removeAccents replaces accented characters with ASCII equivalents.
func removeAccents(s string) string {
	replacements := map[rune]rune{
		'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
		'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
		'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
		'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
		'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
		'ç': 'c', 'ñ': 'n',
		'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
		'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
		'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
		'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
		'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
		'Ç': 'C', 'Ñ': 'N',
	}
	var b strings.Builder
	for _, r := range s {
		if rep, ok := replacements[r]; ok {
			b.WriteRune(rep)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

var dateFormats = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
	"2006-01-02T15:04:05",
}

// parseDate parses various date strings and returns YYYY-MM-DD.
func parseDate(s string) string {
	s = strings.TrimSpace(s)
	for _, f := range dateFormats {
		t, err := time.Parse(f, s)
		if err == nil {
			return t.Format("2006-01-02")
		}
	}
	return s
}

// teamGroupKey returns a standings grouping key that preserves the state suffix
// so "Atletico-MG" and "Atletico-PR" appear as distinct teams.
// Also normalizes known spelling/name variations across data sources.
func teamGroupKey(name string) string {
	k := strings.ToLower(removeAccents(strings.TrimSpace(name)))
	// Normalize Athletico Paranaense spelling variation
	k = strings.ReplaceAll(k, "athletico", "atletico")
	// Common short-name → state-bearing name aliases
	switch k {
	case "vasco":
		k = "vasco da gama-rj"
	case "vasco da gama":
		k = "vasco da gama-rj"
	case "gremio":
		k = "gremio-rs"
	case "atletico mineiro":
		k = "atletico-mg"
	case "atletico paranaense", "atletico-paranaense":
		k = "atletico-pr"
	case "flamengo":
		k = "flamengo-rj"
	case "fluminense":
		k = "fluminense-rj"
	case "botafogo":
		k = "botafogo-rj"
	case "santos":
		k = "santos-sp"
	case "corinthians", "sport club corinthians paulista":
		k = "corinthians-sp"
	case "palmeiras":
		k = "palmeiras-sp"
	case "sao paulo", "sao paulo fc":
		k = "sao paulo-sp"
	case "bahia":
		k = "bahia-ba"
	case "ceara":
		k = "ceara-ce"
	case "fortaleza":
		k = "fortaleza-ce"
	case "goias":
		k = "goias-go"
	case "internacional":
		k = "internacional-rs"
	case "cruzeiro":
		k = "cruzeiro-mg"
	case "csa":
		k = "csa-al"
	case "avai":
		k = "avai-sc"
	case "chapecoense":
		k = "chapecoense-sc"
	}
	return k
}

// matchKey returns a deduplication key for a match.
// Uses state-stripped names so "Palmeiras-SP" and "Palmeiras" (from different files)
// are treated as the same team for deduplication purposes.
func matchKey(m Match) string {
	return m.Date + "|" + teamNameKey(m.HomeTeam) + "|" + teamNameKey(m.AwayTeam) + "|" + competitionKey(m.Competition)
}

// canonicalTeamKey returns teamNameKey (state-stripped search key).
func canonicalTeamKey(name string) string {
	return teamNameKey(name)
}

// competitionKey normalizes a competition name to a canonical key.
func competitionKey(name string) string {
	k := strings.ToLower(strings.TrimSpace(removeAccents(name)))
	switch {
	case k == "" || k == "all":
		return "all"
	case strings.Contains(k, "libertadores"):
		return "libertadores"
	case strings.Contains(k, "copa do brasil") || strings.Contains(k, "cup"):
		return "copa_do_brasil"
	case strings.Contains(k, "brasileirao") || strings.Contains(k, "serie a") ||
		strings.Contains(k, "campeonato brasileiro") || strings.Contains(k, "brasileiro"):
		return "brasileirao"
	default:
		return k
	}
}
