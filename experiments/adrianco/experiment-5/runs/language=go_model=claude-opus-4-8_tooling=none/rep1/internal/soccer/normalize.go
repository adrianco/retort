// Context:
//   - This file handles the messy real-world naming in the datasets. Team names
//     appear with state suffixes ("Palmeiras-SP"), country suffixes
//     ("Barcelona-EQU"), parenthetical notes ("Nacional (URU)") and with
//     Portuguese accents ("Grêmio", "São Paulo").
//   - NormalizeTeam produces an accent-free, suffix-free, lower-cased key used
//     for matching and de-duplication. CleanTeamName produces a human-friendly
//     display name (accents preserved, suffix removed).
//   - Competition labels also vary by source ("Serie A", "Brasileirao Serie A",
//     ...); canonicalCompetition maps raw labels onto the canonical constants in
//     models.go, and CompetitionMatches does loose user-query matching.
//   - We deliberately avoid golang.org/x/text so the module has zero external
//     dependencies; diacritic folding is done with a small explicit table that
//     covers the characters present in Brazilian Portuguese club names.
package soccer

import (
	"regexp"
	"strings"
)

// Brazilian state (UF) codes used as team-name suffixes.
var brazilianStates = map[string]bool{
	"AC": true, "AL": true, "AP": true, "AM": true, "BA": true, "CE": true,
	"DF": true, "ES": true, "GO": true, "MA": true, "MT": true, "MS": true,
	"MG": true, "PA": true, "PB": true, "PR": true, "PE": true, "PI": true,
	"RJ": true, "RN": true, "RS": true, "RO": true, "RR": true, "SC": true,
	"SP": true, "SE": true, "TO": true,
}

var (
	parenRe  = regexp.MustCompile(`\s*\([^)]*\)`)
	spacesRe = regexp.MustCompile(`\s+`)
	// trailing " - XX" / "-XXX" suffix of 2-4 letters (state or country code)
	suffixRe = regexp.MustCompile(`\s*-\s*[A-Za-zÀ-ÿ]{2,4}\s*$`)
)

// diacritics folds accented Latin characters down to ASCII.
var diacritics = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y', 'ÿ': 'y',
	'Á': 'a', 'À': 'a', 'Â': 'a', 'Ã': 'a', 'Ä': 'a', 'Å': 'a',
	'É': 'e', 'È': 'e', 'Ê': 'e', 'Ë': 'e',
	'Í': 'i', 'Ì': 'i', 'Î': 'i', 'Ï': 'i',
	'Ó': 'o', 'Ò': 'o', 'Ô': 'o', 'Õ': 'o', 'Ö': 'o',
	'Ú': 'u', 'Ù': 'u', 'Û': 'u', 'Ü': 'u',
	'Ç': 'c', 'Ñ': 'n',
}

// foldAccents replaces accented characters with their ASCII base.
func foldAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if base, ok := diacritics[r]; ok {
			b.WriteRune(base)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// stripSuffix removes a parenthetical note and a trailing state/country code.
func stripSuffix(s string) string {
	s = parenRe.ReplaceAllString(s, "")
	// Only strip a trailing "-XX" code when it looks like a state/country code,
	// not part of a hyphenated name.
	if m := suffixRe.FindString(s); m != "" {
		code := strings.ToUpper(strings.TrimSpace(strings.TrimLeft(strings.TrimSpace(m), "-")))
		if brazilianStates[code] || len(code) == 3 { // 3-letter -> country code (URU, EQU...)
			s = suffixRe.ReplaceAllString(s, "")
		}
	}
	return strings.TrimSpace(spacesRe.ReplaceAllString(s, " "))
}

// CleanTeamName returns a display name with the suffix/parenthetical removed but
// accents and casing preserved.
func CleanTeamName(s string) string {
	return stripSuffix(strings.TrimSpace(s))
}

// NormalizeTeam returns the identity key for a team name. The state/country
// suffix is DELIBERATELY KEPT (folded into the key) because it disambiguates
// distinct clubs that share a base name — e.g. Atlético-MG, Atlético-GO and
// Athletico-PR can all appear in the same Série A season, and collapsing them
// to "atletico" would merge three different clubs. Within any single source
// file the suffix usage is consistent, so this yields correct grouping for
// standings and statistics.
func NormalizeTeam(s string) string {
	s = strings.TrimSpace(s)
	s = parenRe.ReplaceAllString(s, "") // drop "(URU)" style notes
	s = foldAccents(s)
	s = strings.ToLower(s)
	s = strings.ReplaceAll(s, " - ", "-") // unify "America - MG" -> "america-mg"
	return strings.TrimSpace(spacesRe.ReplaceAllString(s, " "))
}

// normalizeText folds accents and lower-cases arbitrary text (player names,
// clubs, search terms).
func normalizeText(s string) string {
	return strings.TrimSpace(spacesRe.ReplaceAllString(strings.ToLower(foldAccents(s)), " "))
}

// TeamMatches reports whether a user-supplied query refers to the given
// normalized team key. Matching is substring-based in both directions, so a
// bare "flamengo" matches the stored key "flamengo-rj", while a query that
// includes the suffix ("atletico-mg") will NOT match a different club
// ("atletico-go").
func TeamMatches(query, teamNorm string) bool {
	q := NormalizeTeam(query)
	if q == "" {
		return false
	}
	if q == teamNorm {
		return true
	}
	return strings.Contains(teamNorm, q) || strings.Contains(q, teamNorm)
}

// canonicalCompetition maps a raw source label onto one of the canonical
// competition names. Returns the trimmed original if no rule matches.
func canonicalCompetition(raw string) string {
	r := normalizeText(raw)
	switch {
	case strings.Contains(r, "libertadores"):
		return CompLibertadores
	case strings.Contains(r, "copa do brasil"):
		return CompCopaDoBrasil
	case strings.Contains(r, "serie c"):
		return CompSerieC
	case strings.Contains(r, "serie b"):
		return CompSerieB
	case strings.Contains(r, "serie a"), strings.Contains(r, "brasileir"):
		return CompSerieA
	default:
		return strings.TrimSpace(raw)
	}
}

// CompetitionMatches reports whether a user query refers to a competition.
// An empty query matches everything.
func CompetitionMatches(query, competition string) bool {
	if strings.TrimSpace(query) == "" {
		return true
	}
	q := normalizeText(query)
	c := normalizeText(competition)
	// Map common shorthands onto the canonical name first.
	switch canonicalCompetition(query) {
	case CompLibertadores, CompCopaDoBrasil, CompSerieA, CompSerieB, CompSerieC:
		return c == normalizeText(canonicalCompetition(query))
	}
	return strings.Contains(c, q)
}
