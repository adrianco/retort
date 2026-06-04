// Package store: team-name normalization helpers.
//
// Context:
//   - Datasets disagree on team naming. Examples seen in the CSVs:
//     "Palmeiras-SP", "América - MG", "Nacional (URU)", "Barcelona-EQU",
//     "São Paulo", "Sport Club Corinthians Paulista".
//   - To match a user query like "Flamengo" against any of these, we fold
//     accents, lowercase, and strip trailing state/country suffixes, then
//     compare on the resulting key (with a substring fallback for full names).
package store

import (
	"regexp"
	"strings"
)

// accentFold maps accented Latin characters common in Brazilian Portuguese to
// their ASCII equivalents.
var accentFold = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n',
	'Á': 'a', 'À': 'a', 'Â': 'a', 'Ã': 'a', 'Ä': 'a',
	'É': 'e', 'È': 'e', 'Ê': 'e', 'Ë': 'e',
	'Í': 'i', 'Ì': 'i', 'Î': 'i', 'Ï': 'i',
	'Ó': 'o', 'Ò': 'o', 'Ô': 'o', 'Õ': 'o', 'Ö': 'o',
	'Ú': 'u', 'Ù': 'u', 'Û': 'u', 'Ü': 'u',
	'Ç': 'c', 'Ñ': 'n',
}

// foldAccents replaces accented runes with ASCII equivalents.
func foldAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if folded, ok := accentFold[r]; ok {
			b.WriteRune(folded)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// suffixRe strips trailing state/country designators such as "-SP", " - MG",
// "(URU)", "/RS" at the end of a team name.
var suffixRe = regexp.MustCompile(`(?i)\s*[-/(]\s*[a-z]{2,3}\s*\)?$`)

// spaceRe collapses runs of whitespace.
var spaceRe = regexp.MustCompile(`\s+`)

// NormalizeTeam produces a canonical match key for a team name: accents folded,
// lowercased, state/country suffix removed, whitespace collapsed.
func NormalizeTeam(name string) string {
	s := foldAccents(name)
	s = strings.ToLower(strings.TrimSpace(s))
	// Strip a trailing state/country suffix (possibly more than one segment).
	for {
		stripped := suffixRe.ReplaceAllString(s, "")
		if stripped == s {
			break
		}
		s = strings.TrimSpace(stripped)
	}
	s = spaceRe.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// suffixCodeRe captures a trailing state/country code from a raw team name,
// e.g. "Palmeiras-SP" -> "SP", "Nacional (URU)" -> "URU".
var suffixCodeRe = regexp.MustCompile(`(?i)[-/(]\s*([a-z]{2,3})\s*\)?$`)

// extractSuffixCode returns the lowercased trailing state/country code embedded
// in a raw team name, or "" if none.
func extractSuffixCode(name string) string {
	if m := suffixCodeRe.FindStringSubmatch(strings.TrimSpace(name)); m != nil {
		return strings.ToLower(m[1])
	}
	return ""
}

// baseAliases canonicalizes base club names that differ in spelling across the
// authoritative datasets so the same club merges. State codes (appended by
// TeamKey) still keep genuinely distinct clubs apart (e.g. Atlético-MG vs the
// Paranaense club, which both fold to "atletico" but carry MG/PR).
var baseAliases = map[string]string{
	"athletico":     "atletico", // Athletico Paranaense spelled "Atletico-PR" elsewhere
	"vasco da gama": "vasco",
	"america":       "america", // identity; kept explicit as documentation anchor
}

// TeamKey produces a grouping/dedup key that disambiguates same-named clubs in
// different states (e.g. Atlético-MG vs Atlético-PR). It combines the
// accent-folded, suffix-stripped base name with a state code taken from the
// explicit state column when present, otherwise recovered from a suffix in the
// raw name.
func TeamKey(name, state string) string {
	base := NormalizeTeam(name)
	if alias, ok := baseAliases[base]; ok {
		base = alias
	}
	st := strings.ToLower(strings.TrimSpace(state))
	if st == "" {
		st = extractSuffixCode(name)
	}
	if st != "" {
		return base + "-" + st
	}
	return base
}

// TeamMatches reports whether a dataset team name matches a user query. It
// returns true on exact normalized equality or when one normalized name
// contains the other (so "corinthians" matches "sport club corinthians
// paulista", and "palmeiras" matches "palmeiras-sp").
func TeamMatches(teamName, query string) bool {
	nt := NormalizeTeam(teamName)
	nq := NormalizeTeam(query)
	if nq == "" {
		return false
	}
	if nt == nq {
		return true
	}
	return strings.Contains(nt, nq) || strings.Contains(nq, nt)
}

// containsFold reports whether haystack contains needle, both accent-folded and
// lowercased. Used for free-text fields (player name, club, nationality).
func containsFold(haystack, needle string) bool {
	if needle == "" {
		return true
	}
	return strings.Contains(
		strings.ToLower(foldAccents(haystack)),
		strings.ToLower(foldAccents(needle)),
	)
}
