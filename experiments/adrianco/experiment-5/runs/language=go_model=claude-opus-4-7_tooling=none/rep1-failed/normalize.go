package main

import (
	"regexp"
	"strings"
)

// accentMap maps accented runes (mostly Portuguese) to their ASCII equivalents.
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
	'ç': 'c', 'Ç': 'C',
	'ñ': 'n', 'Ñ': 'N',
}

// stripAccents converts Portuguese diacritics to ASCII equivalents.
func stripAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if mapped, ok := accentMap[r]; ok {
			b.WriteRune(mapped)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// stateSuffix matches a trailing " - XX", "-XX", " XX" two-letter state code
// (e.g., "Palmeiras-SP", "América - MG").
var stateSuffix = regexp.MustCompile(`(?i)\s*[-–]?\s*\(?([A-Z]{2,3})\)?\s*$`)

// parenSuffix removes trailing parentheticals such as "(URU)" or
// "(antigo Esporte Clube Barreira)" etc.
var parenSuffix = regexp.MustCompile(`\s*\([^)]*\)\s*$`)

// nonAlnum collapses non-alphanumeric runs.
var nonAlnum = regexp.MustCompile(`[^a-z0-9]+`)

// teamAliases maps a normalized canonical key to a display/canonical name and
// covers common alternative spellings.
var teamAliases = map[string]string{
	"flamengo":        "Flamengo",
	"fluminense":      "Fluminense",
	"palmeiras":       "Palmeiras",
	"santos":          "Santos",
	"corinthians":     "Corinthians",
	"saopaulo":        "São Paulo",
	"saopaulofc":      "São Paulo",
	"gremio":          "Grêmio",
	"internacional":   "Internacional",
	"atleticomineiro": "Atlético Mineiro",
	"atleticomg":      "Atlético Mineiro",
	"atleticopr":      "Athletico Paranaense",
	"athleticopr":     "Athletico Paranaense",
	"athletico":       "Athletico Paranaense",
	"botafogo":        "Botafogo",
	"vasco":           "Vasco da Gama",
	"vascodagama":     "Vasco da Gama",
	"cruzeiro":        "Cruzeiro",
	"bahia":           "Bahia",
	"fortaleza":       "Fortaleza",
	"ceara":           "Ceará",
	"sport":           "Sport Recife",
	"sportrecife":     "Sport Recife",
	"coritiba":        "Coritiba",
	"avai":            "Avaí",
	"chapecoense":     "Chapecoense",
	"goias":           "Goiás",
	"americamg":       "América Mineiro",
	"americamineiro":  "América Mineiro",
	"red bullbragantino": "Red Bull Bragantino",
	"redbullbragantino":  "Red Bull Bragantino",
	"bragantino":         "Red Bull Bragantino",
}

// normalizeTeam returns a normalized key for a team that strips accents,
// state suffixes, parenthetical qualifiers, punctuation, and case.
func normalizeTeam(name string) string {
	if name == "" {
		return ""
	}
	s := stripAccents(name)
	s = parenSuffix.ReplaceAllString(s, "")
	s = stateSuffix.ReplaceAllString(s, "")
	s = strings.ToLower(s)
	s = nonAlnum.ReplaceAllString(s, "")
	return s
}

// canonicalTeamName returns a display-friendly canonical name when possible,
// falling back to the input.
func canonicalTeamName(name string) string {
	key := normalizeTeam(name)
	if v, ok := teamAliases[key]; ok {
		return v
	}
	// Otherwise, strip the parenthetical/state suffix from the original.
	s := parenSuffix.ReplaceAllString(name, "")
	s = stateSuffix.ReplaceAllString(s, "")
	return strings.TrimSpace(s)
}

// teamsMatch reports whether two raw team strings refer to the same club.
func teamsMatch(a, b string) bool {
	na, nb := normalizeTeam(a), normalizeTeam(b)
	if na == "" || nb == "" {
		return false
	}
	if na == nb {
		return true
	}
	// Allow substring matches for fuzzy cases ("santos" inside "santosfc").
	if strings.Contains(na, nb) || strings.Contains(nb, na) {
		return true
	}
	// Alias bridging: if both map to the same canonical alias, equal.
	if av, ok := teamAliases[na]; ok {
		if bv, ok := teamAliases[nb]; ok && av == bv {
			return true
		}
	}
	return false
}

// normalizeText strips accents and lowercases for general fuzzy search.
func normalizeText(s string) string {
	return strings.ToLower(stripAccents(s))
}
