// Normalization helpers. Team names, competition names and dates are written
// inconsistently across the datasets, so everything is folded to a common form
// before matching.
//
// Team identity is the tricky part: some files write "Palmeiras-SP", others
// "Palmeiras", others a full name. A team is reduced to a teamIdentity (a base
// name plus an optional state/country code) so that variants of the same club
// compare equal while genuinely different clubs that share a base name
// (Atlético-MG vs Atlético-PR vs Atlético-GO) stay distinct.
package main

import (
	"regexp"
	"strings"
	"time"
)

var accentMap = map[rune]rune{
	'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
	'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
	'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
	'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
	'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
	'ç': 'c', 'ñ': 'n', 'ý': 'y', 'ÿ': 'y',
	'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A',
	'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
	'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
	'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
	'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
	'Ç': 'C', 'Ñ': 'N',
}

// stripAccents folds Portuguese/Spanish diacritics to plain ASCII so that
// "São Paulo" and "Sao Paulo" compare equal.
func stripAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		if m, ok := accentMap[r]; ok {
			b.WriteRune(m)
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}

var (
	// Trailing state/country code joined by a dash, e.g. "Palmeiras-SP".
	reDashSuffix = regexp.MustCompile(`\s*-\s*[A-Za-z]{2,3}\s*$`)
	// Trailing country code in parentheses, e.g. "Nacional (URU)".
	reParenSuffix = regexp.MustCompile(`\s*\([A-Za-z]{2,4}\)\s*$`)
	// Trailing space-separated two-letter code, e.g. "Vasco da Gama RJ".
	reSpaceSuffix = regexp.MustCompile(`\s+[A-Za-z]{2}\s*$`)
	reMultiSpace  = regexp.MustCompile(`\s+`)
	reLetters     = regexp.MustCompile(`[A-Za-z]+`)
)

// ufCodes are the 27 Brazilian state abbreviations.
var ufCodes = map[string]bool{
	"ac": true, "al": true, "ap": true, "am": true, "ba": true, "ce": true,
	"df": true, "es": true, "go": true, "ma": true, "mt": true, "ms": true,
	"mg": true, "pa": true, "pb": true, "pr": true, "pe": true, "pi": true,
	"rj": true, "rn": true, "rs": true, "ro": true, "rr": true, "sc": true,
	"sp": true, "se": true, "to": true,
}

// spellingAliases folds known alternate spellings to one canonical token.
var spellingAliases = map[string]string{"athletico": "atletico"}

// stateNicknames maps club-name qualifiers to state codes so that a full name
// ("Atlético Mineiro") lines up with the suffixed form ("Atlético-MG").
var stateNicknames = map[string]string{
	"mineiro": "mg", "paranaense": "pr", "goianiense": "go",
}

// ambiguousBases are base names shared by several distinct clubs; for these the
// state code is kept when grouping so the clubs are not merged.
var ambiguousBases = map[string]bool{"atletico": true, "america": true}

// teamIdentity is a normalized, comparable team identity.
type teamIdentity struct {
	base  string // accent-folded lowercase name, state/country suffix removed
	state string // 2-3 letter state/country code, lowercase, "" if unknown
}

// groupKey returns the key used to group matches by team. Ambiguous base names
// keep their state code so clubs in different states stay separate.
func (t teamIdentity) groupKey() string {
	if t.base == "" {
		return ""
	}
	if ambiguousBases[t.base] && t.state != "" {
		return t.base + "|" + t.state
	}
	return t.base
}

// splitTeamSuffix strips any trailing state/country code from a raw team name,
// returning the cleaned name and the extracted code (lowercase, "" if none).
func splitTeamSuffix(raw string) (name, state string) {
	s := strings.TrimSpace(raw)
	for {
		before := s
		if loc := reParenSuffix.FindString(s); loc != "" {
			state = strings.ToLower(reLetters.FindString(loc))
			s = strings.TrimSpace(s[:len(s)-len(loc)])
		}
		if loc := reDashSuffix.FindString(s); loc != "" {
			state = strings.ToLower(reLetters.FindString(loc))
			s = strings.TrimSpace(s[:len(s)-len(loc)])
		}
		if loc := reSpaceSuffix.FindString(s); loc != "" {
			if code := strings.ToLower(strings.TrimSpace(loc)); ufCodes[code] {
				state = code
				s = strings.TrimSpace(s[:len(s)-len(loc)])
			}
		}
		if s == before {
			break
		}
	}
	return strings.TrimSpace(reMultiSpace.ReplaceAllString(s, " ")), state
}

// cleanTeamName removes state/country suffixes while keeping accents and case.
func cleanTeamName(raw string) string {
	name, _ := splitTeamSuffix(raw)
	return name
}

// displayTeamName is cleanTeamName plus a state tag for ambiguous clubs, e.g.
// "Atlético-MG" becomes "Atlético (MG)" so the three Atléticos are told apart.
func displayTeamName(raw string) string {
	name, _ := splitTeamSuffix(raw)
	id := parseTeamIdentity(raw)
	if ambiguousBases[id.base] && id.state != "" {
		return name + " (" + strings.ToUpper(id.state) + ")"
	}
	return name
}

// parseTeamIdentity reduces a raw team name to a teamIdentity.
func parseTeamIdentity(raw string) teamIdentity {
	name, state := splitTeamSuffix(raw)
	base := stripAccents(strings.ToLower(name))
	base = strings.TrimSpace(reMultiSpace.ReplaceAllString(base, " "))

	words := strings.Fields(base)
	for i, w := range words {
		if a, ok := spellingAliases[w]; ok {
			words[i] = a
		}
	}
	// A trailing nickname ("Mineiro") resolves to a state code; the word is
	// kept so the base stays specific enough not to match unrelated clubs.
	if len(words) >= 2 {
		if code, ok := stateNicknames[words[len(words)-1]]; ok {
			state = code
		}
	}
	return teamIdentity{base: strings.Join(words, " "), state: state}
}

// containsWord reports whether the words of needle appear as a contiguous run
// inside the words of haystack.
func containsWord(haystack, needle string) bool {
	hw := strings.Fields(haystack)
	nw := strings.Fields(needle)
	if len(nw) == 0 || len(nw) > len(hw) {
		return false
	}
	for i := 0; i+len(nw) <= len(hw); i++ {
		match := true
		for j := range nw {
			if hw[i+j] != nw[j] {
				match = false
				break
			}
		}
		if match {
			return true
		}
	}
	return false
}

// identityMatches reports whether a team satisfies a free-text query. It
// accepts exact base matches and whole-word containment in either direction
// ("Corinthians" matches "Sport Club Corinthians Paulista"), and rejects a
// match when both sides name a state code and the codes differ.
func identityMatches(t teamIdentity, query string) bool {
	q := parseTeamIdentity(query)
	if q.base == "" {
		return true
	}
	if q.state != "" && t.state != "" && q.state != t.state {
		return false
	}
	if t.base == q.base {
		return true
	}
	return containsWord(t.base, q.base) || containsWord(q.base, t.base)
}

// normalizeCompetition maps the competition labels used by the datasets onto a
// small canonical set of names.
func normalizeCompetition(raw string) string {
	s := strings.TrimSpace(raw)
	low := stripAccents(strings.ToLower(s))
	switch {
	case strings.Contains(low, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(low, "copa do brasil"):
		return "Copa do Brasil"
	case strings.Contains(low, "serie a"):
		return "Brasileirão Série A"
	case strings.Contains(low, "serie b"):
		return "Brasileirão Série B"
	case strings.Contains(low, "serie c"):
		return "Brasileirão Série C"
	}
	if s == "" {
		return "Unknown"
	}
	return s
}

// resolveCompetition maps a free-text competition query onto a single
// canonical competition name. Used where exactly one competition is required
// (standings); returns the query trimmed when nothing matches.
func resolveCompetition(query string) string {
	low := stripAccents(strings.ToLower(strings.TrimSpace(query)))
	switch {
	case low == "":
		return ""
	case strings.Contains(low, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(low, "copa do brasil") || low == "cup" || strings.Contains(low, "brazilian cup"):
		return "Copa do Brasil"
	case strings.Contains(low, "serie b"):
		return "Brasileirão Série B"
	case strings.Contains(low, "serie c"):
		return "Brasileirão Série C"
	case strings.Contains(low, "serie a") || strings.Contains(low, "brasileir") || strings.Contains(low, "campeonato brasileiro"):
		return "Brasileirão Série A"
	}
	return strings.TrimSpace(query)
}

var dateFormats = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006 15:04:05",
	"02/01/2006",
	"2006/01/02",
}

// parseDate tries every known date layout and reports whether one succeeded.
func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false
	}
	for _, f := range dateFormats {
		if t, err := time.Parse(f, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// betterDisplay picks the nicer of two display names: the one with more
// accented characters wins, falling back to the longer string.
func betterDisplay(a, b string) string {
	if a == "" {
		return b
	}
	if b == "" {
		return a
	}
	if ca, cb := accentCount(a), accentCount(b); ca != cb {
		if ca > cb {
			return a
		}
		return b
	}
	if len(a) >= len(b) {
		return a
	}
	return b
}

func accentCount(s string) int {
	n := 0
	for _, r := range s {
		if _, ok := accentMap[r]; ok {
			n++
		}
	}
	return n
}
