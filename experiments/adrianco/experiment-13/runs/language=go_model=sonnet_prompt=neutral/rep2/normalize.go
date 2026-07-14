package main

import (
	"regexp"
	"strings"
)

var (
	stateHyphenRe = regexp.MustCompile(`\s*-\s*[A-Z]{2,3}$`)
	stateSpaceRe  = regexp.MustCompile(`\s+-\s+[A-Z]{2,3}$`)
	parenRe       = regexp.MustCompile(`\s*\([^)]*\)`)
)

// stripAccents replaces accented characters with their ASCII equivalents.
func stripAccents(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		switch r {
		case 'à', 'á', 'â', 'ã', 'ä', 'å':
			b.WriteByte('a')
		case 'è', 'é', 'ê', 'ë':
			b.WriteByte('e')
		case 'ì', 'í', 'î', 'ï':
			b.WriteByte('i')
		case 'ò', 'ó', 'ô', 'õ', 'ö':
			b.WriteByte('o')
		case 'ù', 'ú', 'û', 'ü':
			b.WriteByte('u')
		case 'ç':
			b.WriteByte('c')
		case 'ñ':
			b.WriteByte('n')
		case 'À', 'Á', 'Â', 'Ã', 'Ä', 'Å':
			b.WriteByte('A')
		case 'È', 'É', 'Ê', 'Ë':
			b.WriteByte('E')
		case 'Ì', 'Í', 'Î', 'Ï':
			b.WriteByte('I')
		case 'Ò', 'Ó', 'Ô', 'Õ', 'Ö':
			b.WriteByte('O')
		case 'Ù', 'Ú', 'Û', 'Ü':
			b.WriteByte('U')
		case 'Ç':
			b.WriteByte('C')
		case 'Ñ':
			b.WriteByte('N')
		default:
			b.WriteRune(r)
		}
	}
	return b.String()
}

// normalizeTeam returns a canonical lowercase form of a team name for matching.
func normalizeTeam(name string) string {
	name = parenRe.ReplaceAllString(name, "")
	name = stateSpaceRe.ReplaceAllString(name, "")
	name = stateHyphenRe.ReplaceAllString(name, "")
	name = strings.TrimSpace(name)
	name = strings.ToLower(stripAccents(name))
	name = strings.Join(strings.Fields(name), " ")
	return name
}

// teamMatchesQuery returns true if teamName contains the query (after normalization).
func teamMatchesQuery(teamName, query string) bool {
	normTeam := normalizeTeam(teamName)
	normQuery := normalizeTeam(query)
	if normQuery == "" || normTeam == "" {
		return false
	}
	return strings.Contains(normTeam, normQuery) || strings.Contains(normQuery, normTeam)
}

// normalizeTeamKey returns a normalized team name suitable for grouping (statistics,
// standings). Unlike normalizeTeam, it retains state suffixes so that "Atletico-MG"
// and "Atletico-GO" remain distinct entries.
func normalizeTeamKey(name string) string {
	name = parenRe.ReplaceAllString(name, "")
	name = strings.TrimSpace(name)
	name = strings.ToLower(stripAccents(name))
	name = strings.Join(strings.Fields(name), " ")
	return name
}

// competitionMatchesQuery returns true if competition name matches the query.
func competitionMatchesQuery(comp, query string) bool {
	c := strings.ToLower(stripAccents(comp))
	q := strings.ToLower(stripAccents(query))
	return strings.Contains(c, q) || strings.Contains(q, c)
}
