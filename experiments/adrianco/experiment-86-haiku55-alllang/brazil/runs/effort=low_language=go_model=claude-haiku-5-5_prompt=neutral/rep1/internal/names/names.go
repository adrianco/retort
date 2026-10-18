// Package names normalizes Brazilian club names so the same club can be matched
// across datasets that label it differently ("Palmeiras-SP", "Palmeiras",
// "Sociedade Esportiva Palmeiras", "Nacional (URU)").
package names

import (
	"regexp"
	"strings"
)

// Team is a parsed club name.
type Team struct {
	Display string // cleaned name for output, e.g. "Palmeiras"
	Base    string // accent-free lowercase key, e.g. "palmeiras"
	State   string // state (SP) or country (URU) code; empty when absent
}

// Matches reports whether two names refer to the same club. A missing state on
// either side matches any state.
func (t Team) Matches(o Team) bool {
	return t.Base == o.Base && (t.State == "" || o.State == "" || t.State == o.State)
}

var (
	stateSuffix   = regexp.MustCompile(`(\s*-\s*|\s+)([A-Z]{2,3})\s*$`)
	countryParen  = regexp.MustCompile(`\s*\(([A-Z]{2,3})\)\s*$`)
	parenthetical = regexp.MustCompile(`\([^)]*\)`)
	spaces        = regexp.MustCompile(`\s+`)
	accents       = strings.NewReplacer(
		"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
		"é", "e", "è", "e", "ê", "e", "ë", "e",
		"í", "i", "ì", "i", "î", "i", "ï", "i",
		"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
		"ú", "u", "ù", "u", "û", "u", "ü", "u",
		"ç", "c", "ñ", "n",
	)
)

// aliases maps long official names (already folded) to the short base name.
var aliases = map[string]string{
	"sport club corinthians paulista":  "corinthians",
	"sociedade esportiva palmeiras":    "palmeiras",
	"clube de regatas do flamengo":     "flamengo",
	"sao paulo futebol clube":          "sao paulo",
	"gremio foot-ball porto alegrense": "gremio",
	"esporte clube vitoria":            "vitoria",
	"atletico paranaense":              "athletico",
	"athletico paranaense":             "athletico",
	"atletico mineiro":                 "atletico",
	"vasco da gama":                    "vasco",
}

// noiseWords are club-type abbreviations ("EC Bahia", "Fortaleza FC") that do not
// distinguish one club from another. They are dropped from the ends of a name.
var noiseWords = map[string]bool{
	"fc": true, "ec": true, "sc": true, "cr": true, "ca": true,
	"ac": true, "se": true, "aa": true,
}

// stateAliases disambiguates clubs whose base name collides with another club
// in the same state-qualified form. Keys are "base-state" (folded, lowercase).
var stateAliases = map[string]string{
	"atletico-pr": "athletico",
}

// Fold lowercases, strips accents and collapses whitespace. It is used for
// case- and accent-insensitive comparison of free text.
func Fold(s string) string {
	return spaces.ReplaceAllString(strings.TrimSpace(accents.Replace(strings.ToLower(s))), " ")
}

// stripNoise removes leading and trailing noise words, keeping at least one word.
func stripNoise(s string) string {
	fields := strings.Fields(s)
	for len(fields) > 1 && noiseWords[fields[0]] {
		fields = fields[1:]
	}
	for len(fields) > 1 && noiseWords[fields[len(fields)-1]] {
		fields = fields[:len(fields)-1]
	}
	return strings.Join(fields, " ")
}

// Parse splits a raw club name into its display name, base key and state.
func Parse(raw string) Team {
	s := strings.TrimSpace(raw)
	var state string
	if m := countryParen.FindStringSubmatch(s); m != nil {
		state = m[1]
		s = countryParen.ReplaceAllString(s, "")
	} else if m := stateSuffix.FindStringSubmatch(s); m != nil && (strings.Contains(m[1], "-") || !noiseWords[strings.ToLower(m[2])]) {
		// Hyphenated "-SC" is a state; a space-separated "FC" is a club-type noise word.
		state = m[2]
		s = stateSuffix.ReplaceAllString(s, "")
	}
	s = spaces.ReplaceAllString(strings.TrimSpace(parenthetical.ReplaceAllString(s, "")), " ")

	base := stripNoise(Fold(s))
	if alias, ok := aliases[base]; ok {
		base = alias
	}
	if state != "" {
		if alias, ok := stateAliases[base+"-"+strings.ToLower(state)]; ok {
			base = alias
		}
	}
	return Team{Display: s, Base: base, State: state}
}
