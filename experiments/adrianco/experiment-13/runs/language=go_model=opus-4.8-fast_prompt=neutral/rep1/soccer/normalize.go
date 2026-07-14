// Package soccer implements an in-memory knowledge graph over the provided
// Brazilian soccer datasets (match results and FIFA player data) and the query
// and analysis primitives used by the MCP server.
//
// normalize.go: team/name normalization. The datasets name the same club in
// several ways ("Palmeiras-SP", "Palmeiras", "São Paulo" vs "Sao Paulo"), and
// crucially the state suffix is sometimes the ONLY thing distinguishing two
// real clubs ("Atlético-MG" / Mineiro vs "Athletico-PR" / Paranaense). So the
// matching key is computed in two stages: this file produces a (base, state)
// split and a loose base key; the Store (store.go) decides per club whether the
// state must be kept, by checking whether a base name is shared across states.
package soccer

import (
	"strings"
	"unicode"
)

// foldRune maps a single accented rune to its ASCII base. It covers the
// Latin-1 Supplement and a few Latin Extended-A code points that appear in
// Brazilian Portuguese club and player names (á à â ã ä ç é ê í ó ô õ ú ü ...).
func foldRune(r rune) rune {
	switch r {
	case 'á', 'à', 'â', 'ã', 'ä', 'å', 'ā', 'ă', 'ą':
		return 'a'
	case 'ç', 'ć', 'č':
		return 'c'
	case 'é', 'è', 'ê', 'ë', 'ē', 'ė', 'ę':
		return 'e'
	case 'í', 'ì', 'î', 'ï', 'ī', 'į':
		return 'i'
	case 'ñ', 'ń':
		return 'n'
	case 'ó', 'ò', 'ô', 'õ', 'ö', 'ø', 'ō':
		return 'o'
	case 'ú', 'ù', 'û', 'ü', 'ū', 'ů':
		return 'u'
	case 'ý', 'ÿ':
		return 'y'
	case 'š', 'ś':
		return 's'
	case 'ž', 'ź', 'ż':
		return 'z'
	}
	return r
}

// FoldAccents returns s with diacritics removed (accents folded to ASCII).
func FoldAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		b.WriteRune(foldRune(r))
	}
	return b.String()
}

// normalizeKey folds accents, lower-cases, drops punctuation and collapses
// internal whitespace, producing a stable matching key.
func normalizeKey(s string) string {
	s = FoldAccents(strings.ToLower(strings.TrimSpace(s)))
	var b strings.Builder
	b.Grow(len(s))
	prevSpace := false
	for _, r := range s {
		switch {
		case unicode.IsLetter(r) || unicode.IsDigit(r):
			b.WriteRune(r)
			prevSpace = false
		case r == ' ' || r == '-' || r == '_' || r == '.' || r == '/':
			if !prevSpace && b.Len() > 0 {
				b.WriteByte(' ')
				prevSpace = true
			}
		}
	}
	return strings.TrimSpace(b.String())
}

// NormalizeName returns a matching key for free text (player name, nationality).
func NormalizeName(name string) string { return normalizeKey(name) }

// stripParenthetical removes a trailing "(...)" group, e.g.
// "Nacional (URU)" -> "Nacional".
func stripParenthetical(s string) string {
	s = strings.TrimSpace(s)
	if i := strings.LastIndexByte(s, '('); i > 0 && strings.HasSuffix(s, ")") {
		return strings.TrimSpace(s[:i])
	}
	return s
}

// isStateCode reports whether tail looks like a 2-3 letter all-caps state or
// country abbreviation (SP, RJ, URU, EQU, ...).
func isStateCode(tail string) bool {
	tail = strings.TrimSpace(tail)
	if len(tail) < 2 || len(tail) > 3 {
		return false
	}
	for _, r := range tail {
		if !unicode.IsUpper(r) || !unicode.IsLetter(r) {
			return false
		}
	}
	return true
}

// splitBaseState separates a raw team name into a normalized base key and an
// upper-case state/country code (empty if none). It recognizes the trailing
// "-SP", " - MG" and " RN" forms used across the datasets.
//
//	"Atlético-MG"      -> ("atletico", "MG")
//	"América - RN"     -> ("america", "RN")
//	"America RN"       -> ("america", "RN")
//	"Nacional (URU)"   -> ("nacional", "URU")
//	"Flamengo"         -> ("flamengo", "")
func splitBaseState(raw string) (base, state string) {
	s := strings.TrimSpace(raw)

	// A parenthetical country code, e.g. "Nacional (URU)".
	if i := strings.LastIndexByte(s, '('); i > 0 && strings.HasSuffix(s, ")") {
		inner := strings.TrimSpace(s[i+1 : len(s)-1])
		s = strings.TrimSpace(s[:i])
		if isStateCode(inner) {
			state = inner
		}
	}

	for _, sep := range []string{" - ", "-", " "} {
		if i := strings.LastIndex(s, sep); i > 0 {
			tail := s[i+len(sep):]
			if isStateCode(tail) {
				if state == "" {
					state = strings.TrimSpace(tail)
				}
				s = strings.TrimSpace(s[:i])
				break
			}
		}
	}
	// Returns the raw normalized base (no canonicalization); callers apply
	// canonBase / aliases so that the original spelling can be inspected first.
	return normalizeKey(s), state
}

// canonBase normalizes spelling variants of the same base name. The notable
// case is "Athletico" (Paranaense) vs "Atlético" (Mineiro): both fold to a base
// that must agree across datasets, so "athletico" is canonicalized to
// "atletico" and disambiguated by state instead.
func canonBase(base string) string {
	if strings.HasPrefix(base, "athletico") {
		base = "atletico" + base[len("athletico"):]
	}
	return base
}

// preAlias resolves a raw base (before canonBase) directly to a club key, used
// where the original spelling carries information that canonicalization would
// erase. A bare "Athletico" (no state) appears in Copa Libertadores for
// Athletico Paranaense — the "h" spelling is unique to that club, so it maps to
// "atletico pr" rather than the ambiguous bare "atletico".
var preAlias = map[string]string{
	"athletico": "atletico pr",
}

// aliasKey maps spelled-out club names (used by the BR-Football dataset) onto
// the state-disambiguated key used elsewhere, so e.g. "Atletico Mineiro" and
// "Atlético-MG" resolve to the same club.
var aliasKey = map[string]string{
	"atletico mineiro":    "atletico mg",
	"atletico paranaense": "atletico pr",
	"atletico goianiense": "atletico go",
	"america mineiro":     "america mg",
}

// baseToKey applies the alias/canonicalization rules to a (base, state) pair,
// optionally keeping the state for ambiguous base names. ambiguous may be nil
// (loose mode: state is never appended), which yields the base-only key used
// for substring matching.
func baseToKey(rawBase, state string, ambiguous map[string]bool) string {
	if k, ok := preAlias[rawBase]; ok {
		return k
	}
	base := canonBase(rawBase)
	if k, ok := aliasKey[base]; ok {
		return k
	}
	if ambiguous[base] && state != "" {
		return base + " " + strings.ToLower(state)
	}
	return base
}

// NormalizeTeam returns the loose base key for a team name (state dropped). It
// is used for substring matching; exact identity uses Store.teamKey, which
// keeps the state for ambiguous base names.
func NormalizeTeam(name string) string {
	base, _ := splitBaseState(name)
	return baseToKey(base, "", nil)
}

// DisplayTeam returns a cleaned, human-readable team name: a trailing
// parenthetical is removed but the original accents, casing and any state
// suffix are preserved (the suffix can be the only disambiguator).
func DisplayTeam(name string) string {
	return strings.Join(strings.Fields(stripParenthetical(name)), " ")
}
