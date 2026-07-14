// Package soccer holds the Brazilian soccer domain: the unified Match and
// Player models, team-name normalization (handling state/country suffixes and
// Portuguese accents), and the in-memory Store that answers domain queries.
//
// This file defines the core domain types and the name-normalization rules that
// let the same club be matched across datasets that spell it differently
// ("Palmeiras-SP", "Palmeiras", "São Paulo" vs "Sao Paulo").
package soccer

import (
	"regexp"
	"strings"
	"time"
)

// Match is the unified representation of a game drawn from any of the match
// datasets. Team names are stored as cleaned display names (suffix-stripped,
// original accents preserved).
type Match struct {
	Competition string
	Season      int
	Round       string
	Stage       string
	Date        time.Time
	HasDate     bool
	HomeTeam    string
	AwayTeam    string
	HomeGoals   int
	AwayGoals   int
	Source      string // originating file, for diagnostics
}

// Player is the unified representation of a FIFA player record.
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string
}

// trailing state ("-SP", " - RJ") or country/parenthetical code ("(URU)", "-EQU"),
// with the code captured for canonicalization.
var (
	suffixDash  = regexp.MustCompile(`\s*-\s*([A-Z]{2,3})\s*$`)
	suffixParen = regexp.MustCompile(`\s*\(([A-Z]{2,4})\)\s*$`)
)

// splitSuffix separates a team name from its trailing state/country code, e.g.
// "Atletico-MG" -> ("Atletico", "MG") and "Nacional (URU)" -> ("Nacional",
// "URU"). When no code is present the second value is empty.
func splitSuffix(raw string) (base, code string) {
	name := strings.TrimSpace(raw)
	if m := suffixParen.FindStringSubmatch(name); m != nil {
		return strings.TrimSpace(name[:len(name)-len(m[0])]), m[1]
	}
	if m := suffixDash.FindStringSubmatch(name); m != nil {
		return strings.TrimSpace(name[:len(name)-len(m[0])]), m[1]
	}
	return name, ""
}

// CleanTeamName strips a trailing state/country suffix and surrounding
// whitespace while preserving the team's accents and casing. Used for loose,
// display-friendly rendering of a user's query term.
func CleanTeamName(raw string) string {
	name := strings.TrimSpace(raw)
	for {
		base, code := splitSuffix(name)
		if code == "" {
			break
		}
		name = base
	}
	if name == "" {
		return strings.TrimSpace(raw)
	}
	return name
}

// CanonicalTeam produces the stable display identity for a club, KEEPING its
// state/country code so that distinct clubs sharing a base name (Atlético-MG vs
// Atlético-PR) remain separate. When the name itself carries no code but the
// dataset supplies one in a separate column (state), that code is appended, so
// "Flamengo" (state RJ) and "Flamengo-RJ" resolve to the same identity.
func CanonicalTeam(raw, state string) string {
	base, code := splitSuffix(raw)
	if code == "" {
		code = strings.ToUpper(strings.TrimSpace(state))
	}
	base = strings.TrimSpace(base)
	if base == "" {
		base = strings.TrimSpace(raw)
	}
	if code != "" {
		return base + "-" + code
	}
	return base
}

// IdentityKey is the strict grouping key for a (already canonical) team name:
// accent-folded and lower-cased but, unlike NormalizeKey, it does NOT discard
// the state code, so same-base clubs stay distinct in standings and dedup.
func IdentityKey(name string) string {
	folded := strings.ToLower(accentFolder.Replace(strings.TrimSpace(name)))
	return strings.Join(strings.Fields(folded), " ")
}

// foldAccents maps the Portuguese (and a few Spanish) diacritics that appear in
// the datasets to their ASCII equivalents, so accent-insensitive matching works
// without pulling in golang.org/x/text.
var accentFolder = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u",
	"ç", "c", "ñ", "n",
	"Á", "A", "À", "A", "Â", "A", "Ã", "A", "Ä", "A",
	"É", "E", "È", "E", "Ê", "E", "Ë", "E",
	"Í", "I", "Ì", "I", "Î", "I", "Ï", "I",
	"Ó", "O", "Ò", "O", "Ô", "O", "Õ", "O", "Ö", "O",
	"Ú", "U", "Ù", "U", "Û", "U", "Ü", "U",
	"Ç", "C", "Ñ", "N",
)

// NormalizeKey produces an accent-folded, lower-cased, suffix-stripped key used
// for matching team names across datasets and against user queries.
func NormalizeKey(raw string) string {
	cleaned := CleanTeamName(raw)
	folded := accentFolder.Replace(cleaned)
	folded = strings.ToLower(folded)
	folded = strings.Join(strings.Fields(folded), " ")
	return folded
}

// teamMatches reports whether a stored team name matches a user-supplied query
// term. Matching is accent- and suffix-insensitive and allows the query to be a
// substring of the team name (so "Flamengo" matches "Flamengo-RJ" and the query
// term may also be the longer form).
func teamMatches(team, query string) bool {
	if query == "" {
		return true
	}
	t := NormalizeKey(team)
	q := NormalizeKey(query)
	if t == q {
		return true
	}
	return strings.Contains(t, q) || strings.Contains(q, t)
}

// containsFold reports whether query is contained in value, accent- and
// case-insensitively. Used for free-text fields like club and nationality.
func containsFold(value, query string) bool {
	if query == "" {
		return true
	}
	v := strings.ToLower(accentFolder.Replace(strings.TrimSpace(value)))
	q := strings.ToLower(accentFolder.Replace(strings.TrimSpace(query)))
	return strings.Contains(v, q)
}
