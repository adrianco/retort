// Package soccer implements the in-memory knowledge graph that backs the
// Brazilian Soccer MCP server.
//
// Context
// -------
// This file (normalize.go) is responsible for *team name normalization*. The
// provided Kaggle datasets refer to the same club using several conventions:
//
//	"Palmeiras-SP"      (state suffix, no spaces)
//	"América - MG"      (state suffix, spaced hyphen)
//	"Nacional (URU)"    (country code in parentheses)
//	"Flamengo"          (bare name)
//	"São Paulo"         (accented characters / UTF-8)
//
// To answer questions like "Compare Palmeiras and Santos head-to-head" we must
// be able to recognise that all of the spellings above map to a single canonical
// club. Normalization happens in two layers:
//
//   - CanonicalName: a human friendly display name with state/country suffixes
//     stripped and whitespace collapsed (e.g. "Palmeiras", "América").
//   - MatchKey: an aggressively folded key used purely for comparison. It is
//     lower-cased, accent-folded and stripped of punctuation so that
//     "São Paulo", "sao-paulo" and "Sao Paulo FC" all share a comparable root.
//
// Query matching (see query.go) compares MatchKeys with both exact and
// substring semantics so that a short user query ("Flamengo") matches a longer
// stored name ("Flamengo RJ") and vice versa.
package soccer

import (
	"regexp"
	"strings"
)

// stateSuffix matches a trailing Brazilian state or short country code attached
// with a hyphen, e.g. "-SP", " - MG", "-EQU".
var stateSuffix = regexp.MustCompile(`\s*-\s*[A-Z]{2,3}\s*$`)

// parenSuffix matches a trailing parenthesised country/federation code, e.g.
// "(URU)", "(EQU)", "(ARG)".
var parenSuffix = regexp.MustCompile(`\s*\([A-Za-z]{2,5}\)\s*$`)

// multiSpace collapses runs of whitespace into a single space.
var multiSpace = regexp.MustCompile(`\s+`)

// CanonicalName returns a clean, display friendly club name. It removes trailing
// state suffixes ("-SP"), parenthesised country codes ("(URU)") and collapses
// internal whitespace, while preserving the original accents and casing.
func CanonicalName(raw string) string {
	name := strings.TrimSpace(raw)
	// Strip suffixes repeatedly: a few records carry both a state hyphen and a
	// parenthesised code.
	for {
		before := name
		name = parenSuffix.ReplaceAllString(name, "")
		name = stateSuffix.ReplaceAllString(name, "")
		name = strings.TrimSpace(name)
		if name == before {
			break
		}
	}
	name = multiSpace.ReplaceAllString(name, " ")
	if name == "" {
		// Fall back to the trimmed raw value rather than returning empty.
		return strings.TrimSpace(raw)
	}
	return name
}

// foldRune maps a single accented rune to its ASCII base. Returns the rune
// unchanged when no folding is required.
func foldRune(r rune) rune {
	switch r {
	case 'á', 'à', 'â', 'ã', 'ä', 'å', 'Á', 'À', 'Â', 'Ã', 'Ä', 'Å':
		return 'a'
	case 'é', 'è', 'ê', 'ë', 'É', 'È', 'Ê', 'Ë':
		return 'e'
	case 'í', 'ì', 'î', 'ï', 'Í', 'Ì', 'Î', 'Ï':
		return 'i'
	case 'ó', 'ò', 'ô', 'õ', 'ö', 'Ó', 'Ò', 'Ô', 'Õ', 'Ö':
		return 'o'
	case 'ú', 'ù', 'û', 'ü', 'Ú', 'Ù', 'Û', 'Ü':
		return 'u'
	case 'ç', 'Ç':
		return 'c'
	case 'ñ', 'Ñ':
		return 'n'
	case 'ý', 'ÿ', 'Ý':
		return 'y'
	}
	return r
}

// FoldAccents replaces accented Latin characters with their ASCII base form.
func FoldAccents(s string) string {
	return strings.Map(foldRune, s)
}

// MatchKey produces the comparison key for a team name. It canonicalises the
// name, folds accents, lower-cases it and removes every character that is not a
// letter or digit (spaces included). The result is a compact token suitable for
// exact and substring comparison.
func MatchKey(raw string) string {
	canon := FoldAccents(CanonicalName(raw))
	var b strings.Builder
	b.Grow(len(canon))
	for _, r := range strings.ToLower(canon) {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			b.WriteRune(r)
		}
	}
	return b.String()
}

// NameMatches reports whether a user supplied query refers to the given stored
// team name. It is deliberately permissive: it returns true on an exact key
// match or when one key is a substring of the other. The query must be at least
// three characters once folded to avoid spurious substring hits.
func NameMatches(query, stored string) bool {
	q := MatchKey(query)
	s := MatchKey(stored)
	if q == "" || s == "" {
		return false
	}
	if q == s {
		return true
	}
	if len(q) < 3 {
		return false
	}
	return strings.Contains(s, q) || strings.Contains(q, s)
}
