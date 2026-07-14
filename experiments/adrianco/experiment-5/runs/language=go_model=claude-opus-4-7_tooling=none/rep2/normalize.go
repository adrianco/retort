package main

import (
	"strings"
)

// foldRune maps an accented Latin character to its ASCII equivalent.
// Covers the characters that appear in Brazilian Portuguese plus a handful
// of others seen in the FIFA dataset (German, French, Spanish, etc.).
func foldRune(r rune) rune {
	switch r {
	case 'á', 'à', 'â', 'ã', 'ä', 'å', 'ā', 'ă', 'ą':
		return 'a'
	case 'Á', 'À', 'Â', 'Ã', 'Ä', 'Å', 'Ā', 'Ă', 'Ą':
		return 'A'
	case 'ç', 'ć', 'č':
		return 'c'
	case 'Ç', 'Ć', 'Č':
		return 'C'
	case 'é', 'è', 'ê', 'ë', 'ē', 'ė', 'ę':
		return 'e'
	case 'É', 'È', 'Ê', 'Ë', 'Ē', 'Ė', 'Ę':
		return 'E'
	case 'í', 'ì', 'î', 'ï', 'ī', 'į':
		return 'i'
	case 'Í', 'Ì', 'Î', 'Ï', 'Ī', 'Į':
		return 'I'
	case 'ñ', 'ń':
		return 'n'
	case 'Ñ', 'Ń':
		return 'N'
	case 'ó', 'ò', 'ô', 'õ', 'ö', 'ø', 'ō':
		return 'o'
	case 'Ó', 'Ò', 'Ô', 'Õ', 'Ö', 'Ø', 'Ō':
		return 'O'
	case 'ś', 'š':
		return 's'
	case 'Ś', 'Š':
		return 'S'
	case 'ú', 'ù', 'û', 'ü', 'ū', 'ů':
		return 'u'
	case 'Ú', 'Ù', 'Û', 'Ü', 'Ū', 'Ů':
		return 'U'
	case 'ý', 'ÿ':
		return 'y'
	case 'Ý', 'Ÿ':
		return 'Y'
	case 'ž', 'ź', 'ż':
		return 'z'
	case 'Ž', 'Ź', 'Ż':
		return 'Z'
	}
	return r
}

func stripDiacritics(s string) string {
	out := make([]rune, 0, len(s))
	for _, r := range s {
		out = append(out, foldRune(r))
	}
	return string(out)
}

// stateSuffixes lists Brazilian state abbreviations commonly appended to
// team names (e.g. "Palmeiras-SP", "Flamengo - RJ").
var stateSuffixes = []string{
	"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
	"MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
	"RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

// NormalizeTeam returns a canonical key for a team name so that "Palmeiras",
// "Palmeiras-SP", "PALMEIRAS - SP", and "palmeiras" all match.
func NormalizeTeam(name string) string {
	if name == "" {
		return ""
	}
	s := stripDiacritics(name)
	s = strings.ToLower(s)
	s = strings.TrimSpace(s)

	// Country codes inside parens: "Nacional (URU)" -> "nacional".
	if i := strings.Index(s, "("); i >= 0 {
		s = strings.TrimSpace(s[:i])
	}

	// Remove trailing state suffix forms repeatedly: " - SP", "-SP", " SP".
	for {
		trimmed := false
		for _, st := range stateSuffixes {
			low := strings.ToLower(st)
			for _, sep := range []string{" - " + low, "-" + low, " " + low} {
				if strings.HasSuffix(s, sep) {
					s = strings.TrimSuffix(s, sep)
					trimmed = true
					break
				}
			}
			if trimmed {
				break
			}
		}
		if !trimmed {
			break
		}
		s = strings.TrimSpace(s)
	}

	// Drop common qualifiers/words that vary across data sets.
	for _, drop := range []string{
		" futebol clube", " esporte clube", " sport club",
		" sociedade esportiva", " clube de regatas do",
		" associacao atletica", " atletico clube",
		" f.c.", " s.c.", " e.c.",
	} {
		s = strings.ReplaceAll(s, drop, " ")
	}

	// Collapse whitespace.
	fields := strings.Fields(s)
	s = strings.Join(fields, " ")
	return s
}

// TeamMatches reports whether `query` and `name` refer to the same team after
// normalisation. Substring matching is supported, so "Flamengo" matches
// "Flamengo-RJ" or "Clube de Regatas do Flamengo".
func TeamMatches(query, name string) bool {
	if query == "" || name == "" {
		return false
	}
	q := NormalizeTeam(query)
	n := NormalizeTeam(name)
	if q == "" || n == "" {
		return false
	}
	if q == n {
		return true
	}
	if strings.Contains(n, q) || strings.Contains(q, n) {
		return true
	}
	return false
}

// ContainsFold is case- and accent-insensitive substring matching.
func ContainsFold(haystack, needle string) bool {
	if needle == "" {
		return true
	}
	h := strings.ToLower(stripDiacritics(haystack))
	n := strings.ToLower(stripDiacritics(needle))
	return strings.Contains(h, n)
}
