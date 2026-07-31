// names.go turns the many spellings of a Brazilian club into one canonical
// identity.
//
// The datasets disagree with each other in five different ways:
//
//	Brasileirao_Matches.csv     "Palmeiras-SP"      state glued on with a hyphen
//	Brazilian_Cup_Matches.csv   "América - MG"      state separated by spaces
//	BR-Football-Dataset.csv     "America MG"        accents dropped, space separated
//	novo_campeonato_*.csv       "Athletico-PR"      accented, hyphenated
//	Libertadores_Matches.csv    "Nacional (URU)"    country in parentheses
//	fifa_data.csv               "América FC (Minas Gerais)", "Sport Club do Recife"
//
// parseTeamName splits a raw string into (base, state, country); a curated alias
// table folds spelling variants and renamings ("Athletico Paranaense" ->
// "atletico"/PR) onto the same base. Teams that share a base but sit in different
// states (Atlético-MG vs Atlético-PR, América-MG vs América-RN) stay distinct;
// bare spellings of an ambiguous base are resolved through defaultStates. The
// final base -> team assignment happens in graph.go, once every spelling in every
// file has been observed.
package soccer

import (
	"strings"
	"unicode"
)

// brazilianStates is the set of two letter state abbreviations (UF) that may be
// used as a suffix on a club name.
var brazilianStates = map[string]bool{
	"AC": true, "AL": true, "AP": true, "AM": true, "BA": true, "CE": true,
	"DF": true, "ES": true, "GO": true, "MA": true, "MT": true, "MS": true,
	"MG": true, "PA": true, "PB": true, "PR": true, "PE": true, "PI": true,
	"RJ": true, "RN": true, "RS": true, "RO": true, "RR": true, "SC": true,
	"SP": true, "SE": true, "TO": true,
}

// stateNames maps a UF to its full name, used when rendering team profiles and
// when a dataset spells the state out ("Minas Gerais").
var stateNames = map[string]string{
	"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
	"BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
	"GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
	"MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
	"PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
	"RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia",
	"RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
	"SE": "Sergipe", "TO": "Tocantins",
}

// stateByFullName is the reverse of stateNames, keyed by folded full name; the
// FIFA database writes "América FC (Minas Gerais)".
var stateByFullName = func() map[string]string {
	m := make(map[string]string, len(stateNames))
	for uf, name := range stateNames {
		m[foldKey(name)] = uf
	}
	return m
}()

// foreignCountries are the three letter codes the Libertadores file appends to
// non-Brazilian clubs, plus the country names they stand for.
var foreignCountries = map[string]string{
	"ARG": "Argentina", "BOL": "Bolivia", "CHI": "Chile", "COL": "Colombia",
	"EQU": "Ecuador", "MEX": "Mexico", "PAR": "Paraguay", "PER": "Peru",
	"URU": "Uruguay", "VEN": "Venezuela", "BRA": "Brazil",
}

// clubWordSuffixes are generic club-type tokens that may be stripped from the
// end of a name ("Ceará Sporting Club" -> "ceara"). They are only removed while
// at least one token remains, so a club actually called "Sport" survives.
var clubWordSuffixes = map[string]bool{
	"fc": true, "ec": true, "sc": true, "ac": true, "aa": true, "ad": true,
	"cf": true, "cd": true, "se": true, "afc": true, "efc": true, "fbc": true,
	"club": true, "clube": true, "sporting": true, "sport": true,
	"futebol": true, "esporte": true, "esportivo": true, "esportiva": true,
}

// clubWordPrefixes are generic club-type tokens strippable from the front of a
// name ("EC Vitoria" -> "vitoria"). Deliberately conservative: "sport" and
// "esporte" are excluded because "Sport Club do Recife" must not collapse to
// "recife"; the alias table handles that name instead.
var clubWordPrefixes = map[string]bool{
	"fc": true, "ec": true, "sc": true, "ac": true, "aa": true, "ad": true,
	"cf": true, "cd": true, "se": true, "cr": true, "cs": true,
}

// nameHint overrides the base and/or state derived from a raw name.
type nameHint struct {
	base  string
	state string
}

// teamAliases folds spelling variants, historical names and official long names
// onto a single canonical base. Keys are the folded base produced by
// parseTeamName before aliasing.
var teamAliases = map[string]nameHint{
	// Athletico Paranaense was spelled "Atlético Paranaense" until 2018 and
	// appears bare as "Athletico" in the Libertadores file.
	"athletico":            {"atletico", "PR"},
	"athletico paranaense": {"atletico", "PR"},
	"atletico paranaense":  {"atletico", "PR"},
	"furacao":              {"atletico", "PR"},
	// The other Atléticos.
	"atletico mineiro":    {"atletico", "MG"},
	"atletico goianiense": {"atletico", "GO"},
	"atletico goiania":    {"atletico", "GO"},
	"atletico cearense":   {"atletico", "CE"},
	"atletico acreano":    {"atletico", "AC"},
	"atletico alagoinhas": {"atletico", "BA"},
	// Vasco da Gama.
	"vasco":         {"vasco da gama", "RJ"},
	"vasco da gama": {"vasco da gama", "RJ"},
	"vasco gama":    {"vasco da gama", "RJ"},
	// Red Bull Bragantino (Bragantino until the 2019 rebrand).
	"red bull bragantino": {"bragantino", "SP"},
	"rb bragantino":       {"bragantino", "SP"},
	// Long official names used by the FIFA database and the cup file.
	"sport club do recife":             {"sport", "PE"},
	"sport recife":                     {"sport", "PE"},
	"sport do recife":                  {"sport", "PE"},
	"ceara sporting":                   {"ceara", "CE"},
	"america natal":                    {"america", "RN"},
	"america de natal":                 {"america", "RN"},
	"america mineiro":                  {"america", "MG"},
	"sao paulo futebol":                {"sao paulo", "SP"},
	"corinthians paulista":             {"corinthians", "SP"},
	"sport corinthians paulista":       {"corinthians", "SP"},
	"botafogo de futebol e regatas":    {"botafogo", "RJ"},
	"gremio porto alegrense":           {"gremio", "RS"},
	"gremio foot ball porto alegrense": {"gremio", "RS"},
	"nautico capibaribe":               {"nautico", "PE"},
	"associacao chapecoense":           {"chapecoense", "SC"},
	"parana clube":                     {"parana", "PR"},
	// Foreign clubs whose names vary between rows.
	"ind santa fe":      {"independiente santa fe", ""},
	"u de chile":        {"universidad de chile", ""},
	"universidad chile": {"universidad de chile", ""},
	"u catolica":        {"universidad catolica", ""},
}

// defaultStates disambiguates bare spellings of a base that several clubs share.
// The value is the club a bare name refers to in practice, which in every case
// here is the club that plays in the national divisions.
var defaultStates = map[string]string{
	"america":       "MG",
	"atletico":      "MG",
	"botafogo":      "RJ",
	"bragantino":    "SP",
	"central":       "PE",
	"comercial":     "MS",
	"flamengo":      "RJ",
	"fluminense":    "RJ",
	"guarani":       "SP",
	"internacional": "RS",
	"juventude":     "RS",
	"nautico":       "PE",
	"operario":      "PR",
	"portuguesa":    "SP",
	"rio branco":    "AC",
	"river":         "PI",
	"santa cruz":    "PE",
	"santos":        "SP",
	"sao francisco": "PA",
	"sao jose":      "RS",
	"sao raimundo":  "RR",
	"vitoria":       "BA",
	"ypiranga":      "RS",
}

// defaultCountries disambiguates famous South American clubs whose bare name is
// also the name of a small Brazilian club: the Libertadores file writes "River
// Plate" for the Argentine giant, while the Copa do Brasil file has "River Plate
// - SE" from Sergipe, and likewise Peñarol of Uruguay versus Penarol of Amazonas.
var defaultCountries = map[string]string{
	"river plate": "ARG",
	"penarol":     "URU",
}

// nicknameTable lists the popular names Brazilians use for each club. The club
// column is resolved through the normal name pipeline once the registry is
// built, so the nicknames become additional lookup keys.
var nicknameTable = []struct {
	Club  string
	Names []string
}{
	{"Flamengo-RJ", []string{"Mengão", "Fla", "Mengo", "Rubro-Negro"}},
	{"Fluminense-RJ", []string{"Flu", "Fluzão", "Tricolor Carioca"}},
	{"Corinthians", []string{"Timão", "Coringão"}},
	{"Palmeiras", []string{"Verdão", "Porco", "Alviverde"}},
	{"Santos-SP", []string{"Peixe", "Alvinegro Praiano"}},
	{"São Paulo-SP", []string{"Tricolor Paulista", "SPFC", "Soberano"}},
	{"Atlético-MG", []string{"Galo", "Atlético Mineiro"}},
	{"Athletico-PR", []string{"Furacão", "Athletico Paranaense"}},
	{"Atlético-GO", []string{"Dragão", "Atlético Goianiense"}},
	{"Cruzeiro", []string{"Raposa", "Cabuloso"}},
	{"Grêmio", []string{"Imortal", "Tricolor Gaúcho"}},
	{"Internacional-RS", []string{"Colorado", "Inter"}},
	{"Botafogo-RJ", []string{"Fogão", "Glorioso"}},
	{"Vasco da Gama", []string{"Gigante da Colina", "Vascão", "Vasco"}},
	{"Bahia", []string{"Esquadrão de Aço", "Tricolor de Aço"}},
	{"Vitória-BA", []string{"Leão da Barra"}},
	{"Sport-PE", []string{"Leão da Ilha", "Sport Recife"}},
	{"Náutico-PE", []string{"Timbu"}},
	{"Santa Cruz-PE", []string{"Cobra Coral"}},
	{"Fortaleza", []string{"Leão do Pici"}},
	{"Ceará", []string{"Vovô"}},
	{"Coritiba", []string{"Coxa", "Coxa Branca"}},
	{"Chapecoense", []string{"Chape"}},
	{"Goiás", []string{"Esmeraldino"}},
	{"América-MG", []string{"Coelho", "América Mineiro"}},
	{"Bragantino-SP", []string{"Massa Bruta", "Red Bull Bragantino", "RB Bragantino"}},
	{"Figueirense", []string{"Figueira"}},
	{"Ponte Preta", []string{"Macaca"}},
	{"Portuguesa-SP", []string{"Lusa"}},
	{"CSA", []string{"Azulão"}},
	{"Cuiabá", []string{"Dourado"}},
	{"Criciúma", []string{"Tigre"}},
	{"Avaí", []string{"Leão da Ilha Catarinense"}},
}

// fold removes diacritics, mapping the Latin-1 and Latin Extended-A characters
// that occur in Portuguese and Spanish club names to ASCII. The Go standard
// library ships no Unicode normalisation, so the mapping is explicit.
func fold(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if r < unicode.MaxASCII {
			b.WriteRune(r)
			continue
		}
		if repl, ok := foldRunes[r]; ok {
			b.WriteString(repl)
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

var foldRunes = map[rune]string{
	'á': "a", 'à': "a", 'â': "a", 'ã': "a", 'ä': "a", 'å': "a", 'ā': "a",
	'Á': "A", 'À': "A", 'Â': "A", 'Ã': "A", 'Ä': "A", 'Å': "A", 'Ā': "A",
	'é': "e", 'è': "e", 'ê': "e", 'ë': "e", 'ē': "e",
	'É': "E", 'È': "E", 'Ê': "E", 'Ë': "E", 'Ē': "E",
	'í': "i", 'ì': "i", 'î': "i", 'ï': "i", 'ī': "i",
	'Í': "I", 'Ì': "I", 'Î': "I", 'Ï': "I", 'Ī': "I",
	'ó': "o", 'ò': "o", 'ô': "o", 'õ': "o", 'ö': "o", 'ø': "o", 'ō': "o",
	'Ó': "O", 'Ò': "O", 'Ô': "O", 'Õ': "O", 'Ö': "O", 'Ø': "O", 'Ō': "O",
	'ú': "u", 'ù': "u", 'û': "u", 'ü': "u", 'ū': "u",
	'Ú': "U", 'Ù': "U", 'Û': "U", 'Ü': "U", 'Ū': "U",
	'ç': "c", 'Ç': "C", 'ñ': "n", 'Ñ': "N", 'ý': "y", 'Ý': "Y",
	'ß': "ss", 'æ': "ae", 'Æ': "AE", 'œ': "oe", 'Œ': "OE",
	'’': "'", '‘': "'", '´': "'", '`': "'",
}

// foldKey lower-cases, removes diacritics and punctuation, and collapses runs of
// whitespace. It is the key used by every lookup table in the package.
func foldKey(s string) string {
	s = fold(s)
	var b strings.Builder
	b.Grow(len(s))
	prevSpace := true
	for _, r := range s {
		switch {
		case r >= 'A' && r <= 'Z':
			b.WriteRune(r + 32)
			prevSpace = false
		case (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9'):
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

// nameParts is the decomposition of a raw club name.
type nameParts struct {
	Base    string // canonical folded base name, e.g. "atletico"
	State   string // "MG", or "" when unknown
	Country string // "URU", or "" for Brazilian clubs
	Pretty  string // raw name with suffixes and parentheticals removed
}

// empty reports whether parsing produced nothing usable.
func (p nameParts) empty() bool { return p.Base == "" }

// groupKey identifies the team a set of parts belongs to. Parts without a state
// share the group of the base; graph.go merges those into the single stated team
// when the base is unambiguous.
func (p nameParts) groupKey() string {
	switch {
	case p.Country != "":
		return p.Base + "|" + p.Country
	case p.State != "":
		return p.Base + "|" + p.State
	default:
		return p.Base + "|"
	}
}

// parseTeamName decomposes a raw dataset spelling into base name, state and
// country, applying the alias table.
func parseTeamName(raw string) nameParts {
	s := strings.TrimSpace(raw)
	if s == "" {
		return nameParts{}
	}
	var state, country string

	// 1. Pull out parentheticals: "(URU)" is a country, "(Minas Gerais)" a
	//    state, anything else ("(antigo Esporte Clube Barreira)") is noise.
	for {
		open := strings.Index(s, "(")
		if open < 0 {
			break
		}
		rel := strings.Index(s[open:], ")")
		if rel < 0 {
			s = strings.TrimSpace(s[:open])
			break
		}
		inner := strings.TrimSpace(s[open+1 : open+rel])
		upper := strings.ToUpper(fold(inner))
		if _, ok := foreignCountries[upper]; ok && country == "" {
			country = upper
		} else if uf, ok := stateByFullName[foldKey(inner)]; ok && state == "" {
			state = uf
		}
		s = strings.TrimSpace(s[:open] + " " + s[open+rel+1:])
	}

	key := foldKey(s)
	if key == "" {
		return nameParts{}
	}
	tokens := strings.Fields(key)

	// 2. Peel trailing state / country codes ("Palmeiras SP", "Barcelona EQU").
	peeled := 0
	for len(tokens) > 1 {
		last := strings.ToUpper(tokens[len(tokens)-1])
		if brazilianStates[last] {
			if state == "" {
				state = last
			}
			tokens = tokens[:len(tokens)-1]
			peeled++
			continue
		}
		if _, ok := foreignCountries[last]; ok {
			if country == "" {
				country = last
			}
			tokens = tokens[:len(tokens)-1]
			peeled++
			continue
		}
		break
	}
	pretty := trimTrailingWords(s, peeled)

	// 3. Strip generic club words from both ends, mirroring the cut on the
	//    display form so that "Fortaleza EC" shows as "Fortaleza".
	lead, trail := 0, 0
	for len(tokens) > 1 && clubWordPrefixes[tokens[0]] {
		tokens = tokens[1:]
		lead++
	}
	for len(tokens) > 1 && clubWordSuffixes[tokens[len(tokens)-1]] {
		tokens = tokens[:len(tokens)-1]
		trail++
	}
	pretty = trimTrailingWords(trimLeadingWords(pretty, lead), trail)
	base := strings.Join(tokens, " ")

	// 4. Apply the alias table, then fall back to the default state for bases
	//    shared by several clubs.
	if hint, ok := teamAliases[base]; ok {
		if hint.base != "" {
			base = hint.base
		}
		if state == "" && country == "" {
			state = hint.state
		}
	}
	if state == "" && country == "" {
		if def, ok := defaultCountries[base]; ok {
			country = def
		} else if def, ok := defaultStates[base]; ok {
			state = def
		}
	}
	if country == "BRA" {
		country = ""
	}
	return nameParts{Base: base, State: state, Country: country, Pretty: pretty}
}

// trimTrailingWords drops n trailing words (and any separator left behind) from
// a raw name, so "América - MG" displays as "América" and "Palmeiras-SP" as
// "Palmeiras".
func trimTrailingWords(s string, n int) string {
	out := strings.TrimSpace(s)
	for ; n > 0; n-- {
		cut := strings.LastIndexAny(out, " -–—/")
		if cut <= 0 {
			break
		}
		out = strings.TrimRight(strings.TrimSpace(out[:cut]), " -–—/")
	}
	return strings.TrimSpace(out)
}

// trimLeadingWords drops n leading words, mirroring the removal of club-type
// prefixes ("EC Vitoria" -> "Vitoria").
func trimLeadingWords(s string, n int) string {
	out := strings.TrimSpace(s)
	for ; n > 0; n-- {
		cut := strings.IndexAny(out, " -–—/")
		if cut < 0 || cut+1 >= len(out) {
			break
		}
		out = strings.TrimLeft(strings.TrimSpace(out[cut+1:]), " -–—/")
	}
	return strings.TrimSpace(out)
}

// teamID builds the canonical, URL-safe team identifier.
func teamID(base, state, country string) string {
	id := base
	switch {
	case country != "":
		id += " " + strings.ToLower(country)
	case state != "":
		id += " " + strings.ToLower(state)
	}
	return strings.ReplaceAll(id, " ", "-")
}

// titleCase renders a folded base as a last-resort display name.
func titleCase(base string) string {
	words := strings.Fields(base)
	for i, w := range words {
		r := []rune(w)
		r[0] = unicode.ToUpper(r[0])
		words[i] = string(r)
	}
	return strings.Join(words, " ")
}

// accentScore counts non-ASCII runes; used to prefer "Atlético" over "Atletico"
// when picking a display name among equivalent spellings.
func accentScore(s string) int {
	n := 0
	for _, r := range s {
		if r > unicode.MaxASCII {
			n++
		}
	}
	return n
}
