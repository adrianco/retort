// normalize.go - team name, competition name and date normalization.
//
// The six datasets spell clubs differently ("Palmeiras-SP", "Palmeiras - SP",
// "Palmeiras", "Sao Paulo", "São Paulo", "America MG", "EC Bahia"...). Every raw
// name is reduced to a (base, state) pair; the final team key is decided once all
// data is loaded, so clubs that share a name across states stay separate
// (Atlético-MG vs Atlético-GO, Santos-SP vs Santos-AP) while spellings merge.
package main

import (
	"regexp"
	"strings"
	"time"
)

var accentMap = map[rune]string{
	'á': "a", 'à': "a", 'â': "a", 'ã': "a", 'ä': "a", 'å': "a",
	'é': "e", 'è': "e", 'ê': "e", 'ë': "e",
	'í': "i", 'ì': "i", 'î': "i", 'ï': "i",
	'ó': "o", 'ò': "o", 'ô': "o", 'õ': "o", 'ö': "o", 'ø': "o",
	'ú': "u", 'ù': "u", 'û': "u", 'ü': "u",
	'ç': "c", 'ñ': "n", 'ý': "y", 'ÿ': "y", 'š': "s", 'ž': "z", 'ć': "c", 'č': "c",
	'ß': "ss", 'ł': "l", 'ğ': "g", 'ş': "s", 'ı': "i", 'đ': "d", 'æ': "ae", 'œ': "oe",
}

// fold lower-cases, strips accents and punctuation noise, and collapses spaces.
func fold(s string) string {
	var b strings.Builder
	for _, r := range strings.ToLower(s) {
		if rep, ok := accentMap[r]; ok {
			b.WriteString(rep)
			continue
		}
		switch r {
		case '.', '\'', '’', '`':
			continue
		case ' ', '\t':
			r = ' '
		}
		b.WriteRune(r)
	}
	return strings.Join(strings.Fields(b.String()), " ")
}

var brStates = map[string]bool{}

func init() {
	for _, s := range strings.Fields("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO") {
		brStates[s] = true
	}
}

var (
	reDashState  = regexp.MustCompile(`^(.*?)\s*-\s*([A-Za-z]{2})$`)
	reSpaceState = regexp.MustCompile(`^(.*\S)\s+([A-Z]{2})$`)
	reCountry    = regexp.MustCompile(`^(.*?)\s*(?:\(([A-Z]{3})\)|-([A-Z]{3}))$`)
	reParen      = regexp.MustCompile(`\s*\([^)]*\)`)
)

type alias struct{ base, state string }

// aliases maps a folded name (state suffix already removed) to its canonical base.
var aliases = map[string]alias{
	"vasco da gama":                    {"vasco", ""},
	"sport recife":                     {"sport", ""},
	"sport club do recife":             {"sport", ""},
	"red bull bragantino":              {"bragantino", ""},
	"rb bragantino":                    {"bragantino", ""},
	"atletico mineiro":                 {"atletico", "MG"},
	"galo":                             {"atletico", "MG"},
	"atletico goianiense":              {"atletico", "GO"},
	"atletico paranaense":              {"athletico", ""},
	"athletico paranaense":             {"athletico", ""},
	"america mineiro":                  {"america", "MG"},
	"america fc (minas gerais)":        {"america", "MG"},
	"america fc natal":                 {"america", "RN"},
	"america de natal":                 {"america", "RN"},
	"ceara sporting club":              {"ceara", ""},
	"cs alagoano":                      {"csa", ""},
	"c r b":                            {"crb", ""},
	"clube do remo":                    {"remo", ""},
	"nautico capibaribe":               {"nautico", ""},
	"sport club corinthians paulista":  {"corinthians", ""},
	"sao paulo futebol clube":          {"sao paulo", ""},
	"portuguesa desportos":             {"portuguesa", ""},
	"gremio novorizontino":             {"novorizontino", ""},
	"moto clube":                       {"moto club", ""},
	"tolima":                           {"deportes tolima", ""},
	"gremio foot-ball porto alegrense": {"gremio", ""},
	"clube de regatas do flamengo":     {"flamengo", ""},
	"sociedade esportiva palmeiras":    {"palmeiras", ""},
	"santos futebol clube":             {"santos", ""},
	"fluminense football club":         {"fluminense", ""},
	"cruzeiro esporte clube":           {"cruzeiro", ""},
	"fortaleza esporte clube":          {"fortaleza", ""},
	"sport club internacional":         {"internacional", ""},
	"botafogo de futebol e regatas":    {"botafogo", ""},
}

var affixTokens = map[string]bool{"ec": true, "fc": true, "sc": true, "ad": true, "ca": true, "ae": true, "se": true, "ge": true}

// defaultState says which club a bare name means when several states share it.
var defaultState = map[string]string{
	"flamengo": "RJ", "botafogo": "RJ", "fluminense": "RJ", "internacional": "RS",
	"santos": "SP", "vitoria": "BA", "santa cruz": "PE", "atletico": "MG",
	"america": "MG", "guarani": "SP", "bragantino": "SP", "juventude": "RS",
	"nautico": "PE", "operario": "PR", "boavista": "RJ", "portuguesa": "SP",
	"gremio": "RS", "sao raimundo": "AM", "rio branco": "AC", "ypiranga": "RS",
	"sao jose": "RS", "comercial": "MS", "independente": "PA", "real": "RR",
}

// displayOverride fixes display names where the state is part of the usual name.
var displayOverride = map[string]string{
	"atletico": "Atlético-MG", "atletico-go": "Atlético-GO", "america": "América-MG",
	"america-rn": "América-RN", "athletico": "Athletico-PR", "vasco": "Vasco da Gama",
}

// parseTeamName splits a raw team name into canonical base, state (UF or
// 3-letter country code, may be empty) and a display form without the suffix.
func parseTeamName(raw string) (base, state, display string) {
	s := strings.Join(strings.Fields(raw), " ")
	name := s
	if m := reDashState.FindStringSubmatch(s); m != nil && brStates[strings.ToUpper(m[2])] && m[2] != strings.ToLower(m[2]) {
		name, state = m[1], strings.ToUpper(m[2])
	} else if m := reCountry.FindStringSubmatch(s); m != nil {
		name = m[1]
		state = m[2] + m[3]
	} else if m := reSpaceState.FindStringSubmatch(s); m != nil && brStates[m[2]] {
		name, state = m[1], m[2]
	}
	display = name
	f := fold(name)
	if a, ok := aliases[f]; ok {
		base = a.base
		if a.state != "" {
			state = a.state
		}
	} else {
		if stripped := strings.TrimSpace(reParen.ReplaceAllString(name, "")); stripped != "" {
			display = stripped
			f = fold(stripped)
		}
		if a, ok := aliases[f]; ok {
			base = a.base
			if a.state != "" {
				state = a.state
			}
		} else {
			toks := strings.Fields(f)
			for len(toks) > 1 && affixTokens[toks[0]] {
				toks = toks[1:]
			}
			for len(toks) > 1 && affixTokens[toks[len(toks)-1]] {
				toks = toks[:len(toks)-1]
			}
			base = strings.Join(toks, " ")
			if a, ok := aliases[base]; ok {
				base = a.base
				if a.state != "" {
					state = a.state
				}
			}
		}
	}
	if base == "atletico" && state == "PR" {
		base, state = "athletico", ""
	}
	if base == "athletico" {
		state = ""
	}
	return base, state, display
}

// Competition names used throughout.
const (
	CompSerieA       = "Brasileirão Série A"
	CompSerieB       = "Brasileirão Série B"
	CompSerieC       = "Brasileirão Série C"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// normalizeCompetition maps free text to a canonical competition ("" = unknown).
func normalizeCompetition(s string) string {
	f := fold(s)
	switch {
	case f == "":
		return ""
	case strings.Contains(f, "libertadores"):
		return CompLibertadores
	case strings.Contains(f, "copa do brasil"), strings.Contains(f, "cup"), f == "copa":
		return CompCopaDoBrasil
	case strings.Contains(f, "serie b"):
		return CompSerieB
	case strings.Contains(f, "serie c"):
		return CompSerieC
	case strings.Contains(f, "brasileir"), strings.Contains(f, "serie a"), strings.Contains(f, "campeonato"), strings.Contains(f, "league"):
		return CompSerieA
	}
	return ""
}

var dateLayouts = []string{
	"2006-01-02 15:04:05", "2006-01-02T15:04:05Z07:00", "2006-01-02T15:04:05", "2006-01-02 15:04",
	"2006-01-02", "02/01/2006 15:04", "02/01/2006", "2/1/2006", "02-01-2006", "2006/01/02",
}

// parseDate accepts ISO, ISO with time and Brazilian DD/MM/YYYY dates.
func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	for _, l := range dateLayouts {
		if t, err := time.Parse(l, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}
