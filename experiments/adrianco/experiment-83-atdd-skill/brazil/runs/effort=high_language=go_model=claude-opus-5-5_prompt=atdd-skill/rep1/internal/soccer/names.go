package soccer

import (
	"regexp"
	"strings"
	"unicode"
)

// The datasets write team names in many ways: "Palmeiras-SP",
// "Palmeiras - SP", "Palmeiras", "Sociedade Esportiva Palmeiras",
// "Athletico Paranaense", "Atletico-PR", "Sao Paulo", "São Paulo"...
// Every name is reduced to a team key so that all of them refer to the
// same team, while keeping apart clubs that share a name but not a
// state (Botafogo-RJ and Botafogo-PB).

var accentFolder = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "å", "a",
	"é", "e", "ê", "e", "è", "e", "ë", "e",
	"í", "i", "î", "i", "ì", "i", "ï", "i",
	"ó", "o", "ô", "o", "õ", "o", "ò", "o", "ö", "o", "ø", "o",
	"ú", "u", "û", "u", "ù", "u", "ü", "u",
	"ç", "c", "ñ", "n", "ý", "y", "ÿ", "y", "ß", "ss",
)

// Fold lower-cases a string and removes accents, so that "Grêmio" and
// "gremio" compare equal.
func Fold(s string) string {
	return accentFolder.Replace(strings.ToLower(strings.TrimSpace(s)))
}

var brazilianStates = set("ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg",
	"pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to")

var stateNames = map[string]string{
	"acre": "ac", "alagoas": "al", "amapa": "ap", "amazonas": "am", "bahia": "ba", "ceara": "ce",
	"distrito federal": "df", "espirito santo": "es", "goias": "go", "maranhao": "ma", "mato grosso": "mt",
	"mato grosso do sul": "ms", "minas gerais": "mg", "para": "pa", "paraiba": "pb", "parana": "pr",
	"pernambuco": "pe", "piaui": "pi", "rio de janeiro": "rj", "rio grande do norte": "rn",
	"rio grande do sul": "rs", "rondonia": "ro", "roraima": "rr", "santa catarina": "sc",
	"sao paulo": "sp", "sergipe": "se", "tocantins": "to",
}

var countryCodes = set("arg", "bol", "chi", "col", "ecu", "equ", "par", "per", "uru", "ven", "mex")

// Names shared by several clubs that are told apart only by their state.
var sharedNames = set("atletico", "america", "botafogo", "bragantino", "internacional", "operario",
	"nacional", "independente", "santos", "flamengo", "guarani", "sport", "juventude", "palmeiras", "vitoria")

type knownTeam struct {
	key, display, state string
	aliases             []string
}

// The major clubs, with the names the datasets and users call them by.
var knownTeams = []knownTeam{
	{"flamengo", "Flamengo", "rj", []string{"cr flamengo", "clube de regatas do flamengo"}},
	{"fluminense", "Fluminense", "rj", []string{"fluminense fc"}},
	{"vasco", "Vasco", "rj", []string{"vasco da gama", "cr vasco da gama", "club de regatas vasco da gama"}},
	{"botafogo-rj", "Botafogo", "rj", []string{"botafogo", "botafogo de futebol e regatas"}},
	{"corinthians", "Corinthians", "sp", []string{"sport club corinthians paulista", "sc corinthians paulista", "sc corinthians"}},
	{"palmeiras", "Palmeiras", "sp", []string{"palmeiras", "sociedade esportiva palmeiras", "se palmeiras"}},
	{"sao paulo", "São Paulo", "sp", []string{"sao paulo fc", "spfc"}},
	{"santos", "Santos", "sp", []string{"santos", "santos fc"}},
	{"gremio", "Grêmio", "rs", []string{"gremio fbpa", "gremio foot-ball porto alegrense"}},
	{"internacional", "Internacional", "rs", []string{"internacional", "sc internacional", "sport club internacional"}},
	{"atletico-mg", "Atlético-MG", "mg", []string{"atletico-mg", "atletico mineiro", "clube atletico mineiro"}},
	{"cruzeiro", "Cruzeiro", "mg", []string{"cruzeiro ec", "cruzeiro esporte clube"}},
	{"athletico-pr", "Athletico-PR", "pr", []string{"athletico", "athletico-pr", "atletico-pr", "athletico paranaense", "atletico paranaense", "club athletico paranaense", "ca paranaense"}},
	{"coritiba", "Coritiba", "pr", []string{"coritiba fc"}},
	{"parana", "Paraná", "pr", []string{"parana clube"}},
	{"bahia", "Bahia", "ba", []string{"ec bahia", "esporte clube bahia"}},
	{"vitoria", "Vitória", "ba", []string{"ec vitoria", "esporte clube vitoria"}},
	{"sport", "Sport", "pe", []string{"sport", "sport recife", "sport club do recife"}},
	{"nautico", "Náutico", "pe", []string{"nautico capibaribe", "clube nautico capibaribe"}},
	{"santa cruz", "Santa Cruz", "pe", []string{"santa cruz fc"}},
	{"ceara", "Ceará", "ce", []string{"ceara sc", "ceara sporting club"}},
	{"fortaleza", "Fortaleza", "ce", []string{"fortaleza ec", "fortaleza esporte clube"}},
	{"goias", "Goiás", "go", []string{"goias ec", "goias esporte clube"}},
	{"atletico-go", "Atlético-GO", "go", []string{"atletico-go", "atletico goianiense"}},
	{"america-mg", "América-MG", "mg", []string{"america", "america-mg", "america mineiro", "america fc-mg"}},
	{"bragantino", "Bragantino", "sp", []string{"bragantino", "red bull bragantino", "rb bragantino"}},
	{"chapecoense", "Chapecoense", "sc", []string{"associacao chapecoense de futebol"}},
	{"avai", "Avaí", "sc", []string{"avai fc"}},
	{"figueirense", "Figueirense", "sc", []string{"figueirense fc"}},
	{"criciuma", "Criciúma", "sc", []string{"criciuma ec"}},
	{"joinville", "Joinville", "sc", nil},
	{"cuiaba", "Cuiabá", "mt", []string{"cuiaba ec"}},
	{"juventude", "Juventude", "rs", []string{"juventude", "ec juventude"}},
	{"csa", "CSA", "al", []string{"cs alagoano"}},
	{"remo", "Remo", "pa", []string{"clube do remo"}},
	{"paysandu", "Paysandu", "pa", nil},
	{"guarani", "Guarani", "sp", []string{"guarani", "guarani fc"}},
	{"ponte preta", "Ponte Preta", "sp", []string{"aa ponte preta"}},
	{"portuguesa", "Portuguesa", "sp", []string{"portuguesa desportos", "associacao portuguesa de desportos"}},
}

var (
	knownByAlias = map[string]*knownTeam{}
	knownByKey   = map[string]*knownTeam{}
)

func init() {
	for i := range knownTeams {
		k := &knownTeams[i]
		knownByKey[k.key] = k
		knownByAlias[k.key] = k
		for _, a := range k.aliases {
			knownByAlias[a] = k
		}
	}
}

var (
	parenthetical  = regexp.MustCompile(`\s*\(([^)]*)\)`)
	apostrophes    = regexp.MustCompile(`['’]`)
	punctuation    = regexp.MustCompile(`[.,]`)
	trailingCode   = regexp.MustCompile(`^(.*?)(?:\s*-\s*|\s+)([a-z]{2,3})$`)
	rawStateSuffix = regexp.MustCompile(`(?:\s*-\s*|\s+)[A-Z]{2}$`)
	clubWords      = []string{"fc", "ec", "sc", "esporte clube", "futebol clube", "sport club", "clube"}
	clubPrefixes   = []string{"aa", "ad", "ae", "ca", "ce", "cr", "cs", "ge", "se"}
	connectors     = map[string]bool{"de": true, "do": true, "da": true}
)

// TeamName is a team name reduced to its key, together with the name to
// show for it.
type TeamName struct {
	Key     string
	Display string
	Known   bool // one of the major clubs
}

// NormalizeTeam reduces any spelling of a team name to its key.
func NormalizeTeam(raw string) TeamName {
	s := Fold(raw)
	state, country := "", ""
	s = parenthetical.ReplaceAllStringFunc(s, func(p string) string {
		inner := strings.TrimSpace(parenthetical.FindStringSubmatch(p)[1])
		switch {
		case countryCodes[inner]:
			country = inner
		case stateNames[inner] != "":
			state = stateNames[inner]
		case brazilianStates[inner]:
			state = inner
		}
		return ""
	})
	s = joinInitials(punctuation.ReplaceAllString(apostrophes.ReplaceAllString(s, ""), " "))
	if m := trailingCode.FindStringSubmatch(s); m != nil && m[1] != "" {
		switch {
		case brazilianStates[m[2]]:
			s, state = m[1], m[2]
		case countryCodes[m[2]]:
			s, country = m[1], m[2]
		}
	}
	if country != "" {
		key := s + "-" + country
		return TeamName{Key: key, Display: displayFromRaw(raw)}
	}

	if k := lookupKnown(s, state); k != nil {
		return TeamName{Key: k.key, Display: k.display, Known: true}
	}
	base := stripClubWords(s)
	if k := lookupKnown(base, state); k != nil {
		return TeamName{Key: k.key, Display: k.display, Known: true}
	}
	if sharedNames[base] && state != "" {
		return TeamName{Key: base + "-" + state, Display: titleCase(displayFromRaw(raw)) + "-" + strings.ToUpper(state)}
	}
	return TeamName{Key: withoutConnectors(base), Display: displayFromRaw(raw)}
}

// joinInitials collapses spacing and rejoins initials, so that "C. R. B."
// and "CRB" read the same.
func joinInitials(s string) string {
	var out []string
	initials := ""
	for _, w := range strings.Fields(s) {
		if len(w) == 1 {
			initials += w
			continue
		}
		if initials != "" {
			out, initials = append(out, initials), ""
		}
		out = append(out, w)
	}
	if initials != "" {
		out = append(out, initials)
	}
	return strings.Join(out, " ")
}

// withoutConnectors drops "de", "do" and "da", which the datasets use
// inconsistently ("XV de Piracicaba", "XV Piracicaba").
func withoutConnectors(s string) string {
	words := strings.Fields(s)
	kept := words[:0]
	for _, w := range words {
		if !connectors[w] {
			kept = append(kept, w)
		}
	}
	if len(kept) == 0 {
		return s
	}
	return strings.Join(kept, " ")
}

func lookupKnown(name, state string) *knownTeam {
	if state != "" {
		if k, ok := knownByAlias[name+"-"+state]; ok {
			return k
		}
	}
	k, ok := knownByAlias[name]
	if !ok {
		return nil
	}
	// A club that shares its name with a major club from another state
	// is a different club.
	if state != "" && state != k.state && sharedNames[name] {
		return nil
	}
	return k
}

func stripClubWords(s string) string {
	for changed := true; changed; {
		changed = false
		for _, w := range clubWords {
			if rest, ok := strings.CutSuffix(s, " "+w); ok && rest != "" {
				s, changed = rest, true
			}
			if rest, ok := strings.CutPrefix(s, w+" "); ok && rest != "" {
				s, changed = rest, true
			}
		}
		for _, w := range clubPrefixes {
			if rest, ok := strings.CutPrefix(s, w+" "); ok && rest != "" {
				s, changed = rest, true
			}
		}
	}
	return s
}

// displayFromRaw is the source's own spelling without its state suffix.
func displayFromRaw(raw string) string {
	s := strings.TrimSpace(raw)
	if i := strings.Index(s, " (antigo"); i > 0 {
		s = s[:i]
	}
	s = rawStateSuffix.ReplaceAllString(s, "")
	return strings.TrimSpace(s)
}

func titleCase(s string) string {
	words := strings.Fields(s)
	for i, w := range words {
		r := []rune(w)
		r[0] = unicode.ToUpper(r[0])
		words[i] = string(r)
	}
	return strings.Join(words, " ")
}

func set(items ...string) map[string]bool {
	m := make(map[string]bool, len(items))
	for _, i := range items {
		m[i] = true
	}
	return m
}

// Competition is one of the competitions in the match data.
type Competition string

const (
	SerieA       Competition = "Brasileirão Série A"
	SerieB       Competition = "Brasileirão Série B"
	SerieC       Competition = "Brasileirão Série C"
	CopaDoBrasil Competition = "Copa do Brasil"
	Libertadores Competition = "Copa Libertadores"
)

// IsLeague reports whether a competition is played as a league table.
func (c Competition) IsLeague() bool { return c == SerieA || c == SerieB || c == SerieC }

// IsDomestic reports whether only Brazilian clubs take part.
func (c Competition) IsDomestic() bool { return c != Libertadores }

// ResolveCompetition understands the usual ways of naming a competition.
func ResolveCompetition(name string) (Competition, bool) {
	s := Fold(name)
	switch {
	case s == "":
		return "", false
	case strings.Contains(s, "libertadores"):
		return Libertadores, true
	case strings.Contains(s, "copa do brasil"), strings.Contains(s, "brazil cup"), strings.Contains(s, "brazilian cup"), s == "cup":
		return CopaDoBrasil, true
	case strings.Contains(s, "serie b"):
		return SerieB, true
	case strings.Contains(s, "serie c"):
		return SerieC, true
	case strings.Contains(s, "serie a"), strings.Contains(s, "brasileir"), strings.Contains(s, "league"), strings.Contains(s, "campeonato"):
		return SerieA, true
	}
	return "", false
}
