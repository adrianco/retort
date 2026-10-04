// normalize.go — text folding and team-name normalization.
//
// The datasets spell the same club in many ways ("Palmeiras-SP",
// "Palmeiras - SP", "Palmeiras", "SE Palmeiras", "Atlético Paranaense",
// "Athletico-PR", "Athletico"). Every raw name is reduced to a canonical
// team key of the form "<folded base name>|<state or country code>", e.g.
// "flamengo|RJ" or "nacional|URU". A curated table of major clubs supplies
// aliases and nice display names; all other teams get generic keys. Names
// that carry no state are attached to the single stated variant of the same
// base name when one exists (see TeamRegistry.Finalize).
package main

import (
	"sort"
	"strings"
	"unicode"
)

// foldMap strips diacritics from the Latin characters used in Portuguese
// and Spanish club names.
var foldMap = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'ø': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y', 'ÿ': 'y',
}

// Fold lower-cases s, removes accents, turns punctuation into spaces
// (dots are dropped so "C.R.B." becomes "crb") and collapses whitespace.
func Fold(s string) string {
	var b strings.Builder
	for _, r := range strings.ToLower(s) {
		if f, ok := foldMap[r]; ok {
			r = f
		}
		switch {
		case r == '.' || r == '\'' || r == '’':
			// drop
		case unicode.IsLetter(r) || unicode.IsDigit(r):
			b.WriteRune(r)
		default:
			b.WriteRune(' ')
		}
	}
	return strings.Join(strings.Fields(b.String()), " ")
}

// Brazilian federative unit codes.
var brStates = map[string]bool{
	"AC": true, "AL": true, "AP": true, "AM": true, "BA": true, "CE": true, "DF": true,
	"ES": true, "GO": true, "MA": true, "MT": true, "MS": true, "MG": true, "PA": true,
	"PB": true, "PR": true, "PE": true, "PI": true, "RJ": true, "RN": true, "RS": true,
	"RO": true, "RR": true, "SC": true, "SP": true, "SE": true, "TO": true,
}

// Country qualifiers used in the Libertadores file ("Nacional (URU)", "Barcelona-EQU").
var countryCodes = map[string]bool{
	"URU": true, "PAR": true, "EQU": true, "PER": true, "ARG": true, "CHI": true,
	"BOL": true, "COL": true, "VEN": true, "MEX": true, "ECU": true,
}

// Club-type tokens that carry no identity ("EC Bahia", "Nova Mutum EC").
var prefixNoise = map[string]bool{"ec": true, "fc": true, "sc": true, "ad": true, "ae": true, "ce": true, "ge": true, "cs": true, "se": true, "cr": true}
var suffixNoise = map[string]bool{"ec": true, "fc": true, "sc": true, "clube": true}

// SplitTeamName folds a raw team name and separates a trailing state or
// country qualifier. It returns the folded base name and the upper-case
// qualifier ("" if none).
func SplitTeamName(raw string) (base, qual string) {
	if a, ok := rawAliases[Fold(raw)]; ok {
		return a[0], a[1]
	}
	s := raw
	// Parenthesised country code: "Nacional (URU)". Other parentheticals
	// ("(antigo Esporte Clube Barreira)") are discarded.
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
		inner := strings.ToUpper(strings.TrimSpace(s[i+1 : i+j]))
		if countryCodes[inner] || brStates[inner] {
			qual = inner
		}
		s = s[:i] + " " + s[i+j+1:]
	}
	toks := strings.Fields(Fold(s))
	if len(toks) > 1 && qual == "" {
		last := strings.ToUpper(toks[len(toks)-1])
		if brStates[last] || countryCodes[last] {
			qual = last
			toks = toks[:len(toks)-1]
		}
	}
	for len(toks) > 1 && prefixNoise[toks[0]] {
		toks = toks[1:]
	}
	for len(toks) > 1 && suffixNoise[toks[len(toks)-1]] {
		toks = toks[:len(toks)-1]
	}
	for _, suf := range [][]string{{"futebol", "clube"}, {"f", "c"}, {"s", "c"}} {
		if n := len(toks); n > len(suf) && toks[n-2] == suf[0] && toks[n-1] == suf[1] {
			toks = toks[:n-2]
		}
	}
	if qual == "ECU" {
		qual = "EQU"
	}
	return strings.Join(toks, " "), qual
}

// rawAliases fixes spellings that the generic rules get wrong, keyed by the
// folded raw name: value is {base, qualifier}.
var rawAliases = map[string][2]string{
	"river ac":                  {"river", "PI"}, // River Atlético Clube (Teresina), not Acre
	"moto clube":                {"moto club", "MA"},
	"moto club de sao luis":     {"moto club", "MA"},
	"brasil de pelotas":         {"brasil", "RS"},
	"metropolitano maringa pr":  {"maringa", "PR"},
	"sousa ec":                  {"souza", "PB"},
	"boavista sc saquarema":     {"boavista", "RJ"},
	"retro fc brasil":           {"retro", "PE"},
	"esportivo bento goncalves": {"esportivo", "RS"},
	"atletico alagoinhas":       {"atletico", "BA"},
	"atletico acreano":          {"atletico", "AC"},
	"uniao rondonopolis":        {"uniao", "MT"},
	"uniao de rondonopolis mt":  {"uniao", "MT"},
}

// canonicalClub describes a well-known club: its display name, home state
// and the folded base names (without state) that refer to it.
type canonicalClub struct {
	Display string
	State   string
	Aliases []string
}

// canonicalClubs lists the clubs that matter most for the queries. The first
// club listed for an alias is the default when no state is given (so plain
// "Atletico" means Atlético-MG and plain "Botafogo" means Botafogo-RJ).
var canonicalClubs = []canonicalClub{
	{"Flamengo", "RJ", []string{"flamengo", "clube de regatas do flamengo", "fla", "mengao"}},
	{"Fluminense", "RJ", []string{"fluminense", "flu"}},
	{"Botafogo", "RJ", []string{"botafogo", "botafogo fr", "botafogo de futebol e regatas"}},
	{"Vasco da Gama", "RJ", []string{"vasco", "vasco da gama", "club de regatas vasco da gama"}},
	{"Palmeiras", "SP", []string{"palmeiras", "sociedade esportiva palmeiras", "verdao"}},
	{"Corinthians", "SP", []string{"corinthians", "sport club corinthians paulista", "corinthians paulista", "timao"}},
	{"São Paulo", "SP", []string{"sao paulo", "sao paulo futebol clube", "spfc", "tricolor paulista"}},
	{"Santos", "SP", []string{"santos", "peixe"}},
	{"Red Bull Bragantino", "SP", []string{"bragantino", "red bull bragantino", "rb bragantino"}},
	{"Portuguesa", "SP", []string{"portuguesa", "portuguesa desportos", "associacao portuguesa de desportos"}},
	{"Ponte Preta", "SP", []string{"ponte preta", "macaca"}},
	{"Guarani", "SP", []string{"guarani"}},
	{"São Caetano", "SP", []string{"sao caetano"}},
	{"Santo André", "SP", []string{"santo andre"}},
	{"Grêmio Barueri", "SP", []string{"barueri", "gremio barueri"}},
	{"Grêmio Prudente", "SP", []string{"gremio prudente"}},
	{"Grêmio", "RS", []string{"gremio", "gremio fbpa", "gremio foot ball porto alegrense", "tricolor gaucho"}},
	{"Internacional", "RS", []string{"internacional", "inter", "sport club internacional", "colorado"}},
	{"Juventude", "RS", []string{"juventude"}},
	{"Atlético-MG", "MG", []string{"atletico", "atletico mineiro", "clube atletico mineiro", "atletico mg", "galo"}},
	{"Athletico-PR", "PR", []string{"athletico", "atletico", "athletico paranaense", "atletico paranaense", "clube atletico paranaense", "athletico pr", "atletico pr", "furacao"}},
	{"Atlético-GO", "GO", []string{"atletico", "atletico goianiense", "atletico go", "dragao"}},
	{"América-MG", "MG", []string{"america", "america mineiro", "america fc minas gerais", "america mg", "coelho"}},
	{"América-RN", "RN", []string{"america", "america fc natal", "america rn"}},
	{"Cruzeiro", "MG", []string{"cruzeiro", "cruzeiro esporte clube", "raposa"}},
	{"Ipatinga", "MG", []string{"ipatinga"}},
	{"Coritiba", "PR", []string{"coritiba", "coxa"}},
	{"Paraná", "PR", []string{"parana", "parana clube"}},
	{"Bahia", "BA", []string{"bahia", "esporte clube bahia"}},
	{"Vitória", "BA", []string{"vitoria", "esporte clube vitoria"}},
	{"Sport", "PE", []string{"sport", "sport recife", "sport club do recife"}},
	{"Náutico", "PE", []string{"nautico", "nautico capibaribe", "clube nautico capibaribe"}},
	{"Santa Cruz", "PE", []string{"santa cruz"}},
	{"Ceará", "CE", []string{"ceara", "ceara sporting club", "ceara sporting"}},
	{"Fortaleza", "CE", []string{"fortaleza", "fortaleza esporte clube"}},
	{"Goiás", "GO", []string{"goias", "goias esporte clube"}},
	{"Vila Nova", "GO", []string{"vila nova"}},
	{"Avaí", "SC", []string{"avai"}},
	{"Figueirense", "SC", []string{"figueirense"}},
	{"Chapecoense", "SC", []string{"chapecoense", "associacao chapecoense de futebol", "chape"}},
	{"Criciúma", "SC", []string{"criciuma"}},
	{"Joinville", "SC", []string{"joinville"}},
	{"CSA", "AL", []string{"csa", "centro sportivo alagoano"}},
	{"CRB", "AL", []string{"crb", "clube de regatas brasil"}},
	{"Cuiabá", "MT", []string{"cuiaba"}},
	{"Paysandu", "PA", []string{"paysandu"}},
	{"Remo", "PA", []string{"remo", "clube do remo"}},
	{"Brasiliense", "DF", []string{"brasiliense"}},
	{"River Plate", "ARG", []string{"river plate"}},
	{"Peñarol", "URU", []string{"penarol"}},
	{"Deportes Tolima", "COL", []string{"deportes tolima", "tolima"}},
	{"Bolívar", "BOL", []string{"bolivar"}},
}

// Team is a canonical team.
type Team struct {
	Key      string // e.g. "flamengo|RJ"
	Name     string // display name
	State    string // state or country code (may be empty)
	RawNames map[string]int
}

// TeamRegistry maps raw names to canonical teams.
type TeamRegistry struct {
	teams     map[string]*Team
	byRaw     map[string]*Team
	aliases   map[string][]*canonicalClub // folded alias -> candidate clubs
	pending   map[string]string           // raw name -> provisional key
	finalized bool
}

// NewTeamRegistry builds a registry seeded with the canonical club table.
func NewTeamRegistry() *TeamRegistry {
	r := &TeamRegistry{
		teams:   map[string]*Team{},
		byRaw:   map[string]*Team{},
		aliases: map[string][]*canonicalClub{},
		pending: map[string]string{},
	}
	for i := range canonicalClubs {
		c := &canonicalClubs[i]
		for _, a := range c.Aliases {
			r.aliases[a] = append(r.aliases[a], c)
		}
		key := canonicalKey(c)
		r.teams[key] = &Team{Key: key, Name: c.Display, State: c.State, RawNames: map[string]int{}}
	}
	return r
}

func canonicalKey(c *canonicalClub) string { return c.Aliases[0] + "|" + c.State }

// keyFor computes the provisional key for a base name and qualifier.
func (r *TeamRegistry) keyFor(base, qual string) (key string, canon *canonicalClub) {
	cands := r.aliases[base]
	if len(cands) > 0 {
		if qual == "" {
			return canonicalKey(cands[0]), cands[0]
		}
		for _, c := range cands {
			if c.State == qual {
				return canonicalKey(c), c
			}
		}
	}
	return base + "|" + qual, nil
}

// Register records a raw team name. stateHint is used when the raw name has
// no qualifier but the dataset provides the state in another column.
func (r *TeamRegistry) Register(raw, stateHint string) {
	raw = strings.TrimSpace(raw)
	if _, ok := r.pending[raw+"\x00"+stateHint]; ok {
		return
	}
	base, qual := SplitTeamName(raw)
	if qual == "" && brStates[strings.ToUpper(stateHint)] {
		// A state taken from a separate column is only a hint: some rows
		// are wrong (Vitória listed under ES), so a well-known club name
		// keeps its canonical identity unless the hint selects another
		// club of the same name.
		qual = strings.ToUpper(stateHint)
		if cands := r.aliases[base]; len(cands) > 0 {
			qual = cands[0].State
			for _, c := range cands {
				if c.State == strings.ToUpper(stateHint) {
					qual = c.State
				}
			}
		}
	}
	key, _ := r.keyFor(base, qual)
	r.pending[raw+"\x00"+stateHint] = key
}

// Finalize resolves provisional keys: a stateless generic name is merged into
// the single qualified variant of the same base, when exactly one exists.
func (r *TeamRegistry) Finalize() {
	qualified := map[string]map[string]bool{} // base -> set of quals
	for _, key := range r.pending {
		base, qual, _ := strings.Cut(key, "|")
		if qual != "" {
			if qualified[base] == nil {
				qualified[base] = map[string]bool{}
			}
			qualified[base][qual] = true
		}
	}
	for rk, key := range r.pending {
		raw, _, _ := strings.Cut(rk, "\x00")
		base, qual, _ := strings.Cut(key, "|")
		if qual == "" && len(qualified[base]) == 1 {
			for q := range qualified[base] {
				key = base + "|" + q
			}
		}
		t := r.teams[key]
		if t == nil {
			_, q, _ := strings.Cut(key, "|")
			t = &Team{Key: key, State: q, RawNames: map[string]int{}}
			r.teams[key] = t
		}
		t.RawNames[raw]++
		r.byRaw[rk] = t
	}
	// Display names for generic teams: prefer an accented spelling.
	for _, t := range r.teams {
		if t.Name != "" {
			continue
		}
		t.Name = genericDisplay(t)
	}
	r.finalized = true
}

func genericDisplay(t *Team) string {
	var names []string
	for n := range t.RawNames {
		names = append(names, n)
	}
	sort.Strings(names)
	best, bestScore := "", -1<<30
	for _, n := range names {
		clean := stripQualifier(n)
		// Prefer accented, short, properly capitalised spellings.
		score := -len(clean)
		for _, r := range clean {
			if r > unicode.MaxASCII {
				score += 10
			}
			if r == '.' {
				score -= 5
			}
		}
		if strings.ToLower(clean) == clean || (strings.ToUpper(clean) == clean && len(clean) > 4) {
			score -= 20
		}
		if score > bestScore {
			best, bestScore = clean, score
		}
	}
	if best == "" {
		best, _, _ = strings.Cut(t.Key, "|")
	}
	if t.State != "" {
		best += "-" + t.State
	}
	return best
}

// stripQualifier removes a trailing state/country and parentheticals from a raw name.
func stripQualifier(raw string) string {
	s := raw
	if i := strings.Index(s, "("); i >= 0 {
		s = s[:i]
	}
	s = strings.TrimSpace(s)
	for _, sep := range []string{" - ", "-", " "} {
		if i := strings.LastIndex(s, sep); i > 0 {
			tail := strings.ToUpper(strings.TrimSpace(s[i+len(sep):]))
			if brStates[tail] || countryCodes[tail] {
				return strings.TrimSpace(s[:i])
			}
		}
	}
	return s
}

// Lookup returns the team for a raw dataset name (after Finalize).
func (r *TeamRegistry) Lookup(raw, stateHint string) *Team {
	return r.byRaw[strings.TrimSpace(raw)+"\x00"+stateHint]
}

// Teams returns all teams sorted by display name.
func (r *TeamRegistry) Teams() []*Team {
	out := make([]*Team, 0, len(r.teams))
	for _, t := range r.teams {
		if len(t.RawNames) > 0 {
			out = append(out, t)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out
}

// Get returns a team by key.
func (r *TeamRegistry) Get(key string) *Team { return r.teams[key] }

// Resolve turns a free-text user query ("Sao Paulo FC", "Atlético Mineiro",
// "Palmeiras-SP") into the best matching teams. weight ranks candidates when
// the match is fuzzy (typically the team's match count). The first result is
// the best match; nil means nothing plausible was found.
func (r *TeamRegistry) Resolve(query string, weight func(*Team) int) []*Team {
	base, qual := SplitTeamName(query)
	if base == "" {
		return nil
	}
	if weight == nil {
		weight = func(*Team) int { return 0 }
	}
	// 1. Exact canonical / generic key.
	var exact []*Team
	key, _ := r.keyFor(base, qual)
	if t := r.teams[key]; t != nil && len(t.RawNames) > 0 {
		exact = []*Team{t}
	} else if qual == "" {
		// Generic names with one or more qualified variants.
		for _, t := range r.teams {
			if len(t.RawNames) == 0 {
				continue
			}
			if b, _, _ := strings.Cut(t.Key, "|"); b == base {
				exact = append(exact, t)
			}
		}
		sortByWeight(exact, weight)
	}
	// 2. Fuzzy: every query token must appear in the folded display name,
	// key or one of the raw names. Exact hits stay first.
	seen := map[*Team]bool{}
	for _, t := range exact {
		seen[t] = true
	}
	qtoks := strings.Fields(base)
	var fuzzy []*Team
	for _, t := range r.teams {
		if len(t.RawNames) == 0 || seen[t] {
			continue
		}
		if qual != "" && t.State != qual {
			continue
		}
		hay := Fold(t.Name) + " " + strings.ReplaceAll(t.Key, "|", " ")
		for n := range t.RawNames {
			hay += " " + Fold(n)
		}
		hayToks := map[string]bool{}
		for _, w := range strings.Fields(hay) {
			hayToks[w] = true
		}
		ok := true
		for _, q := range qtoks {
			if !hayToks[q] && !(len(q) >= 4 && strings.Contains(hay, q)) {
				ok = false
				break
			}
		}
		if ok {
			fuzzy = append(fuzzy, t)
		}
	}
	sortByWeight(fuzzy, weight)
	return append(exact, fuzzy...)
}

func sortByWeight(ts []*Team, weight func(*Team) int) {
	sort.SliceStable(ts, func(i, j int) bool {
		wi, wj := weight(ts[i]), weight(ts[j])
		if wi != wj {
			return wi > wj
		}
		return ts[i].Name < ts[j].Name
	})
}
