// Context: Brazilian Soccer MCP Server.
// File: dedup.go
// Purpose: Deduplicate matches that appear in more than one source file. The
// datasets overlap heavily — the same Brasileirão fixture can appear in the
// historical file, the modern file and the extended-statistics file (labelled
// "Serie A"). Without dedup, standings, head-to-head and aggregate statistics
// are inflated several-fold. Two records are considered the same fixture when
// they share a competition family, season and home/away pairing.
package soccer

import "strings"

// normalizeCompetitionFamily collapses competition labels into a family key so
// that the extended dataset's "Serie A" folds together with "Brasileirão".
// Lower divisions (Serie B/C) and other competitions keep distinct families.
func normalizeCompetitionFamily(comp string) string {
	c := strings.ToLower(removeAccents(strings.TrimSpace(comp)))
	switch {
	case c == "serie a" || strings.Contains(c, "brasileir"):
		return "brasileirao"
	case strings.Contains(c, "copa do brasil"):
		return "copa do brasil"
	case strings.Contains(c, "libertadores"):
		return "libertadores"
	default:
		return c
	}
}

// canonicalBRCompetition maps the extended-dataset tournament labels onto the
// canonical competition names used elsewhere, leaving lower divisions intact.
func canonicalBRCompetition(tournament string) string {
	switch normalizeCompetitionFamily(tournament) {
	case "brasileirao":
		return CompBrasileirao
	case "copa do brasil":
		return CompCopaDoBrasil
	case "libertadores":
		return CompLibertadores
	default:
		return tournament
	}
}

// dedupKey identifies a fixture independently of which file it came from.
func dedupKey(m Match) string {
	return strings.Join([]string{
		normalizeCompetitionFamily(m.Competition),
		itoa(m.Season),
		NormalizeTeamName(m.HomeTeam),
		NormalizeTeamName(m.AwayTeam),
	}, "|")
}

func itoa(i int) string {
	if i == 0 {
		return ""
	}
	// Small, allocation-light integer to string for non-negative seasons.
	const digits = "0123456789"
	if i < 0 {
		return "-" + itoa(-i)
	}
	var buf [20]byte
	pos := len(buf)
	for i > 0 {
		pos--
		buf[pos] = digits[i%10]
		i /= 10
	}
	return string(buf[pos:])
}

// richness scores how much detail a record carries, used to choose which of
// several duplicates to keep.
func richness(m Match) int {
	score := 0
	if m.Round != "" {
		score += 2
	}
	if m.Stage != "" {
		score += 2
	}
	if m.HasDate {
		score++
	}
	return score
}

// dedupeMatches removes duplicate fixtures across source files. Matches that
// cannot be reliably keyed (no score, or missing season/teams) are passed
// through untouched. Among duplicates, the record carrying the most detail is
// retained; original ordering is otherwise preserved.
func dedupeMatches(matches []Match) []Match {
	out := make([]Match, 0, len(matches))
	index := map[string]int{} // dedup key -> position in out
	for _, m := range matches {
		if !m.HasScore || m.Season == 0 || m.HomeTeam == "" || m.AwayTeam == "" {
			out = append(out, m)
			continue
		}
		key := dedupKey(m)
		if pos, ok := index[key]; ok {
			if richness(m) > richness(out[pos]) {
				out[pos] = m
			}
			continue
		}
		index[key] = len(out)
		out = append(out, m)
	}
	return out
}
