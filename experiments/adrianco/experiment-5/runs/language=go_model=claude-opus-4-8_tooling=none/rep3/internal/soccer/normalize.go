// Context: team-name normalization. The datasets spell the same club many
// different ways. We derive a stable lowercase, accent-free, suffix-free key
// used for all team/club matching, while keeping a human-readable display name.
package soccer

import (
	"regexp"
	"strings"
)

// accentMap folds common Portuguese (and Spanish) accented letters to ASCII so
// that "São Paulo" and "Sao Paulo" produce the same key without pulling in the
// golang.org/x/text dependency.
var accentMap = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y',
	'Á': 'a', 'À': 'a', 'Â': 'a', 'Ã': 'a', 'Ä': 'a',
	'É': 'e', 'È': 'e', 'Ê': 'e', 'Ë': 'e',
	'Í': 'i', 'Ì': 'i', 'Î': 'i', 'Ï': 'i',
	'Ó': 'o', 'Ò': 'o', 'Ô': 'o', 'Õ': 'o', 'Ö': 'o',
	'Ú': 'u', 'Ù': 'u', 'Û': 'u', 'Ü': 'u',
	'Ç': 'c', 'Ñ': 'n',
}

// foldAccents returns s with accented letters folded to ASCII.
func foldAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if folded, ok := accentMap[r]; ok {
			b.WriteRune(folded)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

var (
	// parenthetical content: "(URU)", "(antigo Esporte Clube Barreira)"
	reParen = regexp.MustCompile(`\([^)]*\)`)
	// trailing state/country suffix: "-SP", " - RJ", " SP", "-EQU"
	reSuffix = regexp.MustCompile(`(?i)[\s-]+[a-z]{2,3}$`)
	// anything that is not a letter or digit
	reNonAlnum = regexp.MustCompile(`[^a-z0-9]+`)
)

// knownState is the set of Brazilian state abbreviations plus the South-American
// country codes used in the Libertadores file. Only these are stripped as
// suffixes so that real name fragments (e.g. "Athletico") survive.
var knownState = map[string]bool{
	"ac": true, "al": true, "ap": true, "am": true, "ba": true, "ce": true,
	"df": true, "es": true, "go": true, "ma": true, "mt": true, "ms": true,
	"mg": true, "pa": true, "pb": true, "pr": true, "pe": true, "pi": true,
	"rj": true, "rn": true, "rs": true, "ro": true, "rr": true, "sc": true,
	"sp": true, "se": true, "to": true,
	// country codes seen in Libertadores_Matches.csv
	"uru": true, "equ": true, "arg": true, "par": true, "bol": true,
	"chi": true, "col": true, "per": true, "ven": true, "bra": true,
	"mex": true, "eua": true,
}

// cleanTeamName strips state/country suffixes and parenthetical notes, producing
// a tidy display name (accents preserved). It also returns the stripped state
// abbreviation when one was recognised.
func cleanTeamName(raw string) (display, state string) {
	s := strings.TrimSpace(raw)
	s = reParen.ReplaceAllString(s, "")
	s = strings.TrimSpace(s)

	// Strip a trailing recognised state/country suffix.
	if loc := reSuffix.FindStringIndex(s); loc != nil {
		suffix := strings.ToLower(strings.Trim(s[loc[0]:], " -"))
		if knownState[foldAccents(suffix)] {
			state = strings.ToUpper(suffix)
			s = strings.TrimSpace(s[:loc[0]])
		}
	}
	s = strings.Join(strings.Fields(s), " ") // collapse whitespace
	return s, state
}

// normKey returns the canonical matching key for a team or club name.
func normKey(raw string) string {
	display, _ := cleanTeamName(raw)
	s := strings.ToLower(foldAccents(display))
	s = reNonAlnum.ReplaceAllString(s, "")
	return aliasKey(s)
}

// teamAlias maps normalized variants onto a single canonical key so that
// differently-worded references to the same club unify across datasets.
var teamAlias = map[string]string{
	"atleticomg":        "atleticomineiro",
	"atletico":          "atleticomineiro",
	"atleticopr":        "athleticoparanaense",
	"athleticopr":       "athleticoparanaense",
	"athletico":         "athleticoparanaense",
	"clubeathletico":    "athleticoparanaense",
	"saopaulofc":        "saopaulo",
	"vascodagama":       "vasco",
	"vascodagamarj":     "vasco",
	"botafogorj":        "botafogo",
	"botafogofr":        "botafogo",
	"atleticogo":        "atleticogoianiense",
	"redbullbragantino": "bragantino",
	"clubebragantino":   "bragantino",
	"gremio":            "gremio",
	"ecvitoria":         "vitoria",
	"saojose":           "saojose",
}

// aliasKey resolves an alias to its canonical form, if any.
func aliasKey(k string) string {
	if canon, ok := teamAlias[k]; ok {
		return canon
	}
	return k
}

// matchesQuery reports whether a normalized team/club key satisfies a user's
// search term. An empty query matches everything. We accept exact equality and,
// for terms of length >= 3, substring containment so partial names work.
func matchesQuery(key, query string) bool {
	q := normKey(query)
	if q == "" {
		return true
	}
	if key == q {
		return true
	}
	if len(q) >= 3 && strings.Contains(key, q) {
		return true
	}
	return false
}
