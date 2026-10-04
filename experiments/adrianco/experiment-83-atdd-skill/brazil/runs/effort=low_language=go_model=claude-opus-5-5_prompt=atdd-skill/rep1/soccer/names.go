package soccer

import (
	"regexp"
	"strings"
)

var foldReplacer = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "é", "e", "ê", "e", "è", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i", "ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u", "ç", "c", "ñ", "n",
	"Á", "a", "À", "a", "Â", "a", "Ã", "a", "É", "e", "Ê", "e", "Í", "i", "Ó", "o", "Ô", "o", "Õ", "o", "Ú", "u", "Ç", "c",
)

// Fold lower-cases and strips accents so "Grêmio" and "gremio" compare equal.
func Fold(s string) string {
	return strings.TrimSpace(strings.ToLower(foldReplacer.Replace(s)))
}

var states = map[string]bool{}

func init() {
	for _, s := range strings.Fields("ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to") {
		states[s] = true
	}
}

var (
	parens = regexp.MustCompile(`\([^)]*\)`)
	// foreign clubs are tagged with a country code: "Guaraní (PAR)", "Barcelona-EQU"
	countryTag = regexp.MustCompile(`\s*(?:\(([A-Z]{3})\)|-([A-Z]{3}))$`)
	nonWord    = regexp.MustCompile(`[^a-z0-9]+`)
	// teams whose name alone is ambiguous without the state
	ambiguous = map[string]string{"atletico": "", "athletico": "", "america": "", "botafogo": "rj", "nacional": "", "guarani": "sp"}
	aliases   = map[string]string{
		"athletico paranaense": "athletico-pr", "atletico paranaense": "athletico-pr", "atletico-pr": "athletico-pr", "athletico-pr": "athletico-pr",
		"atletico mineiro": "atletico-mg", "atletico goianiense": "atletico-go",
		"vasco da gama": "vasco", "sport recife": "sport", "sport club do recife": "sport",
		"red bull bragantino": "bragantino", "ec bahia": "bahia", "ec juventude": "juventude",
		"fortaleza fc": "fortaleza", "santa cruz fc": "santa cruz", "ceara sporting club": "ceara",
		"sc corinthians paulista": "corinthians", "sport club corinthians paulista": "corinthians",
		"se palmeiras": "palmeiras", "cr flamengo": "flamengo", "clube de regatas do flamengo": "flamengo",
		"sao paulo fc": "sao paulo", "santos fc": "santos", "gremio fbpa": "gremio", "csa": "csa",
		"botafogo-rj": "botafogo", "fla": "flamengo", "flu": "fluminense",
	}
)

// TeamKey normalises any of the dataset spellings of a club to one identity.
func TeamKey(raw string) string {
	if m := countryTag.FindStringSubmatch(strings.TrimSpace(raw)); m != nil {
		country := m[1] + m[2]
		base := countryTag.ReplaceAllString(strings.TrimSpace(raw), "")
		return strings.Join(strings.Fields(nonWord.ReplaceAllString(Fold(base), " ")), " ") + "-" + strings.ToLower(country)
	}
	s := Fold(parens.ReplaceAllString(raw, " "))
	toks := strings.Fields(nonWord.ReplaceAllString(s, " "))
	state := ""
	if len(toks) > 1 && states[toks[len(toks)-1]] {
		state = toks[len(toks)-1]
		toks = toks[:len(toks)-1]
	}
	base := strings.Join(toks, " ")
	if a, ok := aliases[base]; ok {
		base = a
	}
	if def, ok := ambiguous[base]; ok {
		if state == "" {
			state = def
		}
		if state != "" && state != def {
			base = base + "-" + state
		}
		if a, ok := aliases[base]; ok {
			base = a
		}
	}
	return base
}

func hasAccent(s string) bool {
	for _, r := range s {
		if r > 127 {
			return true
		}
	}
	return false
}

var stateSuffix = regexp.MustCompile(`\s*-\s*[A-Z]{2}$`)

// displayName strips the state suffix unless it's needed to disambiguate.
func displayName(raw, key string) string {
	if strings.Contains(key, "-") {
		return raw
	}
	return strings.TrimSpace(stateSuffix.ReplaceAllString(raw, ""))
}
