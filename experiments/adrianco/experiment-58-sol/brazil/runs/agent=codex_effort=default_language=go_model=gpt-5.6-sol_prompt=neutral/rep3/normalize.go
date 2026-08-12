package main

import (
	"regexp"
	"strings"
	"unicode"
)

var (
	stateSuffix = regexp.MustCompile(`(?i)\s*-\s*(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$`)
	parenthetic = regexp.MustCompile(`\s*\([^)]*\)\s*`)
	nonWord     = regexp.MustCompile(`[^a-z0-9]+`)
)

var accentReplacer = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u", "ç", "c",
)

var teamAliases = map[string]string{
	"athletico paranaense": "athletico pr", "atletico paranaense": "athletico pr",
	"club athletico paranaense": "athletico pr", "atletico pr": "athletico pr",
	"atletico mineiro": "atletico mg", "clube atletico mineiro": "atletico mg",
	"america mineiro": "america mg", "america futebol clube": "america mg",
	"corinthians paulista": "corinthians", "sport club corinthians paulista": "corinthians",
	"sao paulo fc": "sao paulo", "sao paulo futebol clube": "sao paulo",
	"fluminense fc": "fluminense", "fluminense football club": "fluminense",
	"flamengo rj": "flamengo", "clube de regatas do flamengo": "flamengo",
	"vasco da gama": "vasco", "club de regatas vasco da gama": "vasco",
	"gremio porto alegre": "gremio", "gremio foot ball porto alegrense": "gremio",
	"internacional porto alegre": "internacional", "sport club internacional": "internacional",
	"botafogo rj": "botafogo", "botafogo de futebol e regatas": "botafogo",
	"red bull bragantino": "bragantino", "rb bragantino": "bragantino",
}

func fold(s string) string {
	s = strings.ToLower(strings.TrimSpace(strings.TrimPrefix(s, "\ufeff")))
	s = accentReplacer.Replace(s)
	return strings.TrimSpace(s)
}

// normalizeTeam creates a comparison key while preserving the original name
// in responses. It removes state suffixes and common long-form variations.
func normalizeTeam(s string) string {
	raw := strings.TrimSpace(s)
	// A few short club names are genuinely ambiguous across states. Preserve
	// their state identity while still allowing the familiar long-form aliases.
	foldedRaw := nonWord.ReplaceAllString(fold(raw), " ")
	foldedRaw = strings.Join(strings.Fields(foldedRaw), " ")
	stateAware := map[string]string{
		"atletico mg": "atletico mg", "atletico pr": "athletico pr",
		"athletico pr": "athletico pr", "america mg": "america mg",
		"america rn": "america rn", "botafogo rj": "botafogo",
		"botafogo pb": "botafogo pb", "botafogo sp": "botafogo sp",
	}
	if key, ok := stateAware[foldedRaw]; ok {
		return key
	}
	s = stateSuffix.ReplaceAllString(raw, "")
	s = parenthetic.ReplaceAllString(s, " ")
	s = nonWord.ReplaceAllString(fold(s), " ")
	s = strings.Join(strings.Fields(s), " ")
	if alias, ok := teamAliases[s]; ok {
		return alias
	}
	return s
}

func cleanTeamName(s string) string {
	s = strings.TrimSpace(stateSuffix.ReplaceAllString(strings.TrimSpace(s), ""))
	return strings.Join(strings.Fields(s), " ")
}

func displayTeam(s string) string {
	switch normalizeTeam(s) {
	case "atletico mg":
		return "Atlético Mineiro"
	case "athletico pr":
		return "Athletico Paranaense"
	case "america mg":
		return "América Mineiro"
	case "america rn":
		return "América-RN"
	case "botafogo pb":
		return "Botafogo-PB"
	case "botafogo sp":
		return "Botafogo-SP"
	default:
		return cleanTeamName(s)
	}
}

func fuzzyEqual(a, b string) bool {
	a, b = normalizeTeam(a), normalizeTeam(b)
	if a == "" || b == "" {
		return false
	}
	return a == b || strings.Contains(a, b) || strings.Contains(b, a)
}

func fuzzyText(value, query string) bool {
	v, q := fold(value), fold(query)
	return q == "" || strings.Contains(v, q)
}

func titleWords(s string) string {
	return strings.Map(func(r rune) rune {
		if unicode.IsControl(r) {
			return -1
		}
		return r
	}, strings.TrimSpace(s))
}
