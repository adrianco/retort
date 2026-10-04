// Text, team-name, competition and date normalization.
//
// The datasets spell the same club in many ways ("Palmeiras-SP",
// "Palmeiras - SP", "Palmeiras", "Sociedade Esportiva Palmeiras",
// "Atletico-PR", "Athletico Paranaense", "Athletico"...). Every raw name is
// parsed into a folded base name plus an optional region (Brazilian state or,
// for foreign Libertadores clubs, a country code). The teamRegistry in data.go
// then turns that into a stable canonical key such as "palmeiras-sp".
package main

import (
	"fmt"
	"regexp"
	"strings"
	"time"
)

// foldMap strips diacritics from lower-case runes.
var foldMap = map[rune]string{
	'á': "a", 'à': "a", 'â': "a", 'ã': "a", 'ä': "a", 'å': "a", 'ā': "a", 'ă': "a", 'ą': "a",
	'é': "e", 'è': "e", 'ê': "e", 'ë': "e", 'ē': "e", 'ė': "e", 'ę': "e", 'ě': "e",
	'í': "i", 'ì': "i", 'î': "i", 'ï': "i", 'ī': "i", 'ı': "i", 'į': "i",
	'ó': "o", 'ò': "o", 'ô': "o", 'õ': "o", 'ö': "o", 'ø': "o", 'ō': "o", 'ő': "o",
	'ú': "u", 'ù': "u", 'û': "u", 'ü': "u", 'ū': "u", 'ů': "u", 'ű': "u", 'ų': "u",
	'ç': "c", 'ć': "c", 'č': "c", 'ñ': "n", 'ń': "n", 'ň': "n", 'ý': "y", 'ÿ': "y",
	'š': "s", 'ś': "s", 'ş': "s", 'ș': "s", 'ž': "z", 'ź': "z", 'ż': "z", 'ř': "r",
	'ğ': "g", 'ł': "l", 'đ': "d", 'ď': "d", 'ť': "t", 'ț': "t", 'ß': "ss", 'æ': "ae", 'œ': "oe",
}

// foldText lower-cases s and removes accents so that "São Paulo" and
// "sao paulo" compare equal.
func foldText(s string) string {
	var b strings.Builder
	for _, r := range strings.ToLower(s) {
		if rep, ok := foldMap[r]; ok {
			b.WriteString(rep)
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

// hasNonASCII reports whether s contains accented characters.
func hasNonASCII(s string) bool {
	for _, r := range s {
		if r > 127 {
			return true
		}
	}
	return false
}

var brazilianStates = map[string]bool{
	"ac": true, "al": true, "ap": true, "am": true, "ba": true, "ce": true, "df": true,
	"es": true, "go": true, "ma": true, "mt": true, "ms": true, "mg": true, "pa": true,
	"pb": true, "pr": true, "pe": true, "pi": true, "rj": true, "rn": true, "rs": true,
	"ro": true, "rr": true, "sc": true, "sp": true, "se": true, "to": true,
}

// stateNames maps spelled-out state names (as found in parentheses, e.g.
// FIFA's "América FC (Minas Gerais)") to their abbreviation.
var stateNames = map[string]string{
	"minas gerais": "mg", "sao paulo": "sp", "rio de janeiro": "rj", "rio grande do sul": "rs",
	"parana": "pr", "bahia": "ba", "pernambuco": "pe", "ceara": "ce", "santa catarina": "sc", "goias": "go",
}

var countryCodes = map[string]string{
	"uru": "uru", "par": "par", "equ": "equ", "ecu": "equ", "per": "per", "ven": "ven",
	"bol": "bol", "chi": "chi", "arg": "arg", "col": "col", "mex": "mex",
}

// leadingGeneric / trailingGeneric are club-type words dropped from names
// ("EC Bahia", "Fortaleza EC", "Paulista Futebol Clube").
var leadingGeneric = map[string]bool{
	"ec": true, "fc": true, "sc": true, "se": true, "ad": true, "ae": true, "ce": true,
	"ca": true, "ge": true, "cs": true, "clube": true, "club": true, "do": true,
	"esporte": true, "associacao": true, "sociedade": true, "esportiva": true,
}

var trailingGeneric = map[string]bool{
	"fc": true, "ec": true, "sc": true, "afc": true, "clube": true, "club": true,
	"futebol": true, "esporte": true, "de": true, "football": true, "foot": true,
	"ball": true, "sporting": true,
}

// fullAliases are matched against the whole folded raw name before any
// suffix processing. Values are "base|region".
var fullAliases = map[string]string{
	"river ac":                         "river|pi",
	"central sc":                       "central|pe",
	"sport club corinthians paulista":  "corinthians|sp",
	"sociedade esportiva palmeiras":    "palmeiras|sp",
	"clube de regatas do flamengo":     "flamengo|rj",
	"cr flamengo":                      "flamengo|rj",
	"club de regatas vasco da gama":    "vasco|rj",
	"cr vasco da gama":                 "vasco|rj",
	"gremio foot-ball porto alegrense": "gremio|rs",
	"sport club internacional":         "internacional|rs",
	"sc internacional":                 "internacional|rs",
	"botafogo de futebol e regatas":    "botafogo|rj",
	"clube de regatas brasil":          "crb|al",
	"centro sportivo alagoano":         "csa|al",
	"sport club do recife":             "sport|pe",
	"esporte clube vitoria":            "vitoria|ba",
	"santos fc":                        "santos|sp",
	"spfc":                             "sao paulo|sp",
	"fla":                              "flamengo|rj",
	"flu":                              "fluminense|rj",
	"timao":                            "corinthians|sp",
	"verdao":                           "palmeiras|sp",
	"galo":                             "atletico|mg",
	"furacao":                          "atletico|pr",
	"peixe":                            "santos|sp",
}

// baseAliases are applied after suffix stripping. Values are "base|region"
// (region may be empty, meaning "use the usual default").
var baseAliases = map[string]string{
	"athletico":                      "atletico|pr",
	"athletico paranaense":           "atletico|pr",
	"atletico paranaense":            "atletico|pr",
	"club athletico paranaense":      "atletico|pr",
	"atletico mineiro":               "atletico|mg",
	"atletico goianiense":            "atletico|go",
	"atletico acreano":               "atletico|ac",
	"atletico alagoinhas":            "atletico|ba",
	"vasco da gama":                  "vasco|rj",
	"red bull bragantino":            "bragantino|",
	"rb bragantino":                  "bragantino|",
	"sport recife":                   "sport|pe",
	"sport club do recife":           "sport|pe",
	"nautico capibaribe":             "nautico|pe",
	"portuguesa desportos":           "portuguesa|sp",
	"america fc natal":               "america|rn",
	"america de natal":               "america|rn",
	"america mineiro":                "america|mg",
	"gremio novorizontino":           "novorizontino|sp",
	"moto club de sao luis":          "moto|ma",
	"retro fc brasil":                "retro|pe",
	"cs alagoano":                    "csa|al",
	"souza":                          "sousa|pb",
	"desportiva ferroviaria":         "desportiva|es",
	"operario ferroviario esporte c": "operario|pr",
	"operario ferroviario":           "operario|pr",
	"boavista sport":                 "boavista|rj",
	"boavista sc saquarema":          "boavista|rj",
	"sao jose poa":                   "sao jose|rs",
	"independente de tucurui":        "independente|pa",
	"guarany de sobral":              "guarany|ce",
	"flamengo do piaui":              "flamengo|pi",
	"uniao de rondonopolis":          "uniao|mt",
	"uniao rondonopolis":             "uniao|mt",
	"real noroeste capixaba":         "real noroeste|es",
	"iv de julho":                    "4 de julho|pi",
	"xv piracicaba":                  "xv de piracicaba|sp",
	"brasil de pelotas":              "brasil|rs",
	"ser caxias":                     "caxias|rs",
	"esportivo bento goncalves":      "esportivo|rs",
	"anapolis":                       "anapolis|go",
	"chapecoense":                    "chapecoense|sc",
	"libertad":                       "libertad|par",
	"delfin":                         "delfin|equ",
	"tolima":                         "deportes tolima|",
	"sao paulo futebol":              "sao paulo|sp",
	"santos futebol":                 "santos|sp",
}

// parsedName is the result of parsing a raw team name.
type parsedName struct {
	Base    string // folded base name, e.g. "sao paulo"
	Region  string // lower-case state ("sp") or country ("uru"), may be empty
	Country bool   // Region is a country code
}

var parenRe = regexp.MustCompile(`\(([^)]*)\)`)

func splitAlias(v string) parsedName {
	parts := strings.SplitN(v, "|", 2)
	p := parsedName{Base: parts[0]}
	if len(parts) == 2 {
		p.Region = parts[1]
		p.Country = len(p.Region) == 3
	}
	return p
}

// collapseInitials merges runs of single-letter tokens: "c r b" -> "crb",
// produced from dotted acronyms such as "C.R.B." or "A.b.c.".
func collapseInitials(tokens []string) []string {
	var out []string
	for i := 0; i < len(tokens); {
		j := i
		for j < len(tokens) && len([]rune(tokens[j])) == 1 {
			j++
		}
		if j-i >= 2 {
			out = append(out, strings.Join(tokens[i:j], ""))
			i = j
			continue
		}
		out = append(out, tokens[i])
		i++
	}
	return out
}

// parseTeamName breaks a raw team name into base name and region.
func parseTeamName(raw string) parsedName {
	s := strings.TrimSpace(foldText(raw))
	if v, ok := fullAliases[s]; ok {
		return splitAlias(v)
	}
	var p parsedName
	// Parenthesised parts: country codes, state names or notes like
	// "(antigo Esporte Clube Barreira)".
	for _, m := range parenRe.FindAllStringSubmatch(s, -1) {
		inner := strings.TrimSpace(m[1])
		if cc, ok := countryCodes[inner]; ok {
			p.Region, p.Country = cc, true
		} else if uf, ok := stateNames[inner]; ok {
			p.Region = uf
		}
	}
	s = parenRe.ReplaceAllString(s, " ")
	s = strings.NewReplacer(".", " ", "-", " ", "'", "", "’", "", ",", " ", "/", " ").Replace(s)
	tokens := collapseInitials(strings.Fields(s))
	if v, ok := fullAliases[strings.Join(tokens, " ")]; ok {
		return splitAlias(v)
	}
	if p.Region == "" && len(tokens) > 1 {
		last := tokens[len(tokens)-1]
		if brazilianStates[last] {
			p.Region = last
			tokens = tokens[:len(tokens)-1]
		} else if cc, ok := countryCodes[last]; ok {
			p.Region, p.Country = cc, true
			tokens = tokens[:len(tokens)-1]
		}
	}
	if v, ok := baseAliases[strings.Join(tokens, " ")]; ok {
		return mergeAlias(splitAlias(v), p)
	}
	for len(tokens) > 1 && leadingGeneric[tokens[0]] {
		tokens = tokens[1:]
	}
	for len(tokens) > 1 && trailingGeneric[tokens[len(tokens)-1]] {
		tokens = tokens[:len(tokens)-1]
	}
	p.Base = strings.Join(tokens, " ")
	if v, ok := baseAliases[p.Base]; ok {
		return mergeAlias(splitAlias(v), p)
	}
	return p
}

// mergeAlias applies an alias, keeping an explicitly parsed region when the
// alias does not force one.
func mergeAlias(alias, parsed parsedName) parsedName {
	if alias.Region == "" {
		alias.Region, alias.Country = parsed.Region, parsed.Country
	}
	return alias
}

// teamKey renders a canonical key from a base and region.
func teamKey(base, region string) string {
	if region == "" {
		return base
	}
	return base + "-" + region
}

var displaySuffixRe = regexp.MustCompile(`(?i)\s*(?:-|\s)\s*\(?([a-z]{2,3})\)?\s*$`)

// displayBase strips state/country suffixes and parenthetical notes from a
// raw name while keeping original casing and accents: "Grêmio - RS" -> "Grêmio".
func displayBase(raw string) string {
	s := strings.TrimSpace(raw)
	if m := displaySuffixRe.FindStringSubmatch(s); m != nil {
		code := strings.ToLower(m[1])
		if brazilianStates[code] || countryCodes[code] != "" {
			s = strings.TrimSpace(s[:len(s)-len(m[0])])
		}
	}
	s = strings.TrimSpace(parenRe.ReplaceAllString(s, ""))
	return strings.Join(strings.Fields(s), " ")
}

// Competition names used throughout the server.
const (
	CompSerieA       = "Brasileirão Série A"
	CompSerieB       = "Brasileirão Série B"
	CompSerieC       = "Brasileirão Série C"
	CompCopaBrasil   = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

var allCompetitions = []string{CompSerieA, CompSerieB, CompSerieC, CompCopaBrasil, CompLibertadores}

func isLeague(comp string) bool {
	return comp == CompSerieA || comp == CompSerieB || comp == CompSerieC
}

// normalizeCompetition maps user or dataset spellings to a canonical
// competition name. Empty input (or "all") returns "" meaning no filter.
func normalizeCompetition(s string) (string, error) {
	f := strings.TrimSpace(foldText(s))
	f = strings.NewReplacer("_", " ", "-", " ").Replace(f)
	f = strings.Join(strings.Fields(f), " ")
	switch {
	case f == "" || f == "all" || f == "any":
		return "", nil
	case strings.Contains(f, "libertadores"):
		return CompLibertadores, nil
	case strings.Contains(f, "copa do brasil") || strings.Contains(f, "brazilian cup") ||
		f == "cup" || f == "copa" || f == "cdb":
		return CompCopaBrasil, nil
	case strings.Contains(f, "serie b") || f == "b" || f == "brasileirao b":
		return CompSerieB, nil
	case strings.Contains(f, "serie c") || f == "c" || f == "brasileirao c":
		return CompSerieC, nil
	case strings.Contains(f, "serie a") || strings.Contains(f, "brasileirao") ||
		strings.Contains(f, "brasileiro") || f == "a" || f == "league":
		return CompSerieA, nil
	}
	return "", fmt.Errorf("unknown competition %q (use Brasileirão/Serie A, Serie B, Serie C, Copa do Brasil or Libertadores)", s)
}

// parseDate accepts the formats found in the datasets (and user input).
func parseDate(s string) (t time.Time, hasTime bool, err error) {
	s = strings.TrimSpace(s)
	for _, layout := range []string{"2006-01-02 15:04:05", "2006-01-02T15:04:05", "2006-01-02 15:04"} {
		if t, err = time.Parse(layout, s); err == nil {
			return t, true, nil
		}
	}
	for _, layout := range []string{"2006-01-02", "02/01/2006", "2/1/2006", "2006/01/02"} {
		if t, err = time.Parse(layout, s); err == nil {
			return t, false, nil
		}
	}
	return time.Time{}, false, fmt.Errorf("unrecognized date %q (use YYYY-MM-DD or DD/MM/YYYY)", s)
}
