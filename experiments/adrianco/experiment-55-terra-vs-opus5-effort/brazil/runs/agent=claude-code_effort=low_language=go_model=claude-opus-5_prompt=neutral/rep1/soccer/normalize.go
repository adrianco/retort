// Package soccer loads the Kaggle Brazilian football datasets into an in-memory
// knowledge graph and answers match, team, player, competition and statistical
// queries over it.
//
// normalize.go handles the messy parts of the raw data: Brazilian team names
// appear with state suffixes ("Palmeiras-SP", "América - MG"), with full legal
// names ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ") and with or
// without accents ("São Paulo" vs "Sao Paulo"). Everything is folded down to a
// canonical key so the same club found in six different CSV files resolves to a
// single node.
package soccer

import (
	"strings"
	"unicode"
)

// accentFold maps the accented runes that occur in Brazilian Portuguese club
// and player names onto their ASCII equivalents.
var accentFold = map[rune]rune{
	'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y',
}

// FoldAccents lowercases s and strips Portuguese diacritics.
func FoldAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range strings.ToLower(s) {
		if f, ok := accentFold[r]; ok {
			b.WriteRune(f)
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

// brazilianStates is the set of two-letter state codes used as team suffixes.
var brazilianStates = map[string]bool{
	"ac": true, "al": true, "am": true, "ap": true, "ba": true, "ce": true,
	"df": true, "es": true, "go": true, "ma": true, "mg": true, "ms": true,
	"mt": true, "pa": true, "pb": true, "pe": true, "pi": true, "pr": true,
	"rj": true, "rn": true, "ro": true, "rr": true, "rs": true, "sc": true,
	"se": true, "sp": true, "to": true,
}

// foreignSuffixes are country markers used for non-Brazilian clubs in the
// Libertadores data, e.g. "Nacional (URU)" or "Barcelona-EQU".
var foreignSuffixes = map[string]bool{
	"uru": true, "arg": true, "par": true, "chi": true, "bol": true,
	"equ": true, "col": true, "ven": true, "per": true, "mex": true,
	"bra": true,
}

// clubNoise are generic club words that carry no identifying information.
var clubNoise = map[string]bool{
	"esporte": true, "esportiva": true, "esportivo": true, "clube": true,
	"futebol": true, "club": true, "associacao": true, "atletica": true,
	"sociedade": true, "regatas": true, "sporting": true,
	"de": true, "do": true, "da": true, "e": true,
	"ec": true, "fc": true, "sc": true, "ac": true, "cr": true, "se": true,
	"ce": true, "aa": true, "cf": true,
	// "sport" is noise inside a longer name ("Boavista Sport Club") but is the
	// club itself when it leads ("Sport-PE", "Sport Recife"), so baseKey only
	// drops it in non-leading position.
	"sport": true,
}

// ambiguousBases are club names that are only unique together with their
// state/country suffix (Atlético-MG vs Atlético-PR, América-MG vs América-RN).
var ambiguousBases = map[string]bool{
	"atletico": true, "athletico": true, "america": true, "nacional": true,
	"internacional": false, "barcelona": true, "san lorenzo": false,
}

// aliases maps a canonical key produced by the folding rules onto the key of
// the club it is really the same as.
var aliases = map[string]string{
	// Athletico Paranaense is spelled both ways across the datasets.
	"athletico paranaense": "athletico|pr",
	"athletico":            "athletico|pr",
	"atletico paranaense":  "athletico|pr",
	"athletico|pr":         "athletico|pr",
	"atletico|pr":          "athletico|pr",
	"atletico mineiro":     "atletico|mg",
	"atletico goianiense":  "atletico|go",
	"atletico goiniense":   "atletico|go",
	"america mineiro":      "america|mg",
	"sport recife":         "sport",
	"sport club recife":    "sport",
	"vasco da gama":        "vasco",
	"vasco gama":           "vasco",
	"botafogo rj":          "botafogo",
	"red bull bragantino":  "bragantino",
	"redbull bragantino":   "bragantino",
	"bragantino rb":        "bragantino",
	"sao paulo fc":         "sao paulo",
	"corinthians paulista": "corinthians",
	"gremio":               "gremio",
	"portuguesa rj":        "portuguesa|rj",
	"cuiaba":               "cuiaba",
	"chapecoense":          "chapecoense",
	"athletic":             "athletic",
}

// splitStateSuffix pulls a trailing state or country code off a raw team name.
// It accepts "Palmeiras-SP", "América - MG" and "Nacional (URU)".
func splitStateSuffix(raw string) (name, state string) {
	name = strings.TrimSpace(raw)

	// Trailing "(URU)" style country marker.
	if i := strings.LastIndex(name, "("); i > 0 && strings.HasSuffix(name, ")") {
		inner := FoldAccents(strings.TrimSpace(name[i+1 : len(name)-1]))
		if foreignSuffixes[inner] || brazilianStates[inner] {
			return strings.TrimSpace(name[:i]), strings.ToUpper(inner)
		}
	}

	// Trailing "-XX" / " - XX" state marker.
	if i := strings.LastIndex(name, "-"); i > 0 {
		tail := FoldAccents(strings.TrimSpace(name[i+1:]))
		if brazilianStates[tail] || foreignSuffixes[tail] {
			return strings.TrimSpace(name[:i]), strings.ToUpper(tail)
		}
	}
	return name, ""
}

// stripParenthetical removes "(antigo Esporte Clube Barreira)" style asides.
func stripParenthetical(s string) string {
	for {
		i := strings.Index(s, "(")
		if i < 0 {
			break
		}
		j := strings.Index(s[i:], ")")
		if j < 0 {
			s = s[:i]
			break
		}
		s = s[:i] + " " + s[i+j+1:]
	}
	return strings.TrimSpace(s)
}

// baseKey folds a team name (with any suffix already removed) to its core
// identifying tokens.
func baseKey(name string) string {
	folded := FoldAccents(stripParenthetical(name))
	var toks []string
	for _, tok := range strings.FieldsFunc(folded, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	}) {
		if clubNoise[tok] && len(toks) > 0 {
			continue // a generic club word, but never the leading one
		}
		if clubNoise[tok] && tok != "sport" {
			continue
		}
		toks = append(toks, tok)
	}
	if len(toks) == 0 {
		// The whole name was noise words; fall back to the folded string.
		return strings.Join(strings.Fields(folded), " ")
	}
	return strings.Join(toks, " ")
}

// splitBaseState folds a raw name to its base tokens plus any state code. A
// state written without punctuation ("América MG") is only split off when the
// remaining base is one of the names that needs a state to be unique, so that
// genuinely distinct clubs like "Fluminense PI" are not merged into Fluminense.
func splitBaseState(raw string) (base, state string) {
	name, state := splitStateSuffix(raw)
	base = baseKey(name)
	if state == "" {
		if i := strings.LastIndex(base, " "); i > 0 {
			head, tail := base[:i], base[i+1:]
			// Only strip a bare state word when the club is one that needs the
			// state to be unique, or when enough of the name remains to still
			// identify it ("Vasco Da Gama RJ"). Otherwise a two word club such
			// as "Fluminense PI" would collapse into Fluminense.
			if brazilianStates[tail] && (ambiguousBases[head] || strings.Contains(head, " ")) {
				return head, strings.ToUpper(tail)
			}
		}
	}
	return base, state
}

// CanonicalTeam converts any raw team spelling into a stable key. Names that
// are only unique with their state (Atlético-MG) keep the state in the key.
func CanonicalTeam(raw string) string {
	base, state := splitBaseState(raw)
	if base == "" {
		return ""
	}
	if target, ok := aliases[base]; ok {
		return target
	}
	if ambiguousBases[base] && state != "" {
		key := base + "|" + strings.ToLower(state)
		if target, ok := aliases[key]; ok {
			return target
		}
		return key
	}
	return base
}

// TeamState returns the state/country code embedded in a raw team name, if any.
func TeamState(raw string) string {
	_, state := splitStateSuffix(raw)
	return state
}

// DisplayTeam produces a human friendly name: parentheticals removed, state
// suffix kept only when it disambiguates.
func DisplayTeam(raw string) string {
	base, state := splitBaseState(raw)
	name, _ := splitStateSuffix(raw)
	name = strings.Join(strings.Fields(stripParenthetical(name)), " ")
	if state != "" && ambiguousBases[base] {
		// Re-attach the state in a single canonical spelling.
		if i := strings.LastIndex(strings.ToLower(name), " "+strings.ToLower(state)); i > 0 {
			name = name[:i]
		}
		return name + "-" + state
	}
	return name
}

// TeamMatches reports whether a user supplied query names the given canonical
// team. It accepts exact canonical hits plus prefix/substring matches on the
// token sequence so "Atletico" finds "atletico|mg" and "Flamengo RJ" finds
// "flamengo".
func TeamMatches(query, canonical string) bool {
	q := CanonicalTeam(query)
	if q == "" || canonical == "" {
		return false
	}
	if q == canonical {
		return true
	}
	qBase, _, _ := strings.Cut(q, "|")
	cBase, _, _ := strings.Cut(canonical, "|")
	if qBase == cBase {
		// One side carried a state, the other did not.
		return !strings.Contains(q, "|") || !strings.Contains(canonical, "|")
	}
	// Substring fallback on whole tokens, e.g. "sao paulo" vs "sao paulo fc".
	return containsTokens(cBase, qBase) || containsTokens(qBase, cBase)
}

// containsTokens reports whether all tokens of sub appear in order in s.
func containsTokens(s, sub string) bool {
	st, subt := strings.Fields(s), strings.Fields(sub)
	if len(subt) == 0 || len(subt) > len(st) {
		return false
	}
	for i := 0; i+len(subt) <= len(st); i++ {
		ok := true
		for j := range subt {
			if st[i+j] != subt[j] {
				ok = false
				break
			}
		}
		if ok {
			return true
		}
	}
	return false
}

// NameMatches is a loose, accent-insensitive substring test used for player
// name and club searches.
func NameMatches(query, value string) bool {
	q := strings.TrimSpace(FoldAccents(query))
	if q == "" {
		return true
	}
	return strings.Contains(FoldAccents(value), q)
}
