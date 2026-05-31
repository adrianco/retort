// Context
// -------
// Normalization helpers used throughout the package. The Kaggle datasets spell
// team names inconsistently ("Palmeiras-SP", "Palmeiras", "São Paulo" vs
// "Sao Paulo", "Nacional (URU)") and store dates in several formats. These
// helpers produce stable display names and canonical match keys so the same
// real-world team or fixture collapses to one entity regardless of source.
package soccer

import (
	"regexp"
	"strconv"
	"strings"
	"time"
)

// stateSuffix matches a trailing Brazilian state ("-SP", " - RJ") or country
// code ("(URU)", "-EQU") suffix appended to a team name.
var stateSuffix = regexp.MustCompile(`(?:\s*[-–]\s*[A-Za-z]{2,3}|\s*\([A-Za-z]{2,4}\))\s*$`)

// stateCapture extracts the state/country code from a trailing suffix.
var stateCapture = regexp.MustCompile(`(?:[-–]\s*([A-Za-z]{2,3})|\(([A-Za-z]{2,4})\))\s*$`)

// StateFromName returns the trailing state/country code embedded in a team name
// (e.g. "Atletico-MG" -> "MG", "Nacional (URU)" -> "URU"), or "" if none.
func StateFromName(raw string) string {
	m := stateCapture.FindStringSubmatch(strings.TrimSpace(raw))
	if m == nil {
		return ""
	}
	if m[1] != "" {
		return strings.ToUpper(m[1])
	}
	return strings.ToUpper(m[2])
}

// diacritics maps accented Latin characters to their ASCII equivalents so that
// canonical keys ignore Portuguese/Spanish accents.
var diacritics = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y', 'ÿ': 'y',
}

// stripDiacritics replaces accented characters with their ASCII base form.
func stripDiacritics(s string) string {
	var b strings.Builder
	for _, r := range s {
		if repl, ok := diacritics[unicodeLower(r)]; ok {
			b.WriteRune(repl)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// unicodeLower lowercases a single rune covering the accent table.
func unicodeLower(r rune) rune {
	if r >= 'A' && r <= 'Z' {
		return r + 32
	}
	switch r {
	case 'Á':
		return 'á'
	case 'À':
		return 'à'
	case 'Â':
		return 'â'
	case 'Ã':
		return 'ã'
	case 'É':
		return 'é'
	case 'Ê':
		return 'ê'
	case 'Í':
		return 'í'
	case 'Ó':
		return 'ó'
	case 'Ô':
		return 'ô'
	case 'Õ':
		return 'õ'
	case 'Ú':
		return 'ú'
	case 'Ü':
		return 'ü'
	case 'Ç':
		return 'ç'
	case 'Ñ':
		return 'ñ'
	}
	return r
}

// NormalizeTeamName trims whitespace and removes a trailing state/country
// suffix, returning the human-friendly display name (accents preserved).
func NormalizeTeamName(raw string) string {
	s := strings.TrimSpace(raw)
	s = stateSuffix.ReplaceAllString(s, "")
	return strings.TrimSpace(s)
}

// TeamKey returns the canonical matching key for a team: lowercased, accent and
// suffix stripped, and reduced to alphanumeric characters. Two spellings of the
// same club ("Palmeiras-SP" / "Palmeiras", "São Paulo" / "Sao Paulo") share a
// key.
func TeamKey(raw string) string {
	s := NormalizeTeamName(raw)
	s = stripDiacritics(strings.ToLower(s))
	var b strings.Builder
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// teamMatchesQuery reports whether a stored team name matches a user query.
// Matching is symmetric substring containment on canonical keys so that
// "Corinthians" matches "Sport Club Corinthians Paulista" and vice-versa.
func teamMatchesQuery(query, team string) bool {
	q := TeamKey(query)
	t := TeamKey(team)
	if q == "" || t == "" {
		return false
	}
	return q == t || strings.Contains(t, q) || strings.Contains(q, t)
}

// dateLayouts are tried in order when parsing the various source date formats.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006",
	"01/02/2006 15:04:05",
}

// ParseDate parses a date string in any of the supported source formats. The
// boolean return is true when a time-of-day component was present.
func ParseDate(s string) (time.Time, bool, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			hasTime := strings.Contains(layout, "15:04")
			return t, hasTime, true
		}
	}
	return time.Time{}, false, false
}

// parseIntLoose parses an integer that may be formatted as a float ("2.0") or
// quoted ("2"). Empty / unparseable values yield 0, ok=false.
func parseIntLoose(s string) (int, bool) {
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
