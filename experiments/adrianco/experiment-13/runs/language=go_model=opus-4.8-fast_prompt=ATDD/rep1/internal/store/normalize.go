package store

import (
	"regexp"
	"strconv"
	"strings"
	"time"
)

// brazilianStates is the set of two-letter UF codes used as team-name suffixes.
var brazilianStates = map[string]bool{
	"AC": true, "AL": true, "AP": true, "AM": true, "BA": true, "CE": true,
	"DF": true, "ES": true, "GO": true, "MA": true, "MT": true, "MS": true,
	"MG": true, "PA": true, "PB": true, "PR": true, "PE": true, "PI": true,
	"RJ": true, "RN": true, "RS": true, "RO": true, "RR": true, "SC": true,
	"SP": true, "SE": true, "TO": true,
}

// accentFolds maps accented Portuguese/Spanish runes to their ASCII base.
var accentFolds = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y', 'ÿ': 'y',
}

var (
	parenRe     = regexp.MustCompile(`\s*\([^)]*\)`)
	nonAlnumRe  = regexp.MustCompile(`[^a-z0-9]+`)
	stateSuffix = regexp.MustCompile(`[\s-]+([a-zA-Z]{2})$`)
)

// foldAccents replaces accented runes with their ASCII equivalents.
func foldAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if rep, ok := accentFolds[r]; ok {
			b.WriteRune(rep)
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

// CleanTeamName returns a human-friendly display name with parenthetical
// qualifiers and trailing state suffixes removed (e.g. "Palmeiras-SP" ->
// "Palmeiras", "Nacional (URU)" -> "Nacional", "América - MG" -> "América").
func CleanTeamName(name string) string {
	s := strings.TrimSpace(name)
	s = parenRe.ReplaceAllString(s, "")
	s = strings.TrimSpace(s)
	if m := stateSuffix.FindStringSubmatch(s); m != nil {
		if brazilianStates[strings.ToUpper(m[1])] {
			s = strings.TrimSpace(s[:len(s)-len(m[0])])
		}
	}
	s = strings.TrimRight(s, " -")
	return strings.TrimSpace(s)
}

// NormalizeTeam produces a canonical matching key for a team name: accent-folded,
// lower-cased, with state/country suffixes and punctuation removed.
func NormalizeTeam(name string) string {
	s := foldAccents(strings.ToLower(strings.TrimSpace(name)))
	s = parenRe.ReplaceAllString(s, "")
	if m := stateSuffix.FindStringSubmatch(s); m != nil {
		if brazilianStates[strings.ToUpper(m[1])] {
			s = s[:len(s)-len(m[0])]
		}
	}
	s = nonAlnumRe.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// parseStateSuffix extracts a trailing two-letter Brazilian state (UF) code
// from a team name, e.g. "Atletico-MG" -> "mg". Returns "" when absent.
func parseStateSuffix(name string) string {
	s := foldAccents(strings.ToLower(strings.TrimSpace(name)))
	s = parenRe.ReplaceAllString(s, "")
	if m := stateSuffix.FindStringSubmatch(s); m != nil {
		uf := strings.ToUpper(m[1])
		if brazilianStates[uf] {
			return strings.ToLower(uf)
		}
	}
	return ""
}

// identityKey combines a base name key with a state code to form a stable team
// identity. Teams with no known state use the base key alone.
func identityKey(base, state string) string {
	if state == "" {
		return base
	}
	return base + "|" + state
}

// splitIdentity returns the base key and state code of an identity key.
func splitIdentity(key string) (base, state string) {
	if i := strings.IndexByte(key, '|'); i >= 0 {
		return key[:i], key[i+1:]
	}
	return key, ""
}

// teamNameMatches reports whether a stored team key matches a user query.
// Exact normalised equality is preferred, with substring matching as a
// flexible fallback so partial names ("Atletico") still resolve.
func teamNameMatches(storedKey, query string) bool {
	q := NormalizeTeam(query)
	if q == "" {
		return false
	}
	base, _ := splitIdentity(storedKey)
	if base == q {
		return true
	}
	return strings.Contains(base, q) || strings.Contains(q, base)
}

// containsFold reports whether needle occurs within haystack, ignoring case and
// accents. Used for player name/club/nationality search.
func containsFold(haystack, needle string) bool {
	h := foldAccents(strings.ToLower(haystack))
	n := foldAccents(strings.ToLower(strings.TrimSpace(needle)))
	if n == "" {
		return false
	}
	return strings.Contains(h, n)
}

// NormalizeCompetition maps the many spellings of a competition to a canonical
// name. Unknown competitions are returned trimmed but otherwise unchanged.
func NormalizeCompetition(name string) string {
	k := NormalizeTeam(name)
	switch {
	case strings.Contains(k, "brasileir"),
		strings.Contains(k, "campeonato brasileiro"),
		strings.Contains(k, "serie a"):
		return CompBrasileirao
	case strings.Contains(k, "copa do brasil"),
		strings.Contains(k, "brazilian cup"):
		return CompCopaDoBrasil
	case strings.Contains(k, "libertadores"):
		return CompLibertadores
	}
	return strings.TrimSpace(name)
}

// dateLayouts are tried in order when parsing the many date formats in the data.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006",
	"02/01/2006 15:04:05",
}

// ParseDate parses a date string in any of the supported formats.
func ParseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false
	}
	for _, layout := range dateLayouts {
		if tm, err := time.Parse(layout, s); err == nil {
			return tm, true
		}
	}
	return time.Time{}, false
}

// parseGoal parses a goal count that may be quoted, blank, or float-formatted
// ("1", "1.0", ""). Returns the integer value and whether it was valid.
func parseGoal(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	if i, err := strconv.Atoi(s); err == nil {
		return i, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

// parseIntLoose parses an int from a possibly-messy string, returning 0 on failure.
func parseIntLoose(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	if i, err := strconv.Atoi(s); err == nil {
		return i
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return 0
}
