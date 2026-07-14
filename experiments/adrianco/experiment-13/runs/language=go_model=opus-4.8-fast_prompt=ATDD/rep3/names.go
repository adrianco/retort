// Context: Team/competition name normalization for the Brazilian Soccer MCP
// server. The bundled datasets refer to the same club in many ways — with a
// state suffix ("Palmeiras-SP"), a spaced country code ("Nacional (URU)"), with
// or without Portuguese accents ("São Paulo" vs "Sao Paulo"). To match a user's
// query against the data consistently we reduce every name to a canonical
// "norm key" (lower-case, accent-free, suffix-free) for comparison, while
// keeping a human-friendly display form (suffix stripped, accents preserved).
// Competition names are mapped onto a small set of canonical labels so a query
// like "Libertadores" or "Serie A" resolves to the right competition.
package main

import (
	"regexp"
	"strings"
)

// trailing state/country qualifiers: " - MG", "-SP", " (URU)", "-EQU".
// The capture group isolates the state/country code itself.
var (
	parenSuffix = regexp.MustCompile(`\s*\(([A-Za-z]{2,4})\)\s*$`)
	dashSuffix  = regexp.MustCompile(`\s*-\s*([A-Za-z]{2,3})\s*$`)
	multiSpace  = regexp.MustCompile(`\s+`)
)

// accentFold maps accented Latin runes (as used in Brazilian Portuguese) to
// their plain ASCII equivalents.
var accentFold = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y',
}

func foldAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if repl, ok := accentFold[r]; ok {
			b.WriteRune(repl)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// stripSuffix removes a trailing state/country qualifier from a team name.
func stripSuffix(name string) string {
	name = strings.TrimSpace(name)
	if m := parenSuffix.ReplaceAllString(name, ""); m != name {
		return strings.TrimSpace(m)
	}
	if m := dashSuffix.ReplaceAllString(name, ""); m != name {
		return strings.TrimSpace(m)
	}
	return name
}

// displayTeam returns the human-friendly display form of a team name (the base
// name with accents kept and the state/country suffix removed).
func displayTeam(raw string) string {
	return multiSpace.ReplaceAllString(stripSuffix(raw), " ")
}

// teamState extracts the state/country code from a team name ("Atlético-MG" ->
// "mg", "Nacional (URU)" -> "uru"), or "" when there is none. Distinguishing on
// this code is what keeps Atlético-MG, Atlético-PR and Atlético-GO apart even
// though they share the base name "Atlético".
func teamState(raw string) string {
	raw = strings.TrimSpace(raw)
	if m := parenSuffix.FindStringSubmatch(raw); m != nil {
		return foldAccents(strings.ToLower(m[1]))
	}
	if m := dashSuffix.FindStringSubmatch(raw); m != nil {
		return foldAccents(strings.ToLower(m[1]))
	}
	return ""
}

// normTeam returns the canonical comparison key for a team's base name (no
// state suffix, lower-cased, accent-free).
func normTeam(raw string) string {
	s := strings.ToLower(displayTeam(raw))
	s = foldAccents(s)
	s = multiSpace.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// teamQuery is a parsed team reference used to match against stored matches. A
// query without a state ("Flamengo") matches any state; a query that carries a
// state ("Atlético-MG") matches only that exact club.
type teamQuery struct {
	base     string
	state    string
	hasState bool
}

func parseTeamQuery(raw string) teamQuery {
	st := teamState(raw)
	return teamQuery{base: normTeam(raw), state: st, hasState: st != ""}
}

// matchesSide reports whether this query identifies the given (base, state).
func (q teamQuery) matchesSide(base, state string) bool {
	if q.base != base {
		return false
	}
	if q.hasState {
		return q.state == state
	}
	return true
}

// normText lower-cases and folds accents for loose contains-matching of free
// text fields (player names, clubs, nationalities).
func normText(raw string) string {
	s := strings.ToLower(strings.TrimSpace(raw))
	s = foldAccents(s)
	return multiSpace.ReplaceAllString(s, " ")
}

// resolveCompetition maps a free-text competition query onto a canonical label.
// It returns "" when the query is blank, and the folded query itself when it
// matches no known competition (so it simply won't match any stored matches).
func resolveCompetition(query string) string {
	q := normText(query)
	switch {
	case q == "":
		return ""
	case strings.Contains(q, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(q, "copa do brasil") || q == "cup" || q == "copa":
		return "Copa do Brasil"
	case strings.Contains(q, "brasileir") || q == "serie a" || q == "seria a":
		return "Brasileirão"
	case q == "serie b":
		return "Serie B"
	case q == "serie c":
		return "Serie C"
	default:
		return query
	}
}
