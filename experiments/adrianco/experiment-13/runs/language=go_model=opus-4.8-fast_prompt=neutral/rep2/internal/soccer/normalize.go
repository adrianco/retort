// Context: team-name and text normalization. The datasets refer to the same
// club in many ways ("Palmeiras-SP", "Palmeiras", "São Paulo", "Sao Paulo",
// "Nacional (URU)"). To match reliably we derive two things from a raw name:
//   - a cleaned *display* name (state/country suffixes and parentheticals
//     stripped, whitespace collapsed) shown to the user, and
//   - a *match key* (display name accent-folded to ASCII and lowercased) used
//     for equality and lookups.
//
// Accent folding is done with an explicit rune table so the package has no
// external dependencies.
package soccer

import (
	"regexp"
	"strings"
)

// trailing state/country suffix such as " - RJ", "-SP", " (URU)", "-EQU".
var (
	parenRe       = regexp.MustCompile(`\s*\([^)]*\)`)
	stateSuffixRe = regexp.MustCompile(`\s*-\s*[A-Z]{2,3}\s*$`)
	// stateCodeRe captures a trailing state/country code in any of the forms
	// "-SP", " - MG", "(URU)".
	stateCodeRe = regexp.MustCompile(`(?:\s*-\s*|\s*\()([A-Z]{2,3})\)?\s*$`)
)

// accentFold maps accented Latin characters used in Brazilian Portuguese (and
// neighbouring Spanish names) to their ASCII equivalents.
var accentFold = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y', 'ÿ': 'y',
}

// foldAccents returns s with accented characters replaced by ASCII equivalents.
func foldAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if folded, ok := accentFold[r]; ok {
			b.WriteRune(folded)
			continue
		}
		// Also fold uppercase accented forms by lowercasing first.
		if folded, ok := accentFold[toLowerRune(r)]; ok {
			b.WriteRune(folded)
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

func toLowerRune(r rune) rune {
	if r >= 'A' && r <= 'Z' {
		return r + ('a' - 'A')
	}
	// Map common uppercase accented forms.
	switch r {
	case 'Á', 'À', 'Â', 'Ã', 'Ä':
		return 'á'
	case 'É', 'È', 'Ê', 'Ë':
		return 'é'
	case 'Í', 'Ì', 'Î', 'Ï':
		return 'í'
	case 'Ó', 'Ò', 'Ô', 'Õ', 'Ö':
		return 'ó'
	case 'Ú', 'Ù', 'Û', 'Ü':
		return 'ú'
	case 'Ç':
		return 'ç'
	case 'Ñ':
		return 'ñ'
	}
	return r
}

// cleanTeamName strips parentheticals and state/country suffixes and collapses
// whitespace, producing a display name.
func cleanTeamName(raw string) string {
	s := strings.TrimSpace(raw)
	s = parenRe.ReplaceAllString(s, "")
	s = stateSuffixRe.ReplaceAllString(s, "")
	s = strings.Join(strings.Fields(s), " ")
	return strings.TrimSpace(s)
}

// teamKey returns the accent-folded, lowercased match key for a raw or cleaned
// team name.
func teamKey(name string) string {
	return strings.ToLower(foldAccents(cleanTeamName(name)))
}

// suffixState returns the trailing state/country code embedded in a raw team
// name ("Palmeiras-SP" -> "SP", "América - MG" -> "MG", "Nacional (URU)" ->
// "URU"), or "" if none is present.
func suffixState(raw string) string {
	if m := stateCodeRe.FindStringSubmatch(raw); m != nil {
		return m[1]
	}
	return ""
}

// matchKey lowercases and folds accents without stripping suffixes. Used for
// free-text fields such as player names and club names.
func matchKey(s string) string {
	return strings.ToLower(foldAccents(strings.Join(strings.Fields(s), " ")))
}
