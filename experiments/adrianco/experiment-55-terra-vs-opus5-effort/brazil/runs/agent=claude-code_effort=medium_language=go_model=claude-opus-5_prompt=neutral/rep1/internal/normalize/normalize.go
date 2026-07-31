// Package normalize turns the many spellings of a Brazilian club that appear
// across the Kaggle datasets into a single canonical identity.
//
// The datasets disagree in four independent ways:
//
//	accents      "Grêmio"      vs "Gremio"
//	state suffix "Flamengo-RJ" vs "Flamengo - RJ" vs "Flamengo"
//	country tags "Nacional (URU)" vs "Nacional-URU"
//	club types   "Sport Club do Recife" vs "Sport - PE"
//
// Resolve strips all four, then consults an alias table so that genuinely
// distinct clubs sharing a base name (Atlético-MG vs Athletico-PR, Flamengo-RJ
// vs Flamengo-PI) stay distinct while spellings of the same club collapse.
package normalize

import (
	"strings"
	"unicode"
)

// Team is the canonical identity of a club.
type Team struct {
	ID    string // stable lookup key, e.g. "flamengo" or "botafogo-pb"
	Name  string // human readable display name, e.g. "Flamengo"
	State string // Brazilian state or foreign country code, may be empty
}

// brazilianStates holds the 26 states plus the Federal District.
var brazilianStates = map[string]string{
	"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
	"BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
	"GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
	"MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
	"PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
	"RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
	"SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}

// countryCodes covers the non-Brazilian tags used by the Libertadores file.
var countryCodes = map[string]bool{
	"ARG": true, "URU": true, "PAR": true, "CHI": true, "COL": true, "PER": true,
	"BOL": true, "EQU": true, "ECU": true, "VEN": true, "MEX": true, "BRA": true,
}

// stateByFullName lets us read "(Minas Gerais)" style parentheticals in the
// FIFA player file.
var stateByFullName = func() map[string]string {
	m := make(map[string]string, len(brazilianStates))
	for code, name := range brazilianStates {
		m[foldKey(name)] = code
	}
	return m
}()

// deaccent maps the Latin-1/Latin Extended-A letters used in Brazilian
// Portuguese and Spanish club names onto their ASCII equivalents.
var deaccent = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y', 'ÿ': 'y',
}

// Deaccent lowercases s and folds accented letters to ASCII.
func Deaccent(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range strings.ToLower(s) {
		if repl, ok := deaccent[r]; ok {
			b.WriteRune(repl)
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

// foldKey produces the comparison form used for every lookup table below:
// lowercase, unaccented, punctuation collapsed to single spaces.
func foldKey(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	prevSpace := true
	for _, r := range Deaccent(s) {
		switch {
		case unicode.IsLetter(r) || unicode.IsDigit(r):
			b.WriteRune(r)
			prevSpace = false
		default:
			if !prevSpace {
				b.WriteByte(' ')
				prevSpace = true
			}
		}
	}
	return strings.TrimSpace(b.String())
}

// multiwordSuffixes are club-type phrases that carry no identity.
var multiwordSuffixes = []string{
	"sporting club", "sport club", "esporte clube", "futebol clube",
	"futebol regatas", "esporte c", "futebol s a", "esporte e recreacao",
	"esporte", "clube", "futebol", "ltda", "sa",
}

var multiwordPrefixes = []string{
	"sporting club", "sport club", "esporte clube", "futebol clube",
	"clube de regatas", "clube do", "clube de", "associacao desportiva",
	"associacao atletica", "sociedade esportiva", "gremio esportivo",
	"esporte clube", "clube atletico",
}

// shortSuffixes / shortPrefixes are the initialisms that decorate club names.
// They are only stripped when something is left behind, so "CRB" and "ABC"
// survive intact.
var shortSuffixes = map[string]bool{
	"fc": true, "ec": true, "sc": true, "ac": true, "cf": true, "fr": true,
	"club": true, "clube": true,
}

// connectives are Portuguese linking words that only ever appear between a
// club-type prefix and the real name.
var connectives = map[string]bool{
	"do": true, "da": true, "de": true, "dos": true, "das": true,
}

var shortPrefixes = map[string]bool{
	"fc": true, "ec": true, "sc": true, "ac": true, "cf": true, "ad": true,
	"ae": true, "ge": true, "se": true, "cs": true, "ca": true, "cd": true,
	"ce": true, "sd": true, "sr": true, "aa": true,
}

// ambiguousBases are base names shared by more than one club in the data, so
// the state code stays part of the identity unless an alias pins it down.
var ambiguousBases = map[string]bool{
	"atletico": true, "athletico": true, "america": true, "guarani": true,
	"internacional": true, "flamengo": true, "santos": true, "nautico": true,
	"sao raimundo": true, "ypiranga": true, "santa cruz": true, "operario": true,
	"comercial": true, "river": true, "fluminense": true, "boavista": true,
	"bragantino": true, "botafogo": true, "vitoria": true, "portuguesa": true,
	"real": true, "juventude": true, "sao jose": true, "uniao": true,
	"independente": true, "caxias": true, "nacional": true, "sao luiz": true,
	"sao francisco": true, "remo": true, "gremio": true, "central": true,
	"serra": true, "brasil": true, "madureira": true, "resende": true,
	"desportiva": true, "rio branco": true, "sao bento": true,
}

// alias resolves a folded base name (optionally suffixed with "|state") to the
// canonical identity. Entries without a state apply when the raw name carried
// no state at all, which is how "Flamengo" in the Libertadores file becomes
// Flamengo-RJ rather than a club of its own.
var alias = map[string]Team{}

func addAlias(id, name, state string, keys ...string) {
	t := Team{ID: id, Name: name, State: state}
	for _, k := range keys {
		alias[k] = t
	}
}

func init() {
	// Rio de Janeiro
	addAlias("flamengo", "Flamengo", "RJ", "flamengo", "flamengo|rj", "cr flamengo", "clube de regatas do flamengo")
	addAlias("flamengo-pi", "Flamengo-PI", "PI", "flamengo|pi", "flamengo do piaui", "flamengo do piaui|pi")
	addAlias("fluminense", "Fluminense", "RJ", "fluminense", "fluminense|rj")
	addAlias("botafogo", "Botafogo", "RJ", "botafogo", "botafogo|rj")
	addAlias("vasco-da-gama", "Vasco da Gama", "RJ", "vasco", "vasco|rj", "vasco da gama", "vasco da gama|rj")
	// São Paulo
	addAlias("palmeiras", "Palmeiras", "SP", "palmeiras", "palmeiras|sp", "se palmeiras")
	addAlias("corinthians", "Corinthians", "SP", "corinthians", "corinthians|sp", "corinthians paulista", "sport corinthians paulista")
	addAlias("sao-paulo", "São Paulo", "SP", "sao paulo", "sao paulo|sp")
	addAlias("santos", "Santos", "SP", "santos", "santos|sp")
	addAlias("ponte-preta", "Ponte Preta", "SP", "ponte preta", "ponte preta|sp", "aa ponte preta")
	addAlias("portuguesa", "Portuguesa", "SP", "portuguesa", "portuguesa|sp", "portuguesa desportos", "portuguesa desportos|sp")
	addAlias("red-bull-bragantino", "Red Bull Bragantino", "SP",
		"bragantino", "bragantino|sp", "red bull bragantino", "red bull bragantino|sp")
	addAlias("sao-caetano", "São Caetano", "SP", "sao caetano", "sao caetano|sp")
	addAlias("santo-andre", "Santo André", "SP", "santo andre", "santo andre|sp")
	addAlias("guarani", "Guarani", "SP", "guarani|sp")
	// Rio Grande do Sul
	addAlias("gremio", "Grêmio", "RS", "gremio", "gremio|rs", "gremio foot ball porto alegrense")
	addAlias("internacional", "Internacional", "RS", "internacional", "internacional|rs")
	addAlias("juventude", "Juventude", "RS", "juventude", "juventude|rs")
	// Minas Gerais
	addAlias("cruzeiro", "Cruzeiro", "MG", "cruzeiro", "cruzeiro|mg")
	addAlias("atletico-mineiro", "Atlético Mineiro", "MG",
		"atletico|mg", "atletico mineiro", "atletico mineiro|mg")
	addAlias("america-mineiro", "América-MG", "MG",
		"america|mg", "america mineiro", "america mineiro|mg", "america minas gerais|mg", "america minas gerais")
	// Paraná
	addAlias("athletico-paranaense", "Athletico Paranaense", "PR",
		"athletico", "athletico|pr", "atletico|pr", "athletico paranaense",
		"athletico paranaense|pr", "atletico paranaense", "atletico paranaense|pr")
	addAlias("coritiba", "Coritiba", "PR", "coritiba", "coritiba|pr")
	addAlias("parana", "Paraná", "PR", "parana", "parana|pr")
	// Other capitals
	addAlias("atletico-goianiense", "Atlético Goianiense", "GO",
		"atletico|go", "atletico goianiense", "atletico goianiense|go")
	addAlias("goias", "Goiás", "GO", "goias", "goias|go")
	addAlias("bahia", "Bahia", "BA", "bahia", "bahia|ba")
	addAlias("vitoria", "Vitória", "BA", "vitoria|ba")
	addAlias("sport-recife", "Sport Recife", "PE",
		"sport", "sport|pe", "sport recife", "sport recife|pe", "recife", "recife|pe")
	addAlias("nautico", "Náutico", "PE",
		"nautico|pe", "nautico capibaribe", "nautico capibaribe|pe")
	addAlias("santa-cruz", "Santa Cruz", "PE", "santa cruz|pe")
	addAlias("ceara", "Ceará", "CE", "ceara", "ceara|ce")
	addAlias("fortaleza", "Fortaleza", "CE", "fortaleza", "fortaleza|ce")
	addAlias("atletico-cearense", "Atlético Cearense", "CE",
		"atletico cearense", "atletico cearense|ce", "uniclinic", "uniclinic|ce")
	addAlias("america-rn", "América-RN", "RN",
		"america|rn", "america de natal", "america de natal|rn", "america natal", "america natal|rn")
	addAlias("abc", "ABC", "RN", "abc", "abc|rn", "a b c", "a b c|rn")
	addAlias("csa", "CSA", "AL", "csa", "csa|al", "c s a", "c s a|al", "alagoano", "alagoano|al")
	addAlias("crb", "CRB", "AL", "crb", "crb|al", "c r b", "c r b|al")
	addAlias("asa", "ASA", "AL", "asa", "asa|al", "a s a", "a s a|al")
	addAlias("confianca", "Confiança", "SE", "confianca", "confianca|se")
	// Santa Catarina
	addAlias("chapecoense", "Chapecoense", "SC", "chapecoense", "chapecoense|sc")
	addAlias("avai", "Avaí", "SC", "avai", "avai|sc")
	addAlias("figueirense", "Figueirense", "SC", "figueirense", "figueirense|sc")
	addAlias("criciuma", "Criciúma", "SC", "criciuma", "criciuma|sc")
	addAlias("joinville", "Joinville", "SC", "joinville", "joinville|sc")
	// Centre-west / north
	addAlias("cuiaba", "Cuiabá", "MT", "cuiaba", "cuiaba|mt")
	addAlias("brasiliense", "Brasiliense", "DF", "brasiliense", "brasiliense|df")
	addAlias("paysandu", "Paysandu", "PA", "paysandu", "paysandu|pa")
	addAlias("remo", "Remo", "PA", "remo", "remo|pa")
	addAlias("manaus", "Manaus", "AM", "manaus", "manaus|am")
	// Frequent foreign Libertadores opponents that appear with and without tags.
	addAlias("nacional-uru", "Nacional (URU)", "URU", "nacional|uru")
	addAlias("nacional-par", "Nacional (PAR)", "PAR", "nacional|par")
	addAlias("guarani-par", "Guaraní (PAR)", "PAR", "guarani|par")
	addAlias("libertad", "Libertad", "PAR", "libertad", "libertad|par")
	addAlias("olimpia", "Olimpia", "PAR", "olimpia", "olimpia|par")
	addAlias("river-plate", "River Plate", "ARG", "river plate")
	addAlias("river-plate-uru", "River Plate (URU)", "URU", "river plate|uru")
	addAlias("universitario", "Universitario", "PER", "universitario", "universitario|per")
	addAlias("barcelona-equ", "Barcelona (EQU)", "EQU", "barcelona|equ", "barcelona|ecu")
	addAlias("delfin", "Delfín", "EQU", "delfin", "delfin|equ")
	addAlias("independiente-del-valle", "Independiente del Valle", "EQU", "independiente del valle")
	addAlias("trujillanos", "Trujillanos", "VEN", "trujillanos", "trujillanos|ven")
}

// displayName re-capitalises a folded base name for output.
func displayName(base string) string {
	words := strings.Fields(base)
	for i, w := range words {
		r := []rune(w)
		r[0] = unicode.ToUpper(r[0])
		words[i] = string(r)
	}
	return strings.Join(words, " ")
}

// splitState pulls a trailing or parenthesised state/country code off raw and
// returns the remaining name plus the code (empty when none was present).
func splitState(raw string) (string, string) {
	s := strings.TrimSpace(strings.Trim(strings.TrimSpace(raw), `"`))
	state := ""

	// Parentheticals: "(URU)", "(Minas Gerais)".
	if open := strings.LastIndex(s, "("); open >= 0 {
		if close := strings.Index(s[open:], ")"); close > 0 {
			inner := strings.TrimSpace(s[open+1 : open+close])
			upper := strings.ToUpper(inner)
			if brazilianStates[upper] != "" || countryCodes[upper] {
				state = upper
			} else if code, ok := stateByFullName[foldKey(inner)]; ok {
				state = code
			}
			s = strings.TrimSpace(s[:open] + s[open+close+1:])
		}
	}

	// Trailing token after " - ", "-" or a space.
	if state == "" {
		if idx := strings.LastIndexAny(s, "- /"); idx > 0 && idx < len(s)-1 {
			tail := strings.TrimSpace(s[idx+1:])
			upper := strings.ToUpper(tail)
			// Only treat it as a code if the source wrote it in caps: that
			// keeps "Colo-Colo" and "Sao Jose - POA" intact.
			if tail == upper && (brazilianStates[upper] != "" || countryCodes[upper]) {
				state = upper
				s = strings.TrimSpace(strings.TrimRight(strings.TrimSpace(s[:idx]), "-/ "))
			}
		}
	}
	return s, state
}

// stripClubWords removes club-type prefixes and suffixes from a folded name,
// never emptying it.
func stripClubWords(base string) string {
	changed := true
	for changed {
		changed = false
		for _, p := range multiwordPrefixes {
			if rest, ok := strings.CutPrefix(base, p+" "); ok && rest != "" {
				base, changed = rest, true
			}
		}
		for _, s := range multiwordSuffixes {
			if rest, ok := strings.CutSuffix(base, " "+s); ok && rest != "" {
				base, changed = rest, true
			}
		}
		fields := strings.Fields(base)
		// A connective left dangling by prefix removal, as in
		// "Clube de Regatas do Flamengo" -> "do flamengo".
		if len(fields) > 1 && connectives[fields[0]] {
			base, changed = strings.Join(fields[1:], " "), true
			continue
		}
		if len(fields) > 1 && shortPrefixes[fields[0]] {
			base, changed = strings.Join(fields[1:], " "), true
			continue
		}
		if len(fields) > 1 && shortSuffixes[fields[len(fields)-1]] {
			base, changed = strings.Join(fields[:len(fields)-1], " "), true
		}
	}
	return base
}

// Resolve maps any raw club spelling onto its canonical Team. The zero Team is
// returned for blank input.
func Resolve(raw string) Team {
	name, state := splitState(raw)
	base := stripClubWords(foldKey(name))
	if base == "" {
		return Team{}
	}

	lowState := strings.ToLower(state)
	if t, ok := alias[base+"|"+lowState]; ok && state != "" {
		return t
	}
	if t, ok := alias[base]; ok && state == "" {
		return t
	}
	// An alias with no state qualifier also matches an explicit state that
	// agrees with it, e.g. "Cuiabá - MT" for the alias registered as MT.
	if t, ok := alias[base]; ok && strings.EqualFold(t.State, state) {
		return t
	}

	id := strings.ReplaceAll(base, " ", "-")
	if state != "" && ambiguousBases[base] {
		id += "-" + lowState
	}
	display := displayName(base)
	if state != "" && ambiguousBases[base] {
		display += "-" + state
	}
	return Team{ID: id, Name: display, State: state}
}

// StateName expands a two-letter Brazilian state code; unknown codes come back
// unchanged.
func StateName(code string) string {
	if n, ok := brazilianStates[strings.ToUpper(code)]; ok {
		return n
	}
	return code
}

// Match reports whether a free-text user query plausibly refers to team. It is
// deliberately generous: exact canonical match, then substring on the folded
// forms, so "flamengo", "Flamengo-RJ" and "CR Flamengo" all hit.
func Match(query string, team Team) bool {
	q := Resolve(query)
	if q.ID != "" && q.ID == team.ID {
		return true
	}
	needle := stripClubWords(foldKey(query))
	if needle == "" {
		return false
	}
	hay := foldKey(team.Name)
	return strings.Contains(hay, needle) || strings.Contains(strings.ReplaceAll(team.ID, "-", " "), needle)
}
