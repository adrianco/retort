package soccer

import (
	"regexp"
	"sort"
	"strings"
	"unicode"
)

// Fold lower-cases a string and strips Portuguese/Spanish accents so that
// "São Paulo", "Sao Paulo" and "SAO PAULO" compare equal.
func Fold(s string) string {
	return accentFolder.Replace(strings.ToLower(strings.TrimSpace(s)))
}

var accentFolder = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u",
	"ç", "c", "ñ", "n",
)

// Tokens splits folded text into words, dropping punctuation and gluing
// runs of single letters back together ("C. R. B." -> "crb").
func Tokens(s string) []string {
	words := strings.FieldsFunc(Fold(s), func(r rune) bool {
		return !(unicode.IsLetter(r) || unicode.IsDigit(r) || r == '.' || r == '\'')
	})
	var out []string
	var initials strings.Builder
	flush := func() {
		if initials.Len() > 0 {
			out = append(out, initials.String())
			initials.Reset()
		}
	}
	for _, w := range words {
		parts := strings.Split(strings.ReplaceAll(w, "'", ""), ".")
		for _, p := range parts {
			if p == "" {
				continue
			}
			if len([]rune(p)) == 1 {
				initials.WriteString(p)
				continue
			}
			flush()
			out = append(out, p)
		}
	}
	flush()
	return out
}

// Brazilian state codes (UF) and the country codes used in Libertadores data.
var (
	brazilianStates = set("AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
		"PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO")
	countryCodes = set("URU", "PAR", "EQU", "ECU", "PER", "VEN", "BOL", "CHI", "ARG", "COL", "MEX")
	stateNames   = map[string]string{
		"minas gerais": "MG", "sao paulo": "SP", "rio de janeiro": "RJ", "rio grande do sul": "RS",
		"parana": "PR", "bahia": "BA", "pernambuco": "PE", "ceara": "CE", "goias": "GO", "santa catarina": "SC",
	}

	parenthetical = regexp.MustCompile(`\s*\(([^)]*)\)\s*`)
	dashSuffix    = regexp.MustCompile(`\s*-\s*([A-Za-z]{2,3})\s*$`)
	spaceSuffix   = regexp.MustCompile(`\s+([A-Z]{2})\s*$`)
)

func set(items ...string) map[string]bool {
	m := make(map[string]bool, len(items))
	for _, i := range items {
		m[i] = true
	}
	return m
}

// fillerTokens are club-type abbreviations that vary between datasets and
// carry no identity ("Fortaleza EC", "EC Bahia", "Sao Paulo FC").
var (
	leadingFiller  = set("ec", "fc", "sc", "se", "ce", "ad", "ae", "ge", "cs", "ca")
	trailingFiller = set("ec", "fc", "sc", "clube", "club", "futebol", "esporte")
)

// alias maps a cleaned base name (optionally "base|QUALIFIER") to the
// canonical club, with the display name to use for it.
type alias struct {
	base, qualifier, display string
}

var aliases = map[string]alias{
	"athletico":                       {"athletico paranaense", "PR", "Athletico Paranaense"},
	"athletico|PR":                    {"athletico paranaense", "PR", "Athletico Paranaense"},
	"athletico paranaense":            {"athletico paranaense", "PR", "Athletico Paranaense"},
	"atletico paranaense":             {"athletico paranaense", "PR", "Athletico Paranaense"},
	"atletico|PR":                     {"athletico paranaense", "PR", "Athletico Paranaense"},
	"atletico|MG":                     {"atletico mineiro", "MG", "Atlético Mineiro"},
	"atletico mineiro":                {"atletico mineiro", "MG", "Atlético Mineiro"},
	"atletico|GO":                     {"atletico goianiense", "GO", "Atlético Goianiense"},
	"atletico goianiense":             {"atletico goianiense", "GO", "Atlético Goianiense"},
	"america fc natal":                {"america", "RN", ""},
	"america natal":                   {"america", "RN", ""},
	"america mineiro":                 {"america", "MG", ""},
	"sport club corinthians paulista": {"corinthians", "SP", "Corinthians"},
	"corinthians paulista":            {"corinthians", "SP", "Corinthians"},
	"sociedade esportiva palmeiras":   {"palmeiras", "SP", "Palmeiras"},
	"vasco":                           {"vasco da gama", "", "Vasco da Gama"},
	"vasco da gama":                   {"vasco da gama", "", "Vasco da Gama"},
	"cr vasco da gama":                {"vasco da gama", "RJ", "Vasco da Gama"},
	"sport":                           {"sport", "", "Sport Recife"},
	"sport recife":                    {"sport", "PE", "Sport Recife"},
	"sport club do recife":            {"sport", "PE", "Sport Recife"},
	"nautico capibaribe":              {"nautico", "PE", ""},
	"portuguesa desportos":            {"portuguesa", "SP", ""},
	"red bull bragantino":             {"bragantino", "SP", "Red Bull Bragantino"},
	"bragantino|SP":                   {"bragantino", "SP", "Red Bull Bragantino"},
	"ceara sporting club":             {"ceara", "CE", ""},
	"ceara sporting":                  {"ceara", "CE", ""},
	"gremio novorizontino":            {"novorizontino", "SP", ""},
	"gremio barueri":                  {"barueri", "SP", ""},
	"clube do remo":                   {"remo", "PA", ""},
	"boavista sport":                  {"boavista", "RJ", ""},
	"sao paulo futebol clube":         {"sao paulo", "SP", "São Paulo"},
	"fluminense football club":        {"fluminense", "RJ", "Fluminense"},
	"cruzeiro esporte clube":          {"cruzeiro", "MG", "Cruzeiro"},
}

// TeamName is a raw name from a dataset broken into its identity parts.
type TeamName struct {
	Base      string // folded, cleaned name, e.g. "sao paulo"
	Qualifier string // state (UF) or country code, e.g. "SP", "URU"
	Display   string // the cleaned original spelling, e.g. "São Paulo"
	Fixed     string // a fixed display name from the alias table, if any
}

// ParseTeamName extracts the identity of a club from any of the naming
// styles the datasets use: "Palmeiras-SP", "Palmeiras - SP", "Botafogo RJ",
// "Nacional (URU)", "Sport Club Corinthians Paulista", "América FC (Minas Gerais)".
func ParseTeamName(raw string) TeamName {
	s := strings.TrimSpace(raw)
	qualifier := ""
	s = parenthetical.ReplaceAllStringFunc(s, func(m string) string {
		inner := strings.TrimSpace(parenthetical.FindStringSubmatch(m)[1])
		switch {
		case countryCodes[strings.ToUpper(inner)]:
			qualifier = strings.ToUpper(inner)
		case stateNames[Fold(inner)] != "":
			qualifier = stateNames[Fold(inner)]
		}
		return " "
	})
	s = strings.TrimSpace(s)
	if m := dashSuffix.FindStringSubmatch(s); m != nil {
		code := strings.ToUpper(m[1])
		if brazilianStates[code] || countryCodes[code] {
			qualifier = code
			s = strings.TrimSpace(s[:len(s)-len(m[0])])
		}
	}
	if m := spaceSuffix.FindStringSubmatch(s); m != nil && brazilianStates[m[1]] && len(strings.Fields(s)) > 1 {
		qualifier = m[1]
		s = strings.TrimSpace(s[:len(s)-len(m[0])])
	}
	if qualifier == "EQU" {
		qualifier = "ECU"
	}

	display := trimFillerWords(strings.Fields(s))
	base := strings.Join(trimFiller(Tokens(strings.Join(display, " "))), " ")
	tn := TeamName{Base: base, Qualifier: qualifier, Display: strings.Join(display, " ")}
	if a, ok := aliases[base+"|"+qualifier]; ok {
		tn.apply(a)
	} else if a, ok := aliases[base]; ok {
		tn.apply(a)
	}
	return tn
}

func (tn *TeamName) apply(a alias) {
	tn.Base = a.base
	if a.qualifier != "" {
		tn.Qualifier = a.qualifier
	}
	tn.Fixed = a.display
}

func trimFiller(tokens []string) []string {
	for len(tokens) > 1 && leadingFiller[tokens[0]] {
		tokens = tokens[1:]
	}
	for len(tokens) > 1 && trailingFiller[tokens[len(tokens)-1]] {
		tokens = tokens[:len(tokens)-1]
	}
	return tokens
}

func trimFillerWords(words []string) []string {
	clean := func(w string) string { return strings.Join(Tokens(w), "") }
	for len(words) > 1 && leadingFiller[clean(words[0])] {
		words = words[1:]
	}
	for len(words) > 1 && trailingFiller[clean(words[len(words)-1])] {
		words = words[:len(words)-1]
	}
	return words
}

// TeamID identifies one club across every dataset.
type TeamID string

// Teams is the registry of every club seen in the match data. It settles
// which state an unqualified name ("Flamengo") refers to, and how each club
// is displayed.
type Teams struct {
	defaults map[string]string // base -> most common Brazilian state
	names    map[TeamID]map[string]int
	fixed    map[TeamID]string
	display  map[TeamID]string
	matches  map[TeamID]int
	byBase   map[string][]TeamID
	qualCnt  map[string]map[string]int
	pending  []TeamName
}

func NewTeams() *Teams {
	return &Teams{
		defaults: map[string]string{}, names: map[TeamID]map[string]int{}, fixed: map[TeamID]string{},
		display: map[TeamID]string{}, matches: map[TeamID]int{}, byBase: map[string][]TeamID{},
		qualCnt: map[string]map[string]int{},
	}
}

// Observe records a raw name seen in the data, before Settle is called.
func (t *Teams) Observe(tn TeamName) {
	if brazilianStates[tn.Qualifier] {
		if t.qualCnt[tn.Base] == nil {
			t.qualCnt[tn.Base] = map[string]int{}
		}
		t.qualCnt[tn.Base][tn.Qualifier]++
	}
}

// Settle decides the default state for each club name once all data is seen.
func (t *Teams) Settle() {
	for base, counts := range t.qualCnt {
		best, bestN := "", -1
		for q, n := range counts {
			if n > bestN || (n == bestN && q < best) {
				best, bestN = q, n
			}
		}
		t.defaults[base] = best
	}
}

// ID gives the identity of a parsed name, applying the default state when
// the name carries none.
func (t *Teams) ID(tn TeamName) TeamID {
	q := tn.Qualifier
	if q == "" {
		q = t.defaults[tn.Base]
	}
	return TeamID(tn.Base + "|" + q)
}

// Register records that a match involving this name was loaded.
func (t *Teams) Register(tn TeamName) TeamID {
	id := t.ID(tn)
	if t.names[id] == nil {
		t.names[id] = map[string]int{}
		t.byBase[tn.Base] = append(t.byBase[tn.Base], id)
	}
	t.names[id][tn.Display]++
	if tn.Fixed != "" {
		t.fixed[id] = tn.Fixed
	}
	t.matches[id]++
	t.display[id] = ""
	return id
}

// Name is how a club is shown to the fan.
func (t *Teams) Name(id TeamID) string {
	if d := t.display[id]; d != "" {
		return d
	}
	d := t.computeName(id)
	t.display[id] = d
	return d
}

func (t *Teams) computeName(id TeamID) string {
	base, q, _ := strings.Cut(string(id), "|")
	name := t.fixed[id]
	if name == "" {
		best, bestScore := "", -1
		for n, count := range t.names[id] {
			score := accentCount(n)*100000 + upperStart(n)*10000 + count
			if score > bestScore || (score == bestScore && n < best) {
				best, bestScore = n, score
			}
		}
		name = best
	}
	if name == "" {
		name = base
	}
	if q == "" {
		return name
	}
	if countryCodes[q] {
		return name + " (" + q + ")"
	}
	if len(t.byBase[base]) > 1 && t.defaults[base] != q && t.fixed[id] == "" {
		return name + "-" + q
	}
	return name
}

func accentCount(s string) int {
	n := 0
	for _, r := range s {
		if r > unicode.MaxASCII {
			n++
		}
	}
	return n
}

func upperStart(s string) int {
	for _, r := range s {
		if unicode.IsUpper(r) {
			return 1
		}
		return 0
	}
	return 0
}

// Resolve finds the club a fan means. It tries an exact identity first, then
// the same name in any state, then names containing the words asked for.
func (t *Teams) Resolve(query string) (TeamID, bool) {
	tn := ParseTeamName(query)
	if tn.Base == "" {
		return "", false
	}
	if id := t.ID(tn); t.names[id] != nil {
		return id, true
	}
	if ids := t.byBase[tn.Base]; len(ids) > 0 {
		return t.mostPlayed(ids), true
	}
	var candidates []TeamID
	words := strings.Fields(tn.Base)
	for id := range t.names {
		base, _, _ := strings.Cut(string(id), "|")
		if containsWords(strings.Fields(base), words) || containsWords(Tokens(t.Name(id)), words) {
			candidates = append(candidates, id)
		}
	}
	if len(candidates) == 0 {
		return "", false
	}
	return t.mostPlayed(candidates), true
}

// ResolveExact finds a club only by exact identity, as used for linking
// FIFA club names to clubs in the match data.
func (t *Teams) ResolveExact(name string) (TeamID, bool) {
	id := t.ID(ParseTeamName(name))
	return id, t.names[id] != nil
}

func (t *Teams) mostPlayed(ids []TeamID) TeamID {
	sort.Slice(ids, func(i, j int) bool {
		if t.matches[ids[i]] != t.matches[ids[j]] {
			return t.matches[ids[i]] > t.matches[ids[j]]
		}
		return ids[i] < ids[j]
	})
	return ids[0]
}

func containsWords(have, want []string) bool {
	if len(want) == 0 {
		return false
	}
	pos := map[string]bool{}
	for _, h := range have {
		pos[h] = true
	}
	for _, w := range want {
		if !pos[w] {
			return false
		}
	}
	return true
}
