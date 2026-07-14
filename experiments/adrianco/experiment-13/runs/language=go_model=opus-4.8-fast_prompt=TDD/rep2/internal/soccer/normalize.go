// Package soccer loads the provided Brazilian-soccer CSV datasets into an
// in-memory knowledge base and answers match, team, player, competition and
// statistical queries over them.
//
// This file implements team-name normalization. The datasets use several
// naming conventions for the same club ("Palmeiras-SP", "Palmeiras",
// "São Paulo" vs "Sao Paulo"), so all matching goes through NormalizeTeam /
// TeamsMatch to stay convention- and accent-insensitive.
package soccer

import (
	"strings"
	"unicode"
)

// foldRune maps an accented Latin rune to its unaccented ASCII equivalent.
// It returns the same rune unchanged when no folding applies.
func foldRune(r rune) rune {
	switch r {
	case 'á', 'à', 'â', 'ã', 'ä', 'å':
		return 'a'
	case 'é', 'è', 'ê', 'ë':
		return 'e'
	case 'í', 'ì', 'î', 'ï':
		return 'i'
	case 'ó', 'ò', 'ô', 'õ', 'ö':
		return 'o'
	case 'ú', 'ù', 'û', 'ü':
		return 'u'
	case 'ç':
		return 'c'
	case 'ñ':
		return 'n'
	}
	return r
}

// NormalizeTeam reduces a raw team name to space-separated, accent-folded,
// lowercase alphanumeric tokens. Any non-alphanumeric character (hyphens,
// parentheses, extra spaces) becomes a token separator.
func NormalizeTeam(name string) string {
	var b strings.Builder
	b.Grow(len(name))
	prevSpace := true // suppress leading separator
	for _, r := range strings.ToLower(name) {
		r = foldRune(r)
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			b.WriteRune(r)
			prevSpace = false
		} else if !prevSpace {
			b.WriteByte(' ')
			prevSpace = true
		}
	}
	return strings.TrimRight(b.String(), " ")
}

// teamTokens returns the normalized token set of a team name.
func teamTokens(name string) []string {
	n := NormalizeTeam(name)
	if n == "" {
		return nil
	}
	return strings.Fields(n)
}

// isSubset reports whether every token in sub appears in super.
func isSubset(sub, super []string) bool {
	set := make(map[string]bool, len(super))
	for _, t := range super {
		set[t] = true
	}
	for _, t := range sub {
		if !set[t] {
			return false
		}
	}
	return true
}

// TeamsMatch reports whether two raw team names refer to the same club,
// tolerating missing state suffixes and accent/case differences. Two names
// match when one's token set is a subset of the other's (and both are
// non-empty).
func TeamsMatch(a, b string) bool {
	ta, tb := teamTokens(a), teamTokens(b)
	if len(ta) == 0 || len(tb) == 0 {
		return false
	}
	if len(ta) <= len(tb) {
		return isSubset(ta, tb)
	}
	return isSubset(tb, ta)
}
