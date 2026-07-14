// Package main — Brazilian Soccer MCP Server.
//
// normalize.go: Team-name normalization and multi-format date parsing.
//
// The provided Kaggle datasets are inconsistent: team names appear with state
// suffixes ("Palmeiras-SP"), country codes ("Nacional (URU)"), full legal names
// and Portuguese accents, while dates appear as ISO, ISO+time, and Brazilian
// DD/MM/YYYY. To answer cross-file queries reliably every team name is reduced
// to a canonical key (lowercase, accent-free, suffix-stripped) and every date is
// parsed through a list of known layouts. These helpers are the foundation the
// loader and query engine build on.
package main

import (
	"regexp"
	"strings"
	"time"
)

// parentheticals removes "(...)" segments such as country codes "(URU)" or
// long legal aliases "(antigo ...)".
var parentheticals = regexp.MustCompile(`\s*\([^)]*\)`)

// stateSuffix matches a trailing state/country abbreviation, optionally spaced
// with a dash: "-SP", " - RJ", "-EQU".
var stateSuffix = regexp.MustCompile(`\s*-\s*[A-Za-z]{2,3}\s*$`)

// multiSpace collapses runs of whitespace into a single space.
var multiSpace = regexp.MustCompile(`\s+`)

// accentMap maps accented runes common in Brazilian Portuguese (and broader
// Latin-1) to their unaccented ASCII equivalents.
var accentMap = map[rune]rune{
	'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y',
	'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A', 'Ä': 'A',
	'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
	'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
	'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O', 'Ö': 'O',
	'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
	'Ç': 'C', 'Ñ': 'N',
}

// stripAccents removes diacritical marks, turning "São" into "Sao".
func stripAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if repl, ok := accentMap[r]; ok {
			b.WriteRune(repl)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// NormalizeTeam reduces a raw team name to a canonical matching key:
// lowercase, accent-free, with parenthetical content and state/country
// suffixes removed and whitespace collapsed.
func NormalizeTeam(name string) string {
	s := parentheticals.ReplaceAllString(name, "")
	s = stateSuffix.ReplaceAllString(s, "")
	s = stripAccents(s)
	s = strings.ToLower(s)
	s = multiSpace.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// TeamsMatch reports whether two raw team names refer to the same team after
// normalization. An exact normalized-key match, or one key being a
// word-boundary substring of the other, is considered a match (so "Atlético"
// matches "Atlético Mineiro" only when fully contained).
func TeamsMatch(a, b string) bool {
	na, nb := NormalizeTeam(a), NormalizeTeam(b)
	if na == "" || nb == "" {
		return false
	}
	return na == nb
}

// dateLayouts lists the formats observed across the datasets, tried in order.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006",
	"2006.01.02",
}

// ParseDate parses a date string in any of the known dataset formats and
// reports whether parsing succeeded.
func ParseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}
