// Team name normalization.
//
// The six datasets spell the same club differently: "Palmeiras-SP",
// "Palmeiras", "Sociedade Esportiva Palmeiras", "Sao Paulo" vs "São Paulo-SP",
// "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", etc.
// ParseTeam reduces every spelling to a base key (accent-free, lower-case,
// noise words removed) plus an optional two-letter state code. Two names
// match when their state codes agree (if both have one) and every token of
// the query appears in the candidate name.

package main

import (
	"regexp"
	"strings"
)

// TeamName is a normalized club name.
type TeamName struct {
	Raw    string   // original text as found in the data
	Base   string   // normalized base name, e.g. "corinthians paulista"
	State  string   // two-letter state code, "" if unknown or foreign
	Tokens []string // Base split on spaces
}

var (
	parenRe = regexp.MustCompile(`\([^)]*\)`)
	// "Palmeiras-SP", "América - MG", "Vasco Da Gama RJ": a trailing two-letter
	// code, optionally after a dash or space, marks the state. Only real UF
	// codes count, so "Fluminense FC" keeps its suffix as part of the name.
	stateSuffixRe = regexp.MustCompile(`(?:\s*-\s*|\s+)([A-Z]{2})\s*$`)
	nonAlnumRe    = regexp.MustCompile(`[^a-z0-9]+`)
)

// brazilianStates is the set of valid UF codes.
var brazilianStates = map[string]bool{
	"AC": true, "AL": true, "AP": true, "AM": true, "BA": true, "CE": true, "DF": true,
	"ES": true, "GO": true, "MA": true, "MT": true, "MS": true, "MG": true, "PA": true,
	"PB": true, "PR": true, "PE": true, "PI": true, "RJ": true, "RN": true, "RS": true,
	"RO": true, "RR": true, "SC": true, "SP": true, "SE": true, "TO": true,
}

// noiseTokens are generic club-name words that carry no identity.
var noiseTokens = map[string]bool{
	"club": true, "clube": true, "esporte": true, "futebol": true,
	"de": true, "do": true, "da": true, "dos": true, "das": true, "e": true,
	"ec": true, "fc": true, "sc": true, "ac": true, "atletica": true,
	"associacao": true, "regatas": true, "antigo": true, "sociedade": true,
}

var accentMap = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n',
}

// stripAccents lower-cases s and maps Portuguese/Spanish accented letters to ASCII.
func stripAccents(s string) string {
	var b strings.Builder
	for _, r := range strings.ToLower(s) {
		if m, ok := accentMap[r]; ok {
			r = m
		}
		b.WriteRune(r)
	}
	return b.String()
}

// ParseTeam normalizes a raw team name. fallbackState is used when the name
// carries no state suffix (for example the Mandante_UF column).
func ParseTeam(raw string, fallbackState string) TeamName {
	t := TeamName{Raw: raw, State: strings.ToUpper(strings.TrimSpace(fallbackState))}

	s := strings.TrimSpace(raw)
	if m := stateSuffixRe.FindStringSubmatch(s); m != nil && brazilianStates[m[1]] {
		t.State = m[1]
		s = stateSuffixRe.ReplaceAllString(s, "")
	}
	s = parenRe.ReplaceAllString(s, " ")
	s = stripAccents(s)
	s = nonAlnumRe.ReplaceAllString(s, " ")

	words := strings.Fields(s)
	kept := make([]string, 0, len(words))
	for i, w := range words {
		// "Sport Club ..." is noise, but a bare "Sport" (e.g. Sport Recife) is identity.
		if w == "sport" && i+1 < len(words) && words[i+1] == "club" {
			continue
		}
		if noiseTokens[w] {
			continue
		}
		kept = append(kept, w)
	}
	if len(kept) == 0 {
		// Name was entirely noise (e.g. "FC"); keep the raw words so it still matches.
		kept = words
	}
	t.Tokens = kept
	t.Base = strings.Join(kept, " ")
	return t
}

// Key is a stable identity used for de-duplication and team sets.
func (t TeamName) Key() string {
	if t.State == "" {
		return t.Base
	}
	return t.Base + "|" + t.State
}

// Empty reports whether the name has no usable tokens.
func (t TeamName) Empty() bool {
	return len(t.Tokens) == 0
}

// Matches reports whether this name, used as a query, refers to dataset team t.
// Every query token must appear in the dataset name, and the states must agree
// when both sides have one.
func (q TeamName) Matches(t TeamName) bool {
	if q.Empty() || t.Empty() {
		return false
	}
	if q.State != "" && t.State != "" && q.State != t.State {
		return false
	}
	return tokensSubset(q.Tokens, t.Tokens)
}

// SameClub reports whether two dataset names refer to the same club.
func (t TeamName) SameClub(o TeamName) bool {
	return t.Key() == o.Key()
}

func tokensSubset(sub, super []string) bool {
	set := make(map[string]bool, len(super))
	for _, w := range super {
		set[w] = true
	}
	for _, w := range sub {
		if !set[w] {
			return false
		}
	}
	return true
}
