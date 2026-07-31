// Package soccer loads the Brazilian football datasets shipped in data/kaggle,
// normalises their wildly inconsistent team names into a single canonical
// registry, links everything into an in-memory knowledge graph and answers
// match / team / player / competition / statistics queries over the result.
//
// normalize.go holds the low-level text and date plumbing: UTF-8 accent
// folding, team-name normalisation (state and country suffixes, club-type
// noise words, abbreviations) and the several date formats used by the CSVs.
package soccer

import (
	"regexp"
	"strconv"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"
)

// ---------------------------------------------------------------------------
// Accent folding
// ---------------------------------------------------------------------------

var foldMap map[rune]string

func init() {
	pairs := []struct{ chars, repl string }{
		{"àáâãäåāăą", "a"},
		{"çćĉċč", "c"},
		{"ďđ", "d"},
		{"èéêëēĕėęě", "e"},
		{"ĝğġģ", "g"},
		{"ĥħ", "h"},
		{"ìíîïĩīĭįı", "i"},
		{"ĵ", "j"},
		{"ķ", "k"},
		{"ĺļľŀł", "l"},
		{"ñńņňŉ", "n"},
		{"òóôõöøōŏő", "o"},
		{"ŕŗř", "r"},
		{"śŝşšș", "s"},
		{"ţťŧț", "t"},
		{"ùúûüũūŭůűų", "u"},
		{"ŵ", "w"},
		{"ýÿŷ", "y"},
		{"źżž", "z"},
		{"æ", "ae"},
		{"œ", "oe"},
		{"ß", "ss"},
		{"þ", "th"},
		{"ð", "d"},
	}
	foldMap = make(map[rune]string, 256)
	for _, p := range pairs {
		for _, r := range p.chars {
			foldMap[r] = p.repl
			if u := unicode.ToUpper(r); u != r {
				foldMap[u] = p.repl
			}
		}
	}
}

// Fold lower-cases s and strips diacritics so that "São Paulo", "Sao Paulo"
// and "SAO PAULO" all collapse to the same key. Combining marks and format
// characters (including the UTF-8 BOM) are dropped.
func Fold(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if r < utf8.RuneSelf {
			b.WriteRune(unicode.ToLower(r))
			continue
		}
		if rep, ok := foldMap[r]; ok {
			b.WriteString(rep)
			continue
		}
		if unicode.Is(unicode.Mn, r) || unicode.Is(unicode.Cf, r) {
			continue
		}
		b.WriteRune(unicode.ToLower(r))
	}
	return b.String()
}

var nonAlnum = regexp.MustCompile(`[^a-z0-9]+`)

// Slug folds s and turns it into a hyphen separated identifier.
func Slug(s string) string {
	return strings.Trim(nonAlnum.ReplaceAllString(Fold(s), "-"), "-")
}

// ---------------------------------------------------------------------------
// Team name normalisation
// ---------------------------------------------------------------------------

// BrazilianStates maps the 27 federative unit codes to their full names.
var BrazilianStates = map[string]string{
	"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
	"BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
	"GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
	"MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
	"PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
	"RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
	"SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}

// stateByName resolves a written-out state ("minas gerais") to its code. It is
// built from BrazilianStates plus the handful of spellings seen in the data.
var stateByName = map[string]string{}

func init() {
	for code, name := range BrazilianStates {
		stateByName[Fold(name)] = code
	}
	// "BH" appears once in novo_campeonato_brasileiro.csv for Bahia.
	stateByName["bh"] = "BA"
}

// countryCodes maps the three letter codes used by the Libertadores file (and
// a few written-out names) onto canonical ISO-ish codes.
var countryCodes = map[string]string{
	"arg": "ARG", "argentina": "ARG",
	"bol": "BOL", "bolivia": "BOL",
	"bra": "BRA", "brasil": "BRA", "brazil": "BRA",
	"chi": "CHI", "chile": "CHI",
	"col": "COL", "colombia": "COL",
	"equ": "ECU", "ecu": "ECU", "ecuador": "ECU", "equador": "ECU",
	"mex": "MEX", "mexico": "MEX",
	"par": "PAR", "paraguai": "PAR", "paraguay": "PAR",
	"per": "PER", "peru": "PER",
	"uru": "URU", "ury": "URU", "uruguai": "URU", "uruguay": "URU",
	"ven": "VEN", "venezuela": "VEN",
}

// CountryNames gives a display name for the codes above.
var CountryNames = map[string]string{
	"ARG": "Argentina", "BOL": "Bolivia", "BRA": "Brazil", "CHI": "Chile",
	"COL": "Colombia", "ECU": "Ecuador", "MEX": "Mexico", "PAR": "Paraguay",
	"PER": "Peru", "URU": "Uruguay", "VEN": "Venezuela",
}

// Noise tokens: club-type words that carry no identity ("Esporte Clube",
// "FC", "Futebol Clube", ...). They are only stripped from the head and tail
// of a name and never all of it.
var leadingNoise = map[string]bool{
	"aa": true, "ac": true, "ad": true, "ae": true, "af": true, "ca": true,
	"cd": true, "cf": true, "cr": true, "cs": true, "ea": true, "ec": true,
	"fc": true, "gd": true, "ge": true, "sc": true, "sd": true, "se": true,
	"agremiacao": true, "associacao": true, "club": true, "clube": true,
	"esporte": true, "esportivo": true, "sociedade": true,
	"da": true, "das": true, "de": true, "do": true, "dos": true,
}

var trailingNoise = map[string]bool{
	"ac": true, "cf": true, "ec": true, "fc": true, "gd": true, "sc": true,
	"sd":   true,
	"club": true, "clube": true, "desportiva": true, "desportivo": true,
	"desportos": true, "esporte": true, "esportiva": true, "esportivo": true,
	"futebol": true, "sport": true, "sporting": true,
	"da": true, "das": true, "de": true, "do": true, "dos": true,
}

var parenRe = regexp.MustCompile(`\([^)]*\)`)

// TeamName is a raw team string decomposed into the pieces that matter for
// identity: a noise-free base name plus an optional qualifier (a Brazilian
// state code, or a country code for non-Brazilian clubs).
type TeamName struct {
	Raw       string
	Base      string // folded, noise stripped, e.g. "vasco da gama"
	Qualifier string // "RJ" or "URU"; empty when unknown
	IsState   bool   // true when Qualifier is a Brazilian state
}

// Key is the identity key for the name: base plus qualifier when known.
func (n TeamName) Key() string {
	base := strings.ReplaceAll(n.Base, " ", "-")
	if n.Qualifier == "" {
		return base
	}
	return base + "-" + strings.ToLower(n.Qualifier)
}

// NormalizeTeamName decomposes a raw team string from any of the datasets.
//
//	"Palmeiras-SP"                       -> {Base: "palmeiras", Qualifier: "SP"}
//	"América - MG"                       -> {Base: "america",   Qualifier: "MG"}
//	"Nacional (URU)"                     -> {Base: "nacional",  Qualifier: "URU"}
//	"Arapongas Esporte Clube - PR"       -> {Base: "arapongas", Qualifier: "PR"}
//	"América FC (Minas Gerais)"          -> {Base: "america",   Qualifier: "MG"}
func NormalizeTeamName(raw string) TeamName {
	n := TeamName{Raw: strings.TrimSpace(raw)}
	s := Fold(n.Raw)

	// Parenthesised suffixes are either a country, a state or an editorial
	// note ("(antigo Esporte Clube Barreira)"); the first two are qualifiers,
	// the rest is dropped.
	s = parenRe.ReplaceAllStringFunc(s, func(m string) string {
		inner := strings.TrimSpace(strings.Trim(m, "()"))
		if code, ok := stateByName[inner]; ok && n.Qualifier == "" {
			n.Qualifier, n.IsState = code, true
		} else if code, ok := countryCodes[inner]; ok && n.Qualifier == "" {
			n.Qualifier, n.IsState = code, false
		}
		return " "
	})

	tokens := strings.Fields(nonAlnum.ReplaceAllString(s, " "))
	if len(tokens) == 0 {
		return n
	}

	// Trailing state ("-SP", " SP", " - SP") or country ("-URU") code.
	if n.Qualifier == "" && len(tokens) > 1 {
		last := tokens[len(tokens)-1]
		if _, ok := BrazilianStates[strings.ToUpper(last)]; ok {
			n.Qualifier, n.IsState = strings.ToUpper(last), true
			tokens = tokens[:len(tokens)-1]
		} else if code, ok := countryCodes[last]; ok && len(last) == 3 {
			n.Qualifier, n.IsState = code, false
			tokens = tokens[:len(tokens)-1]
		}
	}

	original := tokens
	for len(tokens) > 1 && leadingNoise[tokens[0]] {
		tokens = tokens[1:]
	}
	for len(tokens) > 1 && trailingNoise[tokens[len(tokens)-1]] {
		tokens = tokens[:len(tokens)-1]
	}
	if len(tokens) == 0 {
		tokens = original
	}

	// "A.b.c." -> ["a","b","c"] -> "abc"; likewise "A.s.a." -> "asa".
	if len(tokens) > 1 {
		allSingle := true
		for _, t := range tokens {
			if len(t) != 1 {
				allSingle = false
				break
			}
		}
		if allSingle {
			tokens = []string{strings.Join(tokens, "")}
		}
	}

	n.Base = strings.Join(tokens, " ")
	return n
}

// ---------------------------------------------------------------------------
// Dates and numbers
// ---------------------------------------------------------------------------

var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05Z07:00",
	"2006-01-02T15:04:05",
	"2006-01-02 15:04",
	"2006-01-02",
	"02/01/2006 15:04:05",
	"02/01/2006 15:04",
	"02/01/2006",
	"02-01-2006",
	"2006/01/02",
}

// ParseDate accepts every date shape found in the datasets: ISO dates, ISO
// datetimes and Brazilian DD/MM/YYYY. The second result reports whether a
// kick-off time was present.
func ParseDate(s string) (t time.Time, hasTime bool, ok bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false, false
	}
	for _, layout := range dateLayouts {
		if parsed, err := time.ParseInLocation(layout, s, time.UTC); err == nil {
			// Go reference layouts spell the hour "15" (or "03").
			return parsed, strings.Contains(layout, "15") || strings.Contains(layout, "03"), true
		}
	}
	return time.Time{}, false, false
}

// ParseDateTime merges a date column with a separate time column
// ("2023-09-24" + "20:00:00"), as used by BR-Football-Dataset.csv.
func ParseDateTime(date, clock string) (t time.Time, hasTime bool, ok bool) {
	t, hasTime, ok = ParseDate(date)
	if !ok {
		return t, hasTime, ok
	}
	clock = strings.TrimSpace(clock)
	if clock == "" {
		return t, hasTime, true
	}
	for _, layout := range []string{"15:04:05", "15:04"} {
		if c, err := time.ParseInLocation(layout, clock, time.UTC); err == nil {
			return time.Date(t.Year(), t.Month(), t.Day(), c.Hour(), c.Minute(), c.Second(), 0, time.UTC), true, true
		}
	}
	return t, hasTime, true
}

// ParseIntLoose reads integers that may arrive as floats ("1.0"), be quoted or
// be blank. ok is false for values that are not numbers.
func ParseIntLoose(s string) (int, bool) {
	s = strings.TrimSpace(strings.Trim(strings.TrimSpace(s), `"`))
	if s == "" {
		return 0, false
	}
	if v, err := strconv.Atoi(s); err == nil {
		return v, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

// ---------------------------------------------------------------------------
// Fuzzy matching helpers (used for "did you mean ...?" answers)
// ---------------------------------------------------------------------------

// Levenshtein returns the edit distance between two folded strings.
func Levenshtein(a, b string) int {
	ra, rb := []rune(a), []rune(b)
	if len(ra) == 0 {
		return len(rb)
	}
	if len(rb) == 0 {
		return len(ra)
	}
	prev := make([]int, len(rb)+1)
	cur := make([]int, len(rb)+1)
	for j := range prev {
		prev[j] = j
	}
	for i := 1; i <= len(ra); i++ {
		cur[0] = i
		for j := 1; j <= len(rb); j++ {
			cost := 1
			if ra[i-1] == rb[j-1] {
				cost = 0
			}
			cur[j] = min3(cur[j-1]+1, prev[j]+1, prev[j-1]+cost)
		}
		prev, cur = cur, prev
	}
	return prev[len(rb)]
}

func min3(a, b, c int) int {
	if b < a {
		a = b
	}
	if c < a {
		a = c
	}
	return a
}
