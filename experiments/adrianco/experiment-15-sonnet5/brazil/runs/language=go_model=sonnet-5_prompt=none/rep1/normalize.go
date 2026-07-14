package main

import (
	"regexp"
	"strings"
)

// stateCodes is the whitelist of Brazilian state (UF) and South American
// country abbreviations used as trailing suffixes in team names across the
// provided datasets (e.g. "Palmeiras-SP", "América - MG", "Barcelona-EQU").
// Restricting to a whitelist (rather than "any 2-4 uppercase letters") avoids
// mis-stripping legitimate name fragments such as "FC" or "EC".
var stateCodes = map[string]bool{
	"AC": true, "AL": true, "AP": true, "AM": true, "BA": true, "CE": true,
	"DF": true, "ES": true, "GO": true, "MA": true, "MT": true, "MS": true,
	"MG": true, "PA": true, "PB": true, "PR": true, "PE": true, "PI": true,
	"RJ": true, "RN": true, "RS": true, "RO": true, "RR": true, "SC": true,
	"SP": true, "SE": true, "TO": true,
	// South American country codes seen in Libertadores data.
	"EQU": true, "URU": true, "PAR": true, "PER": true,
	"COL": true, "CHI": true, "ARG": true, "BOL": true, "VEN": true,
	"MEX": true, "ECU": true, "CRC": true, "BRA": true,
}

var parenRe = regexp.MustCompile(`\([^)]*\)`)
var trailingCodeRe = regexp.MustCompile(`^(.*?)[\s-]+([A-Z]{2,4})$`)
var nonAlnumRe = regexp.MustCompile(`[^a-z0-9 ]+`)
var multiSpaceRe = regexp.MustCompile(`\s+`)

// accentFold maps common Brazilian Portuguese accented runes to their
// unaccented equivalent. A manual table is used instead of a Unicode
// normalization package so the module has zero external dependencies.
var accentFold = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
	'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
	'ç': 'c', 'Ç': 'C',
	'ñ': 'n', 'Ñ': 'N',
	'ý': 'y', 'Ý': 'Y',
}

func foldAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if f, ok := accentFold[r]; ok {
			b.WriteRune(f)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// teamName holds the parsed pieces of a raw team name string.
type teamName struct {
	Base  string // normalized base key, e.g. "america"
	State string // uppercase state/country code if present, e.g. "MG"
	Full  string // Base plus state, uniquely identifying this variant
}

// parseTeamName splits a raw team name (as it appears in the source CSVs)
// into a normalized base key and an optional trailing state/country code.
func parseTeamName(raw string) teamName {
	s := strings.TrimSpace(raw)
	s = parenRe.ReplaceAllString(s, "")
	s = multiSpaceRe.ReplaceAllString(s, " ")
	s = strings.TrimSpace(s)

	state := ""
	if m := trailingCodeRe.FindStringSubmatch(s); m != nil {
		code := strings.ToUpper(m[2])
		if stateCodes[code] {
			candidate := strings.TrimSpace(m[1])
			if candidate != "" {
				state = code
				s = candidate
			}
		}
	}

	base := normalizeKey(s)
	full := base
	if state != "" {
		full = base + "|" + state
	}
	return teamName{Base: base, State: state, Full: full}
}

// normalizeKey lowercases, strips accents and punctuation, and collapses
// whitespace, producing a stable comparison key for free-form text such as
// club names, nationalities and positions.
func normalizeKey(s string) string {
	s = foldAccents(s)
	s = strings.ToLower(s)
	s = nonAlnumRe.ReplaceAllString(s, " ")
	s = multiSpaceRe.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}
