// Package normalize provides team-name normalization for matching across
// datasets that use different naming conventions (state suffixes, accents,
// short vs. long names).
package normalize

import (
	"regexp"
	"strings"
	"unicode"

	"golang.org/x/text/runes"
	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"
)

// stateSuffix matches a trailing " - SP", "-SP", " SP" or " (URU)" style code.
var (
	// dashStateSuffix matches a trailing 2-letter Brazilian state suffix such
	// as "-SP" or " - RJ". We intentionally only strip 2-letter codes because
	// 3+ letters could be a meaningful word in the team name.
	dashStateSuffix = regexp.MustCompile(`(?i)[\s\-]+[a-z]{2}$`)
	parenSuffix     = regexp.MustCompile(`\s*\([^)]*\)\s*$`)
	multispace      = regexp.MustCompile(`\s+`)
)

// nicknames maps common short/canonical team names to a canonical key.
// Values are the canonical normalized key used for comparison.
var nicknames = map[string]string{
	"sao paulo":      "sao paulo",
	"são paulo":      "sao paulo",
	"sao paulo fc":   "sao paulo",
	"flamengo":       "flamengo",
	"cr flamengo":    "flamengo",
	"palmeiras":      "palmeiras",
	"se palmeiras":   "palmeiras",
	"corinthians":    "corinthians",
	"sc corinthians": "corinthians",
	"santos":         "santos",
	"santos fc":      "santos",
	"fluminense":     "fluminense",
	"fluminense fc":  "fluminense",
	"botafogo":       "botafogo",
	"botafogo fr":    "botafogo",
	"vasco":          "vasco",
	"vasco da gama":  "vasco",
	"gremio":         "gremio",
	"grêmio":         "gremio",
	"internacional":  "internacional",
	"inter":          "internacional",
	"atletico":       "atletico",
	"atletico mg":    "atletico mg",
	"atletico-mg":    "atletico mg",
	"athletico":      "athletico pr",
	"athletico-pr":   "athletico pr",
	"athletico pr":   "athletico pr",
	"cruzeiro":       "cruzeiro",
	"bahia":          "bahia",
	"fortaleza":      "fortaleza",
	"ceara":          "ceara",
	"ceará":          "ceara",
}

// stripAccents removes diacritics so "Grêmio" matches "Gremio".
func stripAccents(s string) string {
	t := transform.Chain(norm.NFD, runes.Remove(runes.In(unicode.Mn)), norm.NFC)
	out, _, err := transform.String(t, s)
	if err != nil {
		return s
	}
	return out
}

// Key returns a normalized lookup key for a team name. It is case-folded,
// accent-stripped, and has state suffixes and trailing country codes removed.
func Key(name string) string {
	if name == "" {
		return ""
	}
	s := strings.TrimSpace(name)
	s = stripAccents(s)
	s = strings.ToLower(s)
	s = parenSuffix.ReplaceAllString(s, "")
	s = dashStateSuffix.ReplaceAllString(s, "")
	s = strings.TrimSpace(s)
	s = multispace.ReplaceAllString(s, " ")
	if canonical, ok := nicknames[s]; ok {
		return canonical
	}
	return s
}

// Matches reports whether two names are the same team after normalization.
// It also returns true when one normalized name is a prefix/substring of the
// other (useful for "Flamengo" vs "Flamengo-RJ" or "CR Flamengo").
func Matches(a, b string) bool {
	ka, kb := Key(a), Key(b)
	if ka == "" || kb == "" {
		return false
	}
	if ka == kb {
		return true
	}
	if strings.Contains(ka, kb) || strings.Contains(kb, ka) {
		return true
	}
	return false
}
