// Name and date normalization for the Brazilian soccer datasets.
//
// The source files spell the same club in several ways: "Palmeiras-SP",
// "Palmeiras - SP", "Sport Club Corinthians Paulista", "Atletico Mineiro",
// "Nacional (URU)". This file reduces every spelling to a base key plus an
// optional state code so that all files agree on team identity.

package main

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"
	"unicode"
)

// accentReplacer folds Portuguese and Spanish accents to ASCII. Input must
// already be lower-cased.
var accentReplacer = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u",
	"ç", "c", "ñ", "n",
)

// teamAlias gives the canonical base name and, where the spelling implies it,
// the state. Keys are foldKey output.
type teamAlias struct{ base, state string }

var teamAliases = map[string]teamAlias{
	"sportclubcorinthianspaulista": {"corinthians", "SP"},
	"sociedadeesportivapalmeiras":  {"palmeiras", "SP"},
	"clubederegatasdoflamengo":     {"flamengo", "RJ"},
	"sportclubdorecife":            {"sport", "PE"},
	"atleticomineiro":              {"atletico", "MG"},
	"atleticoparanaense":           {"atletico", "PR"},
	"atleticogoianiense":           {"atletico", "GO"},
	"atleticocearense":             {"atletico", "CE"},
	"atleticoacreano":              {"atletico", "AC"},
	"athletico":                    {"atletico", "PR"},
	"athleticoparanaense":          {"atletico", "PR"},
	"vascodagama":                  {"vasco", "RJ"},
	"rbbragantino":                 {"bragantino", "SP"},
	"redbullbragantino":            {"bragantino", "SP"},
}

// brazilianStates are the state codes that appear as a bare trailing word
// ("Botafogo RJ", "Vasco da Gama RJ").
var brazilianStates = map[string]bool{
	"AC": true, "AL": true, "AM": true, "AP": true, "BA": true, "CE": true, "DF": true,
	"ES": true, "GO": true, "MA": true, "MG": true, "MS": true, "MT": true, "PA": true,
	"PB": true, "PE": true, "PI": true, "PR": true, "RJ": true, "RN": true, "RO": true,
	"RR": true, "RS": true, "SC": true, "SE": true, "SP": true, "TO": true,
}

// clubNoiseWords are club-type words that the datasets add or drop
// ("EC Bahia", "CR Flamengo", "America FC", "Clube de Regatas do Flamengo").
var clubNoiseWords = map[string]bool{
	"cr": true, "fc": true, "cd": true, "ec": true, "sc": true, "ca": true, "ac": true,
	"clube": true, "club": true, "esporte": true, "de": true, "do": true, "da": true,
}

var (
	parenPattern  = regexp.MustCompile(`\(([^)]*)\)`)
	suffixPattern = regexp.MustCompile(`\s*[-–]\s*([A-Z]{2,3})\s*$`)
	stateCode     = regexp.MustCompile(`^[A-Z]{2,3}$`)
)

var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006",
	"2/1/2006",
}

// teamName is a club name split into its display form, base key and state.
type teamName struct {
	Display string
	Base    string
	State   string
}

// foldKey lower-cases s, strips accents and keeps only letters and digits.
// "São Paulo" and "Sao Paulo" both become "saopaulo".
func foldKey(s string) string {
	s = accentReplacer.Replace(strings.ToLower(strings.TrimSpace(s)))
	var b strings.Builder
	for _, r := range s {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// parseTeamName accepts any of the spellings used in the datasets.
// A state comes from a "-SP" / " - SP" suffix or a "(URU)" style parenthetical;
// a parenthetical that is not a state code, such as "(antigo ...)", is dropped.
func parseTeamName(raw string) teamName {
	s := strings.TrimSpace(raw)
	state := ""
	for _, m := range parenPattern.FindAllStringSubmatch(s, -1) {
		if c := strings.TrimSpace(m[1]); stateCode.MatchString(c) {
			state = c
		}
	}
	s = strings.Join(strings.Fields(parenPattern.ReplaceAllString(s, " ")), " ")
	if m := suffixPattern.FindStringSubmatch(s); m != nil {
		if state == "" {
			state = m[1]
		}
		s = strings.TrimSpace(suffixPattern.ReplaceAllString(s, ""))
	}
	// Long spellings are checked against the alias table before any trimming.
	if alias, ok := teamAliases[foldKey(s)]; ok {
		if state == "" {
			state = alias.state
		}
		return teamName{Display: s, Base: alias.base, State: state}
	}

	tokens := strings.Fields(s)
	if n := len(tokens); n > 1 && brazilianStates[tokens[n-1]] {
		if state == "" {
			state = tokens[n-1]
		}
		tokens = tokens[:n-1]
	}
	for len(tokens) > 1 && clubNoiseWords[foldKey(tokens[0])] {
		tokens = tokens[1:]
	}
	for len(tokens) > 1 && clubNoiseWords[foldKey(tokens[len(tokens)-1])] {
		tokens = tokens[:len(tokens)-1]
	}
	s = strings.Join(tokens, " ")

	base := foldKey(s)
	if alias, ok := teamAliases[base]; ok {
		base = alias.base
		if state == "" {
			state = alias.state
		}
	}
	return teamName{Display: s, Base: base, State: state}
}

// parseDate accepts the date shapes found in the datasets: ISO date, ISO
// date-time and Brazilian DD/MM/YYYY.
func parseDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("unrecognised date %q", s)
}

// parseGoals reads a goal count. Some files store integers as floats ("1.0")
// or quoted strings ("2").
func parseGoals(s string) (int, error) {
	f, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if err != nil {
		return 0, fmt.Errorf("invalid goal count %q", s)
	}
	if f < 0 || f != float64(int(f)) {
		return 0, fmt.Errorf("invalid goal count %q", s)
	}
	return int(f), nil
}
