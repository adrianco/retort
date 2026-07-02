package soccer

import (
	"regexp"
	"strings"
	"unicode"

	"golang.org/x/text/runes"
	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"
)

// brazilianStates are the two-letter Brazilian state (UF) abbreviations used
// as suffixes on team names in several of the source datasets, e.g.
// "Flamengo-RJ" or "América - MG".
var brazilianStates = map[string]bool{
	"ac": true, "al": true, "ap": true, "am": true, "ba": true, "ce": true,
	"df": true, "es": true, "go": true, "ma": true, "mt": true, "ms": true,
	"mg": true, "pa": true, "pb": true, "pr": true, "pe": true, "pi": true,
	"rj": true, "rn": true, "rs": true, "ro": true, "rr": true, "sc": true,
	"sp": true, "se": true, "to": true,
}

var stateSuffixPattern = regexp.MustCompile(`\s*-\s*([A-Za-z]{2})$`)

// teamAliases maps a normalized (but not yet alias-resolved) team key to a
// canonical key, so that well known clubs referred to by different names
// across datasets resolve to the same identity.
var teamAliases = map[string]string{
	"atletico mineiro":    "atletico",
	"atletico paranaense": "athletico",
}

// stripAccents removes diacritical marks (accents) from a string, e.g.
// "São Paulo" -> "Sao Paulo", "Grêmio" -> "Gremio".
func stripAccents(s string) string {
	t := transform.Chain(norm.NFD, runes.Remove(runes.In(unicode.Mn)), norm.NFC)
	out, _, err := transform.String(t, s)
	if err != nil {
		return s
	}
	return out
}

// NormalizeTeamKey produces a canonical, comparable key for a team name as
// it appears in any of the source datasets. It strips accents, trailing
// Brazilian state (UF) suffixes, punctuation, and collapses whitespace, then
// resolves a small set of known aliases so that the same club referenced
// under different names produces the same key.
func NormalizeTeamKey(name string) string {
	s := stripAccents(name)
	s = strings.ReplaceAll(s, ".", "")
	s = strings.ToLower(strings.TrimSpace(s))
	s = strings.Join(strings.Fields(s), " ")

	if m := stateSuffixPattern.FindStringSubmatch(s); m != nil {
		if brazilianStates[strings.ToLower(m[1])] {
			s = strings.TrimSpace(s[:len(s)-len(m[0])])
		}
	}

	if canonical, ok := teamAliases[s]; ok {
		return canonical
	}
	return s
}
