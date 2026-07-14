package main

import (
	"strings"
	"unicode"
)

// normalizeTeam strips state suffixes and lowercases for consistent matching.
// E.g. "Palmeiras-SP" -> "palmeiras", "Boavista - RJ" -> "boavista"
func normalizeTeam(name string) string {
	name = strings.TrimSpace(name)

	// Remove trailing " - UF" patterns (2-letter state)
	if idx := strings.LastIndex(name, " - "); idx > 0 {
		suffix := strings.TrimSpace(name[idx+3:])
		if len(suffix) == 2 && isAllUpper(suffix) {
			name = name[:idx]
		}
	}

	// Remove trailing "-UF" patterns (e.g. "Palmeiras-SP")
	if idx := strings.LastIndex(name, "-"); idx > 0 {
		suffix := name[idx+1:]
		if len(suffix) == 2 && isAllUpper(suffix) {
			name = name[:idx]
		}
	}

	// Remove parenthetical country codes like "(URU)", "(ARG)", "(EQU)"
	if idx := strings.Index(name, "("); idx > 0 {
		name = strings.TrimSpace(name[:idx])
	}

	name = strings.TrimSpace(name)
	return strings.ToLower(removeDiacritics(name))
}

func isAllUpper(s string) bool {
	for _, r := range s {
		if !unicode.IsUpper(r) {
			return false
		}
	}
	return len(s) > 0
}

// teamMatches returns true if query is found within the normalized team name.
func teamMatches(normalized, query string) bool {
	q := strings.ToLower(removeDiacritics(strings.TrimSpace(query)))
	return strings.Contains(normalized, q)
}

// diacriticsMap maps accented characters to ASCII equivalents
var diacriticsMap = strings.NewReplacer(
	"à", "a", "á", "a", "â", "a", "ã", "a", "ä", "a", "å", "a",
	"è", "e", "é", "e", "ê", "e", "ë", "e",
	"ì", "i", "í", "i", "î", "i", "ï", "i",
	"ò", "o", "ó", "o", "ô", "o", "õ", "o", "ö", "o",
	"ù", "u", "ú", "u", "û", "u", "ü", "u",
	"ý", "y", "ÿ", "y",
	"ç", "c",
	"ñ", "n",
	"À", "a", "Á", "a", "Â", "a", "Ã", "a", "Ä", "a", "Å", "a",
	"È", "e", "É", "e", "Ê", "e", "Ë", "e",
	"Ì", "i", "Í", "i", "Î", "i", "Ï", "i",
	"Ò", "o", "Ó", "o", "Ô", "o", "Õ", "o", "Ö", "o",
	"Ù", "u", "Ú", "u", "Û", "u", "Ü", "u",
	"Ý", "y",
	"Ç", "c",
	"Ñ", "n",
)

func removeDiacritics(s string) string {
	return diacriticsMap.Replace(s)
}
