package main

// Team name normalisation.
//
// The datasets spell the same club many ways ("Palmeiras-SP", "Palmeiras - SP",
// "Palmeiras", "Sao Paulo", "São Paulo", "Atletico Mineiro", "Atlético-MG"...).
// Every name is reduced to a (base, state) pair: base is an accent-free,
// lower-case club name with generic tokens (FC, EC, ...) removed, and state is
// the Brazilian UF (or a country code in Libertadores data) when one is given.
// The team key is "base|state"; names without a state are resolved to the
// state of the best-known club with that base (see Registry).

import (
	"regexp"
	"sort"
	"strings"
	"unicode"
)

var accentMap = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n',
}

// fold lower-cases s, strips accents and replaces punctuation with spaces.
func fold(s string) string {
	var b strings.Builder
	space := true
	for _, r := range strings.ToLower(s) {
		if m, ok := accentMap[r]; ok {
			r = m
		}
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			b.WriteRune(r)
			space = false
		} else if !space {
			b.WriteByte(' ')
			space = true
		}
	}
	return strings.TrimSpace(b.String())
}

var regionCodes = func() map[string]bool {
	m := map[string]bool{}
	for _, c := range strings.Fields("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO " +
		"URU PAR EQU VEN PER ARG CHI BOL COL MEX") {
		m[c] = true
	}
	return m
}()

var (
	reParen       = regexp.MustCompile(`\(([^)]*)\)`)
	reStateSuffix = regexp.MustCompile(`^(.*\S)(?:\s*-\s*|\s+)([A-Za-z]{2,3})$`)
	reSpaces      = regexp.MustCompile(`\s+`)
)

// Names whose trailing token looks like a state code but is not one.
var fullNameAliases = map[string][2]string{
	"boavista sc saquarema": {"boavista", "RJ"},
	"central sc":            {"central", "PE"},
	"sao jose poa":          {"sao jose", "RS"},
	"brasil de pelotas":     {"brasil", "RS"},
	"river ac":              {"river", "PI"},
	"sao jose pa":           {"sao jose", "RS"},
}

// Clubs commonly referred to by base name plus state; they get a fixed
// identity and display name so that e.g. the three "Atlético" clubs never mix.
type special struct{ base, state, display string }

var specials = map[string]special{
	"atletico|MG":                     {"atletico-mg", "MG", "Atlético-MG"},
	"atletico mineiro|":               {"atletico-mg", "MG", "Atlético-MG"},
	"atletico|":                       {"atletico-mg", "MG", "Atlético-MG"},
	"atletico|PR":                     {"athletico-pr", "PR", "Athletico-PR"},
	"athletico|PR":                    {"athletico-pr", "PR", "Athletico-PR"},
	"athletico|":                      {"athletico-pr", "PR", "Athletico-PR"},
	"atletico paranaense|":            {"athletico-pr", "PR", "Athletico-PR"},
	"athletico paranaense|":           {"athletico-pr", "PR", "Athletico-PR"},
	"atletico|GO":                     {"atletico-go", "GO", "Atlético-GO"},
	"atletico goianiense|":            {"atletico-go", "GO", "Atlético-GO"},
	"atletico|AC":                     {"atletico acreano", "AC", "Atlético Acreano"},
	"atletico acreano|":               {"atletico acreano", "AC", "Atlético Acreano"},
	"america|MG":                      {"america-mg", "MG", "América-MG"},
	"america|":                        {"america-mg", "MG", "América-MG"},
	"america mineiro|":                {"america-mg", "MG", "América-MG"},
	"america|RN":                      {"america-rn", "RN", "América-RN"},
	"america natal|":                  {"america-rn", "RN", "América-RN"},
	"america de natal|":               {"america-rn", "RN", "América-RN"},
	"america fc natal|":               {"america-rn", "RN", "América-RN"},
	"atletico|BA":                     {"atletico alagoinhas", "BA", "Atlético de Alagoinhas"},
	"atletico alagoinhas|":            {"atletico alagoinhas", "BA", "Atlético de Alagoinhas"},
	"operario ferroviario|":           {"operario", "PR", ""},
	"operario ferroviario esporte c|": {"operario", "PR", ""},
}

// Alternative club names, keyed and valued by folded base.
var baseAliases = map[string]string{
	"vasco da gama":                    "vasco",
	"sport recife":                     "sport",
	"sport club do recife":             "sport",
	"nautico capibaribe":               "nautico",
	"portuguesa desportos":             "portuguesa",
	"portuguesa de desportos":          "portuguesa",
	"cs alagoano":                      "csa",
	"clube do remo":                    "remo",
	"red bull bragantino":              "bragantino",
	"rb bragantino":                    "bragantino",
	"ceara sporting":                   "ceara",
	"sport club corinthians paulista":  "corinthians",
	"corinthians paulista":             "corinthians",
	"moto":                             "moto club",
	"moto club de sao luis":            "moto club",
	"xv piracicaba":                    "xv de piracicaba",
	"iv de julho":                      "4 de julho",
	"ser caxias":                       "caxias",
	"aguia de maraba":                  "aguia",
	"palmas fr":                        "palmas",
	"palmas ltda":                      "palmas",
	"gremio novorizontino":             "novorizontino",
	"guarany":                          "guarany de sobral",
	"flamengo do piaui":                "flamengo",
	"real noroeste capixaba":           "real noroeste",
	"uniao de rondonopolis":            "uniao rondonopolis",
	"desportiva ferroviaria":           "desportiva",
	"gremio barueri":                   "barueri",
	"gremio foot ball porto alegrense": "gremio",
	"cr flamengo":                      "flamengo",
	"clube de regatas do flamengo":     "flamengo",
	"sociedade esportiva palmeiras":    "palmeiras",
	"metropolitano maringa":            "maringa",
	"afogados da ingazeira":            "afogados",
	"macae esporte":                    "macae",
	"auto esporte":                     "auto esporte",
	"esportivo bento goncalves":        "esportivo",
	"sete de setembro":                 "7 de setembro",
	"souza":                            "sousa",
	"retro fc brasil":                  "retro",
	"cs sergipe":                       "sergipe",
	"rondonopolis":                     "uniao rondonopolis",
	"s francisco":                      "sao francisco",
	"sao mateus es":                    "sao mateus",
}

// Home state of well-known clubs, used when a name carries no state.
var defaultStates = map[string]string{
	"flamengo": "RJ", "fluminense": "RJ", "botafogo": "RJ", "vasco": "RJ",
	"palmeiras": "SP", "corinthians": "SP", "santos": "SP", "sao paulo": "SP",
	"bragantino": "SP", "portuguesa": "SP", "guarani": "SP", "ponte preta": "SP",
	"gremio": "RS", "internacional": "RS", "juventude": "RS",
	"cruzeiro": "MG", "bahia": "BA", "vitoria": "BA", "sport": "PE",
	"nautico": "PE", "santa cruz": "PE", "fortaleza": "CE", "ceara": "CE",
	"goias": "GO", "coritiba": "PR", "parana": "PR", "chapecoense": "SC",
	"figueirense": "SC", "avai": "SC", "criciuma": "SC", "cuiaba": "MT",
	"operario": "PR", "boavista": "RJ", "csa": "AL",
}

// Foreign clubs that share a base name with suffixed clubs and must stay
// separate when they appear without a suffix.
var standaloneBases = map[string]bool{"river plate": true, "nacional": true}

var (
	prefixTokens = map[string]bool{"ec": true, "fc": true, "sc": true, "ad": true, "ae": true, "ca": true, "ce": true, "se": true, "ge": true}
	suffixTokens = map[string]bool{"ec": true, "fc": true, "sc": true, "clube": true, "club": true}
	// dropped together with a following "clube"/"club"
	suffixQualifiers = map[string]bool{"futebol": true, "esporte": true, "sport": true}
)

// parsedName is the result of analysing one raw team name.
type parsedName struct {
	base    string // folded canonical base
	state   string // explicit state/country code, "" if none
	display string // cleaned original spelling of the base ("" if aliased)
	forced  string // fixed display name for special clubs
}

// parseName splits a raw team name into base and state. When lenient is set
// (user input) a lower-case trailing state code is accepted as well.
func parseName(raw string, lenient bool) parsedName {
	s := strings.TrimSpace(raw)
	state := ""
	if a, ok := fullNameAliases[fold(s)]; ok {
		return parsedName{base: a[0], state: a[1]}
	}
	for _, m := range reParen.FindAllStringSubmatch(s, -1) {
		if regionCodes[m[1]] {
			state = m[1]
		}
	}
	s = strings.TrimSpace(reParen.ReplaceAllString(s, " "))
	if m := reStateSuffix.FindStringSubmatch(s); m != nil && state == "" {
		code := m[2]
		if lenient {
			code = strings.ToUpper(code)
		}
		if regionCodes[code] {
			state = code
			s = strings.TrimRight(strings.TrimSpace(m[1]), "- ")
		}
	}
	s = strings.ReplaceAll(s, ".", " ")
	s = strings.TrimSpace(reSpaces.ReplaceAllString(s, " "))

	toks := joinInitials(strings.Fields(fold(s)))
	base := strings.Join(toks, " ")
	if a, ok := baseAliases[base]; ok {
		base = a
	} else {
		for len(toks) > 1 && prefixTokens[toks[0]] {
			toks = toks[1:]
		}
		for len(toks) > 1 && suffixTokens[toks[len(toks)-1]] {
			club := strings.HasPrefix(toks[len(toks)-1], "clu")
			toks = toks[:len(toks)-1]
			if club && len(toks) > 1 && suffixQualifiers[toks[len(toks)-1]] {
				toks = toks[:len(toks)-1]
			}
		}
		base = strings.Join(toks, " ")
		if a, ok := baseAliases[base]; ok {
			base = a
		}
	}
	p := parsedName{base: base, state: state}
	sp, ok := specials[base+"|"+state]
	if !ok && state != "" {
		if sp, ok = specials[base+"|"]; ok && sp.state != state {
			ok = false
		}
	}
	if ok {
		p.base, p.state, p.forced = sp.base, sp.state, sp.display
		return p
	}
	if fold(s) == base {
		p.display = s
	}
	return p
}

// joinInitials merges runs of single letters ("c r b" -> "crb").
func joinInitials(toks []string) []string {
	var out []string
	run := ""
	flush := func() {
		if run != "" {
			out = append(out, run)
			run = ""
		}
	}
	for i, t := range toks {
		single := len(t) == 1 && t[0] >= 'a' && t[0] <= 'z'
		next := i+1 < len(toks) && len(toks[i+1]) == 1
		if single && (run != "" || next) {
			run += t
			continue
		}
		flush()
		out = append(out, t)
	}
	flush()
	return out
}

// Team is one canonical club.
type Team struct {
	Key     string
	Base    string
	State   string
	Name    string
	Matches int
}

// Registry maps raw names to canonical teams. Names are observed first, then
// Freeze resolves stateless names and picks display names.
type Registry struct {
	stateCount map[string]map[string]int // base -> state -> observations
	variants   map[string]map[string]int // key -> spelling -> observations
	forced     map[string]string         // key -> fixed display name
	Teams      map[string]*Team
	byBase     map[string][]*Team
	derbies    map[string]string // "keyA\x00keyB" -> rivalry name
}

func NewRegistry() *Registry {
	return &Registry{
		stateCount: map[string]map[string]int{},
		variants:   map[string]map[string]int{},
		forced:     map[string]string{},
		Teams:      map[string]*Team{},
		byBase:     map[string][]*Team{},
	}
}

func (r *Registry) observe(raw string) {
	p := parseName(raw, false)
	if r.stateCount[p.base] == nil {
		r.stateCount[p.base] = map[string]int{}
	}
	r.stateCount[p.base][p.state]++
}

// resolveState picks the state for a name observed without one.
func (r *Registry) resolveState(base string, international bool) string {
	if st, ok := defaultStates[base]; ok {
		return st
	}
	if standaloneBases[base] {
		return ""
	}
	best, bestN := "", 0
	for st, n := range r.stateCount[base] {
		if st == "" || (international && len(st) != 3) || (!international && len(st) != 2) {
			continue
		}
		if n > bestN || (n == bestN && st < best) {
			best, bestN = st, n
		}
	}
	return best
}

// keyFor returns the canonical key for a raw dataset name.
func (r *Registry) keyFor(raw string, international bool) string {
	p := parseName(raw, false)
	st := p.state
	if st == "" {
		st = r.resolveState(p.base, international)
	}
	key := p.base + "|" + st
	if _, ok := r.Teams[key]; !ok {
		t := &Team{Key: key, Base: p.base, State: st}
		r.Teams[key] = t
		r.byBase[p.base] = append(r.byBase[p.base], t)
		r.variants[key] = map[string]int{}
	}
	if p.display != "" {
		r.variants[key][p.display]++
	}
	if p.forced != "" {
		r.forced[key] = p.forced
	}
	return key
}

// Freeze assigns display names once all matches have been counted.
func (r *Registry) Freeze() {
	for base, teams := range r.byBase {
		sort.Slice(teams, func(i, j int) bool {
			if teams[i].Matches != teams[j].Matches {
				return teams[i].Matches > teams[j].Matches
			}
			return teams[i].Key < teams[j].Key
		})
		for i, t := range teams {
			name := r.forced[t.Key]
			if name == "" {
				name = bestVariant(r.variants[t.Key])
			}
			if name == "" {
				name = strings.Title(base) //nolint:staticcheck // ASCII-only input
			}
			t.Name = name
			if i > 0 && t.State != "" {
				t.Name = name + "-" + t.State
			}
		}
	}
}

// bestVariant prefers accented, properly capitalised, frequent spellings.
func bestVariant(v map[string]int) string {
	best, bestScore := "", -1
	for s, n := range v {
		score := n
		for _, c := range s {
			if c > 127 {
				score += 1_000_000
			} else if unicode.IsUpper(c) {
				score += 10_000
			}
		}
		if score > bestScore || (score == bestScore && s < best) {
			best, bestScore = s, score
		}
	}
	return best
}

// Find resolves user input to a team. It tries an exact normalised match and
// falls back to word-containment matching, preferring clubs with more matches.
func (r *Registry) Find(query string) (*Team, bool) {
	if strings.TrimSpace(query) == "" {
		return nil, false
	}
	for _, lenient := range []bool{false, true} {
		p := parseName(query, lenient)
		teams := r.byBase[p.base]
		if len(teams) == 0 {
			continue
		}
		if p.state != "" {
			if t, ok := r.Teams[p.base+"|"+p.state]; ok {
				return t, true
			}
			continue
		}
		if st, ok := defaultStates[p.base]; ok {
			if t, ok := r.Teams[p.base+"|"+st]; ok {
				return t, true
			}
		}
		return teams[0], true
	}
	q := " " + fold(query) + " "
	var best *Team
	bestLen := 0
	for _, t := range r.Teams {
		b := " " + strings.ReplaceAll(t.Base, "-", " ") + " "
		n := fold(t.Name)
		hit := (len(t.Base) >= 6 && strings.Contains(q, b)) || strings.Contains(" "+n+" ", q)
		if !hit {
			continue
		}
		l := len(t.Base)
		if best == nil || l > bestLen || (l == bestLen && (t.Matches > best.Matches || (t.Matches == best.Matches && t.Key < best.Key))) {
			best, bestLen = t, l
		}
	}
	return best, best != nil
}
