// Package soccer loads the bundled Brazilian football datasets and answers
// structured queries about matches, teams, players and competitions.
//
// normalize.go contains the team-name normalization helpers. The source CSV
// files use several different naming conventions for the same club, e.g.
// "Palmeiras-SP", "América - MG", "Nacional (URU)" and "Sao Paulo" vs
// "São Paulo". To match teams reliably we derive two values from a raw name:
//
//   - a cleaned *display* name (state / country suffixes stripped)
//   - a normalized *match key* (display name, accent-folded, lower-cased and
//     stripped of punctuation) used for equality and substring comparisons.
package soccer

import (
	"regexp"
	"strings"
)

// suffixState matches a trailing state/country code such as "-SP", " - MG" or
// "-EQU" that several datasets append to team names.
var suffixState = regexp.MustCompile(`\s*[-–]\s*[A-Za-z]{2,3}\s*$`)

// suffixParen matches a trailing parenthesised country code such as "(URU)".
var suffixParen = regexp.MustCompile(`\s*\([A-Za-z]{2,4}\)\s*$`)

// multiSpace collapses runs of whitespace into a single space.
var multiSpace = regexp.MustCompile(`\s+`)

// accentFold maps common Latin accented runes to their ASCII equivalents so
// that "São Paulo" and "Sao Paulo" compare equal. It intentionally avoids the
// golang.org/x/text dependency to keep the module self-contained.
var accentFold = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y', 'ÿ': 'y',
	'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A',
	'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
	'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
	'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
	'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
	'Ç': 'C', 'Ñ': 'N',
}

// CleanTeamName returns a display-friendly team name with trailing state or
// country suffixes and surrounding whitespace removed. It applies the suffix
// strippers repeatedly so that names carrying more than one suffix are fully
// cleaned.
func CleanTeamName(raw string) string {
	name := strings.TrimSpace(raw)
	for {
		stripped := suffixParen.ReplaceAllString(name, "")
		stripped = suffixState.ReplaceAllString(stripped, "")
		stripped = strings.TrimSpace(stripped)
		if stripped == name || stripped == "" {
			break
		}
		name = stripped
	}
	return multiSpace.ReplaceAllString(name, " ")
}

// dispSuffix tightens the spacing of a trailing state code so that
// "América - MG" renders as "América-MG".
var dispSuffix = regexp.MustCompile(`\s*-\s*([A-Za-z]{2,3})\s*$`)

// DisplayName returns a human-readable team name that, unlike CleanTeamName,
// retains the state/country suffix needed to tell same-named clubs apart
// (e.g. "Atlético-MG" vs "Atlético-GO"). It only normalises whitespace.
func DisplayName(raw string) string {
	s := multiSpace.ReplaceAllString(strings.TrimSpace(raw), " ")
	s = dispSuffix.ReplaceAllString(s, "-$1")
	return s
}

// suffixCapture extracts a trailing state/country code for disambiguation.
var suffixCapture = regexp.MustCompile(`[-–]\s*([A-Za-z]{2,3})\s*$|\(([A-Za-z]{2,4})\)\s*$`)

// teamSuffix returns the upper-cased trailing state/country code of a team name,
// or "" when there is none.
func teamSuffix(raw string) string {
	m := suffixCapture.FindStringSubmatch(strings.TrimSpace(raw))
	if m == nil {
		return ""
	}
	if m[1] != "" {
		return strings.ToUpper(m[1])
	}
	return strings.ToUpper(m[2])
}

// FoldAccents replaces accented Latin runes with their ASCII equivalents.
func FoldAccents(s string) string {
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

// keyPunct strips punctuation that is irrelevant for matching.
var keyPunct = regexp.MustCompile(`[._'/]`)

// NormalizeKey produces a canonical match key for a team name: cleaned,
// accent-folded, lower-cased, punctuation-stripped and space-collapsed.
func NormalizeKey(raw string) string {
	s := CleanTeamName(raw)
	s = FoldAccents(s)
	s = strings.ToLower(s)
	s = keyPunct.ReplaceAllString(s, " ")
	s = multiSpace.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// TeamMatches reports whether a team (identified by its raw name) satisfies a
// user-supplied query. An empty query matches everything.
//
// Matching is done on suffix-stripped, accent-folded keys: it succeeds on an
// exact match or a substring match in either direction, which lets "Flamengo"
// find "Flamengo-RJ" and "Sao Paulo" find "São Paulo". When the query itself
// carries a state/country suffix (e.g. "Atlético-MG"), the team's suffix must
// match too, so a disambiguated query does not also match "Atlético-GO".
func TeamMatches(teamRaw, query string) bool {
	q := NormalizeKey(query)
	if q == "" {
		return true
	}
	t := NormalizeKey(teamRaw)
	baseHit := t == q || strings.Contains(t, q) || strings.Contains(q, t)
	if !baseHit {
		return false
	}
	if qSuf := teamSuffix(query); qSuf != "" {
		return qSuf == teamSuffix(teamRaw)
	}
	return true
}
