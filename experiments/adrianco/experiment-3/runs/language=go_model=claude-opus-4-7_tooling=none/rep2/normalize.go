// normalize.go handles the messy team/club name variations described in the
// specification (state suffixes, country codes, accents, full names) so that
// "Palmeiras-SP", "Palmeiras" and "palmeiras" all match consistently.
package main

import (
	"strconv"
	"strings"
)

// accentMap folds Portuguese (and a few neighbouring-language) accented runes
// down to their plain ASCII equivalent.
var accentMap = map[rune]rune{
	'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y', 'ÿ': 'y',
}

// stripAccents replaces accented runes with their ASCII base form.
func stripAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if rep, ok := accentMap[r]; ok {
			b.WriteRune(rep)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// normalizeTeamKey produces a canonical lookup key for a team or club name.
// It lower-cases, strips accents, drops parenthetical text and collapses all
// punctuation to single spaces. The state code is deliberately *kept* (so
// "Palmeiras-SP" -> "palmeiras sp") because it disambiguates clubs that share
// a name, e.g. Atlético-MG, Atlético-GO and Atlético-PR. Substring matching
// still lets a bare "Palmeiras" query find "palmeiras sp".
func normalizeTeamKey(name string) string {
	s := stripAccents(strings.ToLower(strings.TrimSpace(name)))

	// Drop any parenthetical qualifier, e.g. "Nacional (URU)".
	for {
		i := strings.Index(s, "(")
		if i < 0 {
			break
		}
		j := strings.Index(s[i:], ")")
		if j < 0 {
			s = s[:i]
			break
		}
		s = s[:i] + " " + s[i+j+1:]
	}

	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if r == ' ' || (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			b.WriteRune(r)
		} else {
			b.WriteRune(' ')
		}
	}
	return strings.Join(strings.Fields(b.String()), " ")
}

// normalizeText canonicalizes free text (player names, nationalities) for
// case- and accent-insensitive substring search.
func normalizeText(s string) string {
	return strings.Join(strings.Fields(stripAccents(strings.ToLower(strings.TrimSpace(s)))), " ")
}

// keyContains reports whether the normalized haystack key contains the
// normalized needle as a substring. An empty needle never matches.
func keyContains(haystackKey, needle string) bool {
	n := normalizeTeamKey(needle)
	if n == "" {
		return false
	}
	return strings.Contains(haystackKey, n)
}

// itoa is a tiny helper used across formatting code.
func itoa(n int) string { return strconv.Itoa(n) }
