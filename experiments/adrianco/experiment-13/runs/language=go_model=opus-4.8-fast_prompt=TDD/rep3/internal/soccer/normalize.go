// Context: Brazilian Soccer MCP Server.
// File: normalize.go
// Purpose: Team-name normalization helpers. The provided datasets use
// inconsistent naming conventions — state suffixes ("Palmeiras-SP"), country
// codes ("Nacional (URU)"), accents ("Grêmio") and full club names ("Sport
// Club Corinthians Paulista"). These helpers produce a canonical key used for
// matching, a clean display name, and a fuzzy query-to-team matcher.
package soccer

import (
	"regexp"
	"strings"
	"unicode"

	"golang.org/x/text/runes"
	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"
)

// suffixPattern matches trailing state/country qualifiers such as "-SP",
// " - MG", " (URU)" and "-EQU". Codes are always uppercase in the datasets, so
// requiring uppercase avoids mangling hyphenated club names like "Colo-Colo".
var suffixPattern = regexp.MustCompile(`(?:\s*\([A-Z]{2,4}\)|\s*-\s*[A-Z]{2,4})\s*$`)

var spacePattern = regexp.MustCompile(`\s+`)

// stripSuffix removes a single trailing state/country qualifier.
func stripSuffix(s string) string {
	return suffixPattern.ReplaceAllString(strings.TrimSpace(s), "")
}

// removeAccents strips diacritical marks (ã -> a, ê -> e, ç -> c).
func removeAccents(s string) string {
	t := transform.Chain(norm.NFD, runes.Remove(runes.In(unicode.Mn)), norm.NFC)
	out, _, err := transform.String(t, s)
	if err != nil {
		return s
	}
	return out
}

// CleanTeamName trims whitespace and removes a trailing state/country suffix
// while preserving accents and casing, suitable for display.
func CleanTeamName(raw string) string {
	return strings.TrimSpace(stripSuffix(raw))
}

// NormalizeTeamName produces a lowercase, accent-free, suffix-free key for
// consistent matching across datasets.
func NormalizeTeamName(raw string) string {
	s := CleanTeamName(raw)
	s = removeAccents(s)
	s = strings.ToLower(s)
	s = spacePattern.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// TeamMatches reports whether a free-text query refers to the given team name.
// Matching is accent- and suffix-insensitive and succeeds when either
// normalized form contains the other (so "Corinthians" matches "Sport Club
// Corinthians Paulista"). An empty query never matches.
func TeamMatches(query, team string) bool {
	q := NormalizeTeamName(query)
	if q == "" {
		return false
	}
	t := NormalizeTeamName(team)
	if t == "" {
		return false
	}
	return strings.Contains(t, q) || strings.Contains(q, t)
}
