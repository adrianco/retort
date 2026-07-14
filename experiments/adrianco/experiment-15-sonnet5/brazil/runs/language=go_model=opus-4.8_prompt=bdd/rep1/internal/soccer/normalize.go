package soccer

import (
	"regexp"
	"strings"
	"unicode"

	"golang.org/x/text/runes"
	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"
)

// Team-name normalisation is the trickiest part of the data: the same club is
// spelled several ways across the datasets, and — worse — a bare base name can
// be ambiguous. For example "Atletico-MG" (Mineiro), "Atletico-PR"
// (Paranaense) and "Atletico-GO" (Goianiense) are three different clubs that
// share the base name "Atlético", so naively stripping the state suffix would
// merge them. Meanwhile BR-Football writes them out in full ("Atletico
// Mineiro") and other files add club-type words ("EC Bahia", "Fortaleza FC").
//
// The resolver works in two steps:
//  1. Look the accent-folded, suffix-intact "raw key" up in an alias table that
//     maps every known variant of an ambiguous or oddly-spelled club to a
//     single canonical key.
//  2. Fall back, for everything else, to the base key (state/country suffix
//     stripped, accents folded). This unifies the common case where the only
//     difference is a "-SP"-style suffix or an accent.

var (
	// trailing " - MG", "-SP" style Brazilian state suffixes.
	stateSuffixRe = regexp.MustCompile(`-[a-z]{2}$`)
	// trailing country codes, e.g. "(uru)" or "-equ".
	parenCountryRe = regexp.MustCompile(`\s*\([a-z]{2,4}\)$`)
	dashCountryRe  = regexp.MustCompile(`-[a-z]{3}$`)
	dashSpacingRe  = regexp.MustCompile(`\s*-\s*`)
	multiSpaceRe   = regexp.MustCompile(`\s+`)
)

// clubAliases maps a normalised raw key (accents folded, lower-cased, dash
// spacing collapsed) to a canonical club key. Only clubs that would otherwise
// be mis-merged or fail to unify need an entry here.
var clubAliases = map[string]string{
	// Atlético family — base name collides, so the suffix disambiguates.
	"atletico-go":          "atletico goianiense",
	"atletico goianiense":  "atletico goianiense",
	"atletico-mg":          "atletico mineiro",
	"atletico mineiro":     "atletico mineiro",
	"atletico-pr":          "athletico paranaense",
	"athletico-pr":         "athletico paranaense",
	"atletico paranaense":  "athletico paranaense",
	"athletico paranaense": "athletico paranaense",
	"athletico":            "athletico paranaense",
	// América family.
	"america-mg":      "america mineiro",
	"america mg":      "america mineiro",
	"america mineiro": "america mineiro",
	"america-rn":      "america rn",
	// Vasco: "Vasco" vs "Vasco da Gama" vs "Vasco Da Gama RJ".
	"vasco":            "vasco da gama",
	"vasco da gama":    "vasco da gama",
	"vasco da gama-rj": "vasco da gama",
	"vasco da gama rj": "vasco da gama",
	// Club-type prefixes/suffixes and city qualifiers.
	"ec bahia":            "bahia",
	"fortaleza fc":        "fortaleza",
	"botafogo rj":         "botafogo",
	"ec juventude":        "juventude",
	"santa cruz fc":       "santa cruz",
	"sport recife":        "sport",
	"red bull bragantino": "bragantino",
	"bragantino":          "bragantino",
}

// clubDisplayNames gives a clean, correctly-accented display name for canonical
// keys whose most-common raw spelling would otherwise be ambiguous.
var clubDisplayNames = map[string]string{
	"atletico goianiense":  "Atlético Goianiense",
	"atletico mineiro":     "Atlético Mineiro",
	"athletico paranaense": "Athletico Paranaense",
	"america mineiro":      "América Mineiro",
	"america rn":           "América-RN",
	"vasco da gama":        "Vasco da Gama",
	"bragantino":           "Red Bull Bragantino",
}

// foldAccents removes diacritics (São -> Sao, Grêmio -> Gremio).
func foldAccents(s string) string {
	t := transform.Chain(norm.NFD, runes.Remove(runes.In(unicode.Mn)), norm.NFC)
	out, _, err := transform.String(t, s)
	if err != nil {
		return s
	}
	return out
}

// rawKey folds accents, lower-cases and collapses dash/space spacing, but keeps
// any state/country suffix intact so the alias table can use it.
func rawKey(raw string) string {
	s := foldAccents(strings.TrimSpace(raw))
	s = strings.ToLower(s)
	s = dashSpacingRe.ReplaceAllString(s, "-")
	s = multiSpaceRe.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// baseKey strips a trailing state or country suffix from a raw key.
func baseKey(rk string) string {
	rk = dashCountryRe.ReplaceAllString(rk, "")
	rk = parenCountryRe.ReplaceAllString(rk, "")
	rk = stateSuffixRe.ReplaceAllString(rk, "")
	rk = multiSpaceRe.ReplaceAllString(rk, " ")
	return strings.TrimSpace(rk)
}

// NormalizeTeam returns the canonical matching key for a team name. Two names
// that refer to the same club produce the same key.
func NormalizeTeam(raw string) string {
	rk := rawKey(raw)
	if rk == "" {
		return ""
	}
	if canon, ok := clubAliases[rk]; ok {
		return canon
	}
	return baseKey(rk)
}

// CleanTeam returns a human-friendly display name with the state/country suffix
// stripped but the original casing and accents preserved.
func CleanTeam(raw string) string {
	s := strings.TrimSpace(raw)
	s = dashSpacingRe.ReplaceAllString(s, "-")
	// Strip a trailing "-XX"/"-XXX"/"(XXX)" suffix, preserving casing/accents.
	s = regexp.MustCompile(`-[A-Za-z]{2,3}$`).ReplaceAllString(s, "")
	s = regexp.MustCompile(`\s*\([A-Za-z]{2,4}\)$`).ReplaceAllString(s, "")
	s = multiSpaceRe.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// canonicalDisplayName returns a curated display name for a canonical key, if
// one is defined.
func canonicalDisplayName(key string) (string, bool) {
	name, ok := clubDisplayNames[key]
	return name, ok
}

// NormalizeName returns the matching key for a player or free-text name.
func NormalizeName(raw string) string {
	s := foldAccents(strings.TrimSpace(raw))
	s = strings.ToLower(s)
	s = multiSpaceRe.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}
