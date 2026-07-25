// normalize.go - team/player name normalization.
//
// Context
//
//	The five match datasets spell the same club in wildly different ways:
//
//	    Brasileirao_Matches.csv       "Palmeiras-SP"   "Atletico-MG"   "Sao Paulo-SP"
//	    Brazilian_Cup_Matches.csv     "Palmeiras - SP" "Atlético - MG" "São Paulo - SP"
//	    novo_campeonato_brasileiro    "Palmeiras"      "Atlético-MG"   "São Paulo"
//	    BR-Football-Dataset.csv       "Palmeiras"      "Atletico Mineiro" "Sao Paulo"
//	    Libertadores_Matches.csv      "Palmeiras"      "Atlético-MG"   "São Paulo"
//
//	plus parenthetical country markers ("Nacional (URU)"), abbreviation dots
//	("C.r.b. - AL"), corporate suffixes ("Vitoria F. C. - ES") and legacy names
//	("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ").
//
//	ParseTeamName reduces any of these to a (base, region) pair:
//	accent-folded, lower-cased, punctuation-free base plus the two letter
//	Brazilian state or three letter country code when one is present. Region is
//	kept separate rather than discarded because several distinct clubs share a
//	base name - Flamengo-RJ vs Flamengo-PI, Atlético-MG vs Athletico-PR - and
//	collapsing them would silently corrupt every statistic.
//
//	The remaining irreducible variations (Vasco vs Vasco da Gama, Athletico vs
//	Atlético Paranaense) are handled by the curated alias table in clubs.go.
package soccer

import (
	"regexp"
	"strings"
	"unicode"

	"golang.org/x/text/runes"
	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"
)

// brazilStates maps the 27 federative unit codes to their names. A trailing
// token matching one of these is treated as a state marker, not part of the
// club name.
var brazilStates = map[string]string{
	"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
	"BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
	"GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
	"MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
	"PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
	"RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
	"SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}

// foreignRegions covers the CONMEBOL country markers used by the Libertadores
// dataset.
var foreignRegions = map[string]string{
	"ARG": "Argentina", "URU": "Uruguay", "PAR": "Paraguay", "CHI": "Chile",
	"COL": "Colombia", "VEN": "Venezuela", "PER": "Peru", "BOL": "Bolivia",
	"EQU": "Ecuador", "ECU": "Ecuador", "MEX": "Mexico", "BRA": "Brazil",
}

// stateByFullName lets "(Minas Gerais)" in the FIFA club column resolve to MG.
var stateByFullName = func() map[string]string {
	m := make(map[string]string, len(brazilStates))
	for code, name := range brazilStates {
		m[normalizeText(name)] = code
	}
	return m
}()

// clubTypeTokens are legal-entity words that carry no identifying information.
// They are removed wherever they appear, as long as something is left over.
var clubTypeTokens = map[string]bool{
	"fc": true, "ec": true, "sc": true, "cd": true, "ca": true, "ad": true,
	"ae": true, "ge": true, "cs": true, "cr": true, "sd": true, "se": true,
	"ce": true, "ac": true, "afc": true, "esporte": true, "esportiva": true,
	"esportivo": true, "clube": true, "club": true, "futebol": true,
	"associacao": true, "sociedade": true, "recreativo": true, "ltda": true,
}

// connectorTokens are Portuguese/Spanish articles dropped from the middle of a
// name so that "XV de Piracicaba" and "XV Piracicaba" collide.
var connectorTokens = map[string]bool{
	"de": true, "do": true, "da": true, "dos": true, "das": true, "del": true,
}

var (
	parenRe    = regexp.MustCompile(`\(([^)]*)\)`)
	trailingRe = regexp.MustCompile(`^(.*[^\s-])[\s-]+([a-z]{2,3})$`)
	nonAlnumRe = regexp.MustCompile(`[^a-z0-9]+`)
	accentFold = transform.Chain(norm.NFD, runes.Remove(runes.In(unicode.Mn)), norm.NFC)
)

// NameParts is the result of decomposing a raw team spelling.
type NameParts struct {
	Raw    string // the original spelling, trimmed
	Base   string // canonical, accent-free, space-separated base name
	Region string // "SP", "RJ", "URU", ... or "" when not stated
}

// Key returns the lookup key used by the alias table and club registry.
func (n NameParts) Key() string {
	if n.Region == "" {
		return n.Base
	}
	return n.Base + "|" + n.Region
}

// normalizeText folds accents, lower-cases and squashes punctuation to single
// spaces. It is the shared first stage for team names, player names and free
// text queries.
func normalizeText(s string) string {
	folded, _, err := transform.String(accentFold, s)
	if err != nil {
		folded = s
	}
	folded = strings.ToLower(folded)
	folded = nonAlnumRe.ReplaceAllString(folded, " ")
	return strings.Join(strings.Fields(folded), " ")
}

// regionCode recognises a state or country marker, returning the upper-cased
// code and whether it matched.
func regionCode(token string) (string, bool) {
	t := strings.ToUpper(strings.TrimSpace(token))
	if _, ok := brazilStates[t]; ok {
		return t, true
	}
	if _, ok := foreignRegions[t]; ok {
		return t, true
	}
	if code, ok := stateByFullName[normalizeText(token)]; ok {
		return code, true
	}
	return "", false
}

// RegionName expands a region code into a human readable place name.
func RegionName(code string) string {
	if n, ok := brazilStates[code]; ok {
		return n
	}
	if n, ok := foreignRegions[code]; ok {
		return n
	}
	return code
}

// IsBrazilianState reports whether the code is one of the 27 federative units.
func IsBrazilianState(code string) bool {
	_, ok := brazilStates[code]
	return ok
}

// ParseTeamName decomposes a raw team spelling into a base name and an
// optional region marker.
func ParseTeamName(raw string) NameParts {
	out := NameParts{Raw: strings.TrimSpace(raw)}

	folded, _, err := transform.String(accentFold, out.Raw)
	if err != nil {
		folded = out.Raw
	}
	s := strings.ToLower(folded)

	// Parenthesised content is either a region marker - "Nacional (URU)",
	// "América FC (Minas Gerais)" - or an editorial aside such as
	// "(antigo Esporte Clube Barreira)". Keep the former, drop the latter.
	for _, m := range parenRe.FindAllStringSubmatch(s, -1) {
		if code, ok := regionCode(m[1]); ok && out.Region == "" {
			out.Region = code
		}
	}
	s = parenRe.ReplaceAllString(s, " ")
	s = strings.Join(strings.Fields(s), " ")

	// A trailing "-SP", " - SP" or " SP" is a state marker.
	if m := trailingRe.FindStringSubmatch(s); m != nil {
		if code, ok := regionCode(m[2]); ok {
			if out.Region == "" {
				out.Region = code
			}
			s = m[1]
		}
	}

	tokens := strings.Fields(nonAlnumRe.ReplaceAllString(s, " "))
	tokens = joinInitialisms(tokens)

	kept := make([]string, 0, len(tokens))
	for _, t := range tokens {
		if clubTypeTokens[t] || connectorTokens[t] {
			continue
		}
		kept = append(kept, t)
	}
	// Never normalize a name out of existence: "CRB", "Sport" and "Internacional"
	// are entirely made of tokens we would otherwise strip.
	if len(kept) == 0 {
		kept = tokens
	}
	out.Base = strings.Join(kept, " ")
	if out.Base == "" {
		out.Base = normalizeText(out.Raw)
	}
	return out
}

// joinInitialisms collapses runs of two or more single-letter tokens, so that
// "A.b.c. - RN" and "C. R. B." become "abc" and "crb" rather than "a b c".
func joinInitialisms(tokens []string) []string {
	out := make([]string, 0, len(tokens))
	for i := 0; i < len(tokens); {
		j := i
		for j < len(tokens) && len(tokens[j]) == 1 {
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

// displayTrailingRe matches a trailing state/country marker in an unfolded
// display name. State and country codes are pure ASCII, so this deliberately
// works on the original string: slicing a folded copy back onto the original
// would be wrong wherever folding changes the rune count.
var displayTrailingRe = regexp.MustCompile(`(?i)^(.*[^\s-])[\s-]+([a-z]{2,3})$`)

// stripRegionSuffix removes a trailing state marker from a display name while
// preserving its original accents and capitalisation, turning "Palmeiras - SP"
// into "Palmeiras".
func stripRegionSuffix(raw string) string {
	s := strings.TrimSpace(raw)
	if m := displayTrailingRe.FindStringSubmatch(s); m != nil {
		if _, ok := regionCode(m[2]); ok {
			return strings.TrimRight(m[1], " -")
		}
	}
	return s
}

// hasAccent reports whether the string contains non-ASCII characters, used to
// prefer "São Paulo" over "Sao Paulo" as a display name.
func hasAccent(s string) bool {
	for _, r := range s {
		if r > unicode.MaxASCII {
			return true
		}
	}
	return false
}

// containsNormalized reports whether needle occurs in haystack once both have
// been accent-folded and lower-cased. Used for fuzzy player/club search.
func containsNormalized(haystack, needle string) bool {
	if needle == "" {
		return true
	}
	return strings.Contains(normalizeText(haystack), normalizeText(needle))
}
