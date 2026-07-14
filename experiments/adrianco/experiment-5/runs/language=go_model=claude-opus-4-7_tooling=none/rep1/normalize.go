package main

import (
	"strings"
)

// NormalizeTeam returns a canonical lower-case key used to match team names across CSVs.
// Brazilian datasets use multiple naming conventions: "Palmeiras-SP", "Palmeiras",
// "Sociedade Esportiva Palmeiras". For teams that share a short base name with another
// club (Atletico-MG vs Atletico-PR), an alias lookup is performed BEFORE stripping the
// state suffix so the two stay distinct.
func NormalizeTeam(name string) string {
	if name == "" {
		return ""
	}
	s := name

	// Drop parenthesized region/country codes: "Nacional (URU)" -> "Nacional".
	for {
		i := strings.IndexByte(s, '(')
		if i < 0 {
			break
		}
		j := strings.IndexByte(s[i:], ')')
		if j < 0 {
			break
		}
		s = s[:i] + s[i+j+1:]
	}

	s = stripAccents(s)
	s = strings.ToLower(s)
	s = strings.Join(strings.Fields(s), " ")
	s = strings.TrimSpace(s)

	// Try alias with the state suffix intact (preserves Atletico-MG vs Atletico-PR).
	if v, ok := aliasMap[s]; ok {
		return v
	}
	// Normalize spaced "atletico - mg" to "atletico-mg" for alias.
	sCompact := strings.ReplaceAll(s, " - ", "-")
	if v, ok := aliasMap[sCompact]; ok {
		return v
	}

	// Strip the trailing state suffix and try alias again, then return.
	stripped := stripStateSuffix(s)
	if v, ok := aliasMap[stripped]; ok {
		return v
	}
	return stripped
}

func stripStateSuffix(s string) string {
	t := strings.TrimRight(s, " \t")
	if len(t) < 3 {
		return s
	}
	idx := strings.LastIndex(t, "-")
	if idx >= 0 && idx >= len(t)-4 {
		suffix := strings.TrimSpace(t[idx+1:])
		if len(suffix) == 2 && isLetters(suffix) {
			return strings.TrimRight(t[:idx], " ")
		}
	}
	return s
}

func isLetters(s string) bool {
	for _, r := range s {
		if !((r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z')) {
			return false
		}
	}
	return len(s) > 0
}

// accentMap covers Portuguese characters that appear in team / player names.
var accentMap = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
	'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
	'ñ': 'n', 'Ñ': 'N',
	'ç': 'c', 'Ç': 'C',
}

func stripAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if m, ok := accentMap[r]; ok {
			b.WriteRune(m)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// aliasMap maps known team-name variants to a canonical short key.
// Keys are post-accent-strip, lower-case. Entries with state suffix are checked
// BEFORE the suffix is stripped, so "atletico-mg" maps differently from "atletico-pr".
var aliasMap = map[string]string{
	// State-suffix forms must come before suffix stripping.
	"atletico-mg":      "atletico mineiro",
	"atletico-pr":      "athletico paranaense",
	"athletico-pr":     "athletico paranaense",
	"atletico mg":      "atletico mineiro",
	"atletico pr":      "athletico paranaense",
	"athletico pr":     "athletico paranaense",
	"america-mg":       "america mineiro",
	"america-rn":       "america rn",
	"america mg":       "america mineiro",
	"america rn":       "america rn",
	"americano-rj":     "americano",
	"juventude-rs":     "juventude",

	// Long-form names.
	"sport club corinthians paulista":  "corinthians",
	"sport club corinthians":           "corinthians",
	"sport club do recife":             "sport",
	"sport recife":                     "sport",
	"clube de regatas do flamengo":     "flamengo",
	"sao paulo fc":                     "sao paulo",
	"sociedade esportiva palmeiras":    "palmeiras",
	"santos fc":                        "santos",
	"santos futebol clube":             "santos",
	"clube atletico mineiro":           "atletico mineiro",
	"club de regatas vasco da gama":    "vasco",
	"vasco da gama":                    "vasco",
	"fluminense football club":         "fluminense",
	"gremio foot-ball porto alegrense": "gremio",
}
