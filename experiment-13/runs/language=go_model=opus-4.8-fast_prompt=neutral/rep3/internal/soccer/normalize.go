// Package soccer implements the in-memory knowledge graph and query engine
// behind the Brazilian Soccer MCP server.
//
// normalize.go contains the text-normalization helpers that make matching
// robust across the many naming conventions used by the source datasets:
//
//   - State suffixes:     "Palmeiras-SP", "América - MG"
//   - Country codes:      "Nacional (URU)", "Barcelona-EQU"
//   - Parentheticals:     "Boavista Sport Club (antigo ...) - RJ"
//   - Accents / cedilla:  "São Paulo", "Grêmio", "Avaí", "Fortaleza"
//   - Full vs short names: "Sport Club Corinthians Paulista" vs "Corinthians"
//
// Every team name is reduced to a canonical lookup *key* (lower-cased,
// accent-folded, punctuation-stripped) so that the variants above collapse
// onto a single node in the graph.
package soccer

import (
	"regexp"
	"strings"
)

// accentFolder maps accented Latin characters commonly found in Brazilian
// Portuguese onto their ASCII equivalents. Implemented as a Replacer to keep
// the package dependency-free (no golang.org/x/text required).
var accentFolder = strings.NewReplacer(
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

var (
	// reParenthetical removes any "(...)" group, e.g. "(URU)" or "(antigo ...)".
	reParenthetical = regexp.MustCompile(`\s*\([^)]*\)`)
	// reStateSuffix removes a trailing state/country code such as "-SP",
	// " - MG" or "-EQU" (2-3 upper-case letters at the very end).
	reStateSuffix = regexp.MustCompile(`\s*-\s*[A-Z]{2,3}\s*$`)
	// reCountryCode captures a trailing parenthesized code, e.g. "(URU)".
	reCountryCode = regexp.MustCompile(`\s*\(([A-Z]{2,4})\)\s*$`)
	// reStateCode captures a trailing "-XX" / " - XX" state code.
	reStateCode = regexp.MustCompile(`\s*-\s*([A-Z]{2,3})\s*$`)
	// reNonAlnum collapses anything that is not a letter, digit or space.
	reNonAlnum = regexp.MustCompile(`[^a-z0-9 ]+`)
	// reSpaces collapses runs of whitespace.
	reSpaces = regexp.MustCompile(`\s+`)
)

// splitTeam decomposes a raw team name into a canonical base key, a region
// code (state or country, lower-cased, possibly empty) and a human-friendly
// display name. The region lets us distinguish clubs that share a base name and
// differ only by state — e.g. Atlético-MG, Atlético-PR and Atlético-GO.
//
//	"Atletico-MG"    -> base "atletico",  region "mg", display "Atletico"
//	"Nacional (URU)" -> base "nacional",  region "uru", display "Nacional"
//	"Flamengo-RJ"    -> base "flamengo",  region "rj", display "Flamengo"
func splitTeam(raw string) (base, region, display string) {
	s := strings.TrimSpace(strings.Trim(strings.TrimSpace(raw), `"`))
	if m := reCountryCode.FindStringSubmatch(s); m != nil {
		region = strings.ToLower(m[1])
		s = s[:len(s)-len(m[0])]
	} else if m := reStateCode.FindStringSubmatch(s); m != nil {
		region = strings.ToLower(m[1])
		s = s[:len(s)-len(m[0])]
	}
	// Drop any remaining parenthetical noise, e.g. "(antigo ...)".
	s = reParenthetical.ReplaceAllString(s, "")
	display = strings.TrimSpace(reSpaces.ReplaceAllString(s, " "))

	base = foldAccents(strings.ToLower(display))
	base = reNonAlnum.ReplaceAllString(base, " ")
	base = strings.TrimSpace(reSpaces.ReplaceAllString(base, " "))
	return base, region, display
}

// foldAccents returns s with Portuguese accents removed.
func foldAccents(s string) string { return accentFolder.Replace(s) }

// CleanTeamName returns a human-friendly display name for a raw team string:
// surrounding quotes/whitespace are trimmed and parenthetical groups plus a
// trailing state/country code are stripped.
//
//	"Palmeiras-SP"                       -> "Palmeiras"
//	"América - MG"                       -> "América"
//	"Nacional (URU)"                     -> "Nacional"
//	"Boavista Sport Club (antigo ...) - RJ" -> "Boavista Sport Club"
func CleanTeamName(raw string) string {
	s := strings.TrimSpace(strings.Trim(strings.TrimSpace(raw), `"`))
	s = reParenthetical.ReplaceAllString(s, "")
	s = reStateSuffix.ReplaceAllString(s, "")
	s = reSpaces.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// TeamKey returns the canonical lookup key for a team name. The key is
// lower-cased, accent-folded and stripped of punctuation so that all naming
// variants of the same club collapse onto one value.
//
//	"Palmeiras-SP"  -> "palmeiras"
//	"São Paulo"     -> "sao paulo"
//	"Grêmio"        -> "gremio"
func TeamKey(raw string) string {
	s := CleanTeamName(raw)
	s = foldAccents(strings.ToLower(s))
	s = reNonAlnum.ReplaceAllString(s, " ")
	s = reSpaces.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// normText lower-cases and accent-folds free text for loose comparisons.
func normText(s string) string {
	return strings.TrimSpace(foldAccents(strings.ToLower(s)))
}

// NormalizeCompetition maps the various competition labels used across the
// datasets onto a single canonical name.
func NormalizeCompetition(raw string) string {
	s := normText(raw)
	switch {
	case strings.Contains(s, "serie a") || s == "brasileirao" || strings.Contains(s, "brasileir") && !strings.Contains(s, "serie b") && !strings.Contains(s, "serie c"):
		return CompBrasileiraoA
	case strings.Contains(s, "serie b"):
		return CompBrasileiraoB
	case strings.Contains(s, "serie c"):
		return CompBrasileiraoC
	case strings.Contains(s, "copa do brasil"):
		return CompCopaDoBrasil
	case strings.Contains(s, "libertadores"):
		return CompLibertadores
	}
	return strings.TrimSpace(raw)
}

// competitionMatches reports whether a stored competition name satisfies a
// (possibly fuzzy) user-supplied competition filter.
func competitionMatches(stored, query string) bool {
	if query == "" {
		return true
	}
	canon := NormalizeCompetition(query)
	if strings.EqualFold(stored, canon) {
		return true
	}
	return strings.Contains(normText(stored), normText(query))
}
