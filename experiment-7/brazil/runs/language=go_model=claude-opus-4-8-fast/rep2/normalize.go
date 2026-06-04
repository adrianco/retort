// Brazilian Soccer MCP Server
//
// File: normalize.go
// Responsibility: Text and value normalization helpers shared by the loader and
// query engine. Brazilian datasets are messy: team names carry state suffixes
// ("Palmeiras-SP"), country codes ("Nacional (URU)") and full legal names;
// dates come in ISO, Brazilian (DD/MM/YYYY) and timestamped forms; and text is
// UTF-8 with Portuguese accents. These helpers fold all of that into stable,
// comparable canonical forms so that "Grêmio", "GREMIO" and "Gremio-RS" all
// match each other.
package main

import (
	"regexp"
	"strconv"
	"strings"
	"time"
)

// accentReplacer folds the Portuguese accented characters that appear in the
// datasets to their ASCII equivalents. Done with a Replacer (rather than an
// x/text transform) to keep the server dependency-free.
var accentReplacer = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u",
	"ç", "c", "ñ", "n",
	"Á", "A", "À", "A", "Â", "A", "Ã", "A", "Ä", "A",
	"É", "E", "È", "E", "Ê", "E", "Ë", "E",
	"Í", "I", "Ì", "I", "Î", "I", "Ï", "I",
	"Ó", "O", "Ò", "O", "Ô", "O", "Õ", "O", "Ö", "O",
	"Ú", "U", "Ù", "U", "Û", "U", "Ü", "U",
	"Ç", "C", "Ñ", "N",
)

// stripAccents removes Portuguese diacritics from s.
func stripAccents(s string) string {
	return accentReplacer.Replace(s)
}

var (
	// parenRe matches parenthetical qualifiers like "(URU)" or "(antigo ...)".
	parenRe = regexp.MustCompile(`\s*\([^)]*\)`)
	// stateSuffixRe matches a trailing state/country code such as "-SP",
	// " - RJ" or "-URU" (2 or 3 upper-case letters at the end of the name).
	stateSuffixRe = regexp.MustCompile(`\s*-\s*[A-Z]{2,3}\s*$`)
	// spaceRe collapses runs of whitespace.
	spaceRe = regexp.MustCompile(`\s+`)
)

// cleanTeamName returns a human-friendly display name: parenthetical qualifiers
// and trailing state/country suffixes are removed but the original casing and
// accents are preserved (e.g. "Grêmio - RS" -> "Grêmio").
func cleanTeamName(raw string) string {
	s := strings.TrimSpace(raw)
	s = parenRe.ReplaceAllString(s, "")
	s = stateSuffixRe.ReplaceAllString(s, "")
	s = spaceRe.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// baseAndState splits a raw team name into its accent-folded, lower-cased base
// (no state suffix) and the upper-case state/country code embedded in the name
// ("" if none). For example "Atlético-MG" -> ("atletico", "MG") and
// "Nacional (URU)" -> ("nacional", "").
func baseAndState(raw string) (base, state string) {
	s := strings.TrimSpace(raw)
	s = parenRe.ReplaceAllString(s, "")
	if m := stateSuffixRe.FindString(s); m != "" {
		state = strings.ToUpper(strings.Trim(m, " -"))
		s = stateSuffixRe.ReplaceAllString(s, "")
	}
	return normKey(s), state
}

// teamBaseKey returns the suffix-stripped canonical key used for loose,
// state-insensitive matching (so "Flamengo" matches "Flamengo-RJ").
func teamBaseKey(raw string) string {
	base, _ := baseAndState(raw)
	return base
}

// teamFullKey returns the canonical key including a state suffix, which keeps
// distinct same-named clubs apart (Atlético-MG vs Atlético-PR). When the name
// itself carries no suffix, the supplied state column (if any) is used. This is
// the identity used when computing standings, where conflation would corrupt
// the table.
func teamFullKey(raw, state string) string {
	base, suf := baseAndState(raw)
	if suf == "" {
		suf = strings.ToUpper(strings.TrimSpace(state))
	}
	if suf != "" {
		return base + "-" + strings.ToLower(suf)
	}
	return base
}

// teamDisplay returns the display spelling, appending a synthesized "-STATE"
// suffix when the name lacks one but a state column distinguishes the club.
func teamDisplay(raw, state string) string {
	name := cleanTeamName(raw)
	_, suf := baseAndState(raw)
	if suf == "" {
		suf = strings.ToUpper(strings.TrimSpace(state))
	}
	if suf != "" {
		name = name + "-" + suf
	}
	return name
}

// teamKey is retained for callers (e.g. player club matching) that only need a
// loose, suffix-insensitive canonical key.
func teamKey(raw string) string { return teamBaseKey(raw) }

// normKey folds an arbitrary string (player name, nationality, club, query
// term) into the same accent-free lower-case space-collapsed form used for
// matching. Unlike teamKey it does not strip state suffixes.
func normKey(raw string) string {
	s := stripAccents(strings.TrimSpace(raw))
	s = strings.ToLower(s)
	s = spaceRe.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// dateLayouts are tried in order by parseDate. Order matters: more specific
// (timestamped) layouts come first.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006", // Brazilian DD/MM/YYYY
	"01/02/2006 15:04:05",
}

// parseDate parses the several date formats found across the datasets. It
// returns the parsed time and whether parsing succeeded.
func parseDate(raw string) (time.Time, bool) {
	s := strings.TrimSpace(raw)
	if s == "" || strings.EqualFold(s, "NA") {
		return time.Time{}, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// atoi parses an integer, tolerating surrounding whitespace, quotes and the
// trailing ".0" that some numeric CSV columns carry. Returns 0/false on
// failure so callers can decide whether the value is meaningful.
func atoi(raw string) (int, bool) {
	s := strings.TrimSpace(strings.Trim(raw, `"`))
	if s == "" || strings.EqualFold(s, "NA") {
		return 0, false
	}
	if i := strings.IndexByte(s, '.'); i >= 0 {
		s = s[:i]
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0, false
	}
	return n, true
}

// itoa is a tiny wrapper used by Match.signature to avoid importing strconv
// there.
func itoa(n int) string { return strconv.Itoa(n) }
