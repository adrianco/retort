// Package soccer builds and queries an in-memory knowledge graph of Brazilian
// soccer data (teams, matches, competitions and players) loaded from the Kaggle
// CSV datasets shipped in data/kaggle.
//
// normalize.go holds the team-name normalisation machinery. The source datasets
// spell the same club in many different ways ("Palmeiras-SP", "Palmeiras",
// "Atlético - MG", "Atletico Mineiro", "Sport Club do Recife", ...), so every
// raw name is parsed into a (base, region) pair which, combined with the alias
// tables in aliases.go, yields a stable canonical team ID.
package soccer

import (
	"regexp"
	"strings"
	"unicode"

	"golang.org/x/text/runes"
	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"
)

// brazilianStates is the set of two-letter Brazilian federative unit codes used
// as team-name suffixes throughout the datasets.
var brazilianStates = map[string]string{
	"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
	"BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
	"GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
	"MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
	"PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
	"RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
	"SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}

// foreignCodes are the three-letter country codes the Libertadores dataset uses
// for non-Brazilian clubs.
var foreignCodes = map[string]string{
	"URU": "Uruguay", "PAR": "Paraguay", "PER": "Peru", "EQU": "Ecuador",
	"VEN": "Venezuela", "ARG": "Argentina", "BOL": "Bolivia", "CHI": "Chile",
	"COL": "Colombia", "MEX": "Mexico", "BRA": "Brazil", "USA": "United States",
}

// nameStopwords are Portuguese/Spanish connectors dropped from the slug so that
// "Vasco da Gama" and "Vasco Da Gama RJ" collapse onto the same base.
var nameStopwords = map[string]bool{
	"de": true, "do": true, "da": true, "dos": true, "das": true,
	"e": true, "of": true, "the": true, "el": true, "la": true,
}

// clubTypeTokens are generic club-type words and acronyms ("Futebol Clube",
// "EC", "FC", ...) that carry no identity and are stripped from the slug.
// Deliberately absent: "sport" (Sport Recife), "esportivo" (Clube Esportivo),
// "sporting" (Sporting Cristal) — those are part of real club identities.
var clubTypeTokens = map[string]bool{
	"fc": true, "ec": true, "sc": true, "ac": true, "ca": true, "cr": true,
	"ad": true, "ge": true, "cs": true, "sd": true, "aa": true, "cd": true,
	"se": true, "af": true, "ae": true, "sr": true, "fr": true, "ce": true,
	"clube": true, "club": true, "futebol": true, "esporte": true,
	"associacao": true, "regatas": true, "ltda": true,
}

var (
	// "Nacional (URU)", "River (PI)" — region in parentheses.
	reParenRegion = regexp.MustCompile(`\s*\(([A-Z]{2,3})\)$`)
	// "Palmeiras-SP", "América - MG", "Barcelona-EQU".
	reDashRegion = regexp.MustCompile(`\s*-\s*([A-Z]{2,3})$`)
	// "America MG", "ASA AL" — space separated, requires a preceding word.
	reSpaceRegion = regexp.MustCompile(`\S\s+([A-Z]{2,3})$`)
	// Any leftover parenthetical, e.g. "(antigo Esporte Clube Barreira)".
	reParenthetical = regexp.MustCompile(`\s*\([^)]*\)`)
	reNonAlnum      = regexp.MustCompile(`[^a-z0-9]+`)
)

// ParsedName is the structural decomposition of a raw team name found in a CSV.
type ParsedName struct {
	Raw    string // exactly as it appeared in the dataset
	Clean  string // display form: region suffix and parentheticals removed
	Base   string // canonical slug of the club name, without region
	Region string // "SP", "MG", "URU", ... or "" when the source omitted it
	// DefaultRegion is the curated fall-back region for club names that are
	// ambiguous across states (bare "Flamengo" almost always means Flamengo-RJ).
	// It is only consulted once the explicit and data-derived regions fail.
	DefaultRegion string
}

// FoldASCII strips diacritics so that "São Paulo" and "Sao Paulo" compare equal.
func FoldASCII(s string) string {
	t := transform.Chain(norm.NFD, runes.Remove(runes.In(unicode.Mn)), norm.NFC)
	out, _, err := transform.String(t, s)
	if err != nil {
		return s
	}
	// A few letters have no combining-mark decomposition.
	r := strings.NewReplacer("ø", "o", "Ø", "O", "đ", "d", "Đ", "D", "ß", "ss", "æ", "ae", "Æ", "AE")
	return r.Replace(out)
}

// Slug reduces an arbitrary string to lower-case alphanumerics, which is the
// comparison form used for every lookup key in the graph.
func Slug(s string) string {
	s = strings.ToLower(FoldASCII(s))
	s = reNonAlnum.ReplaceAllString(s, "")
	return s
}

// tokenize splits a folded name into lower-case alphanumeric tokens.
func tokenize(s string) []string {
	s = strings.ToLower(FoldASCII(s))
	raw := reNonAlnum.Split(s, -1)
	out := make([]string, 0, len(raw))
	for _, t := range raw {
		if t != "" {
			out = append(out, t)
		}
	}
	return out
}

// stripRegionSuffix removes one trailing region code from s, if present and
// recognised. It reports the remaining name, the code, and whether it matched.
func stripRegionSuffix(s string) (rest, region string, ok bool) {
	for _, re := range []*regexp.Regexp{reParenRegion, reDashRegion, reSpaceRegion} {
		m := re.FindStringSubmatchIndex(s)
		if m == nil {
			continue
		}
		code := s[m[2]:m[3]]
		if !isRegionCode(code) {
			continue
		}
		// m[0] is the start of the whole match; for reSpaceRegion the match
		// begins one rune earlier (the preceding non-space), so cut at the code.
		cut := m[2]
		rest = strings.TrimRight(s[:cut], " -(")
		return strings.TrimSpace(rest), code, true
	}
	return s, "", false
}

func isRegionCode(code string) bool {
	if _, ok := brazilianStates[code]; ok {
		return true
	}
	_, ok := foreignCodes[code]
	return ok
}

// ParseTeamName decomposes a raw dataset team name into its canonical parts.
//
// The pipeline is: normalise dashes → peel off region suffixes → drop leftover
// parentheticals → tokenize → drop stopwords and club-type tokens → join.
// Exact-name overrides in rawNameOverrides run first and win outright, which is
// how genuinely misleading names ("Central SC" is from Pernambuco, not Santa
// Catarina) are corrected.
func ParseTeamName(raw string) ParsedName {
	s := strings.TrimSpace(raw)
	s = strings.NewReplacer("–", "-", "—", "-", " ", " ").Replace(s)
	s = strings.NewReplacer("'", "", "’", "").Replace(s) // O'Higgins -> OHiggins
	s = strings.Join(strings.Fields(s), " ")

	p := ParsedName{Raw: raw}

	if ov, ok := rawNameOverrides[Slug(s)]; ok {
		p.Clean = ov.Display
		p.Base = ov.Base
		p.Region = ov.Region
		return p
	}

	// Peel region suffixes; the outermost (last) one wins, e.g. "Rio Branco - Vn - ES".
	for {
		rest, region, ok := stripRegionSuffix(s)
		if !ok {
			break
		}
		s = rest
		if p.Region == "" {
			p.Region = region
		}
	}

	s = strings.TrimSpace(reParenthetical.ReplaceAllString(s, ""))
	p.Clean = s

	// Overrides are consulted a second time now that the region suffix and any
	// parentheticals are gone, so one entry covers every spelling of a club's
	// legal name ("Boavista Sport Club (antigo ...) - RJ" and "Boavista - RJ").
	if ov, ok := rawNameOverrides[Slug(s)]; ok {
		p.Base = ov.Base
		if p.Region == "" {
			p.Region = ov.Region
		}
		return p
	}

	toks := tokenize(s)
	kept := make([]string, 0, len(toks))
	for _, t := range toks {
		if nameStopwords[t] || clubTypeTokens[t] {
			continue
		}
		kept = append(kept, t)
	}
	if len(kept) == 0 { // e.g. a name made entirely of club-type words
		kept = toks
	}
	// Drop single-letter initials ("Parnahyba S.c", "Serra F. C."), unless the
	// whole name is initials ("A.b.c." is ABC, "C.r.b." is CRB).
	if len(kept) > 1 {
		trimmed := make([]string, 0, len(kept))
		for _, t := range kept {
			if len(t) == 1 && t[0] >= 'a' && t[0] <= 'z' {
				continue
			}
			trimmed = append(trimmed, t)
		}
		if len(trimmed) > 0 {
			kept = trimmed
		}
	}
	base := strings.Join(kept, "")

	if a, ok := baseAliases[base]; ok {
		base = a.Base
		p.DefaultRegion = a.Region
	}
	p.Base = base
	return p
}

// TeamID composes the canonical identifier for a club.
func TeamID(base, region string) string {
	if region == "" {
		return base
	}
	return base + "-" + strings.ToLower(region)
}

// RegionName expands a region code to a human-readable state or country name.
func RegionName(code string) string {
	if v, ok := brazilianStates[code]; ok {
		return v
	}
	if v, ok := foreignCodes[code]; ok {
		return v
	}
	return code
}

// IsBrazilianRegion reports whether code is a Brazilian federative unit.
func IsBrazilianRegion(code string) bool {
	_, ok := brazilianStates[code]
	return ok
}
