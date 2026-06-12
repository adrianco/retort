package soccer

import "sort"

// sourcePreference orders datasets when several cover the same
// competition+season with an equal number of matches. Lower index wins.
var sourcePreference = map[string]int{
	"Brasileirao_Matches.csv":        0,
	"novo_campeonato_brasileiro.csv": 1,
	"Libertadores_Matches.csv":       2,
	"Brazilian_Cup_Matches.csv":      3,
	"BR-Football-Dataset.csv":        4,
}

// DedupedMatches returns the matches selected by f with overlapping datasets
// collapsed: for each (competition, season) group covered by more than one
// source file, only the single most complete source's matches are kept (ties
// broken by sourcePreference). Groups covered by a single source are returned
// unchanged. This removes the duplication that arises because several bundled
// datasets cover the same competition and season.
func (kb *KB) DedupedMatches(f MatchFilter) []Match {
	type key struct {
		comp   string
		season int
	}
	groups := map[key]map[string][]Match{}
	for _, m := range kb.SearchMatches(f) {
		k := key{NormalizeTeam(m.Competition), m.Season}
		if groups[k] == nil {
			groups[k] = map[string][]Match{}
		}
		groups[k][m.Source] = append(groups[k][m.Source], m)
	}
	var out []Match
	for _, bySource := range groups {
		out = append(out, bySource[pickSource(bySource)]...)
	}
	return out
}

// Standings computes a league table for a competition and season. Because
// several datasets overlap for the same competition+season, the table is
// computed from the single source that contains the most matches for that
// competition+season (ties broken by sourcePreference). This avoids
// double-counting fixtures present in multiple files. The result is sorted by
// points, then goal difference, then goals for.
func (kb *KB) Standings(competition string, season int) []TeamRecord {
	matches := kb.SearchMatches(MatchFilter{Competition: competition, Season: season})

	// Group by source and choose the most complete one.
	bySource := map[string][]Match{}
	for _, m := range matches {
		bySource[m.Source] = append(bySource[m.Source], m)
	}
	best := pickSource(bySource)

	// Aggregate each team's record from the chosen source.
	type agg struct {
		display string
		rec     TeamRecord
	}
	byTeam := map[string]*agg{}
	record := func(rawTeam string, gf, ga int) {
		key := NormalizeTeam(rawTeam)
		a := byTeam[key]
		if a == nil {
			a = &agg{display: rawTeam, rec: TeamRecord{Team: rawTeam}}
			byTeam[key] = a
		}
		a.rec.Matches++
		a.rec.GoalsFor += gf
		a.rec.GoalsAgainst += ga
		switch {
		case gf > ga:
			a.rec.Wins++
		case gf < ga:
			a.rec.Losses++
		default:
			a.rec.Draws++
		}
	}
	for _, m := range bySource[best] {
		if !m.HasScore {
			continue
		}
		record(m.HomeTeam, m.HomeGoals, m.AwayGoals)
		record(m.AwayTeam, m.AwayGoals, m.HomeGoals)
	}

	out := make([]TeamRecord, 0, len(byTeam))
	for _, a := range byTeam {
		out = append(out, a.rec)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Points() != out[j].Points() {
			return out[i].Points() > out[j].Points()
		}
		if out[i].GoalDiff() != out[j].GoalDiff() {
			return out[i].GoalDiff() > out[j].GoalDiff()
		}
		if out[i].GoalsFor != out[j].GoalsFor {
			return out[i].GoalsFor > out[j].GoalsFor
		}
		return out[i].Team < out[j].Team
	})
	return out
}

// pickSource returns the source key holding the most matches, breaking ties
// via sourcePreference (and finally the source name for determinism).
func pickSource(bySource map[string][]Match) string {
	best := ""
	for src, ms := range bySource {
		if best == "" {
			best = src
			continue
		}
		switch {
		case len(ms) > len(bySource[best]):
			best = src
		case len(ms) == len(bySource[best]):
			if sourceRank(src) < sourceRank(best) ||
				(sourceRank(src) == sourceRank(best) && src < best) {
				best = src
			}
		}
	}
	return best
}

func sourceRank(src string) int {
	if r, ok := sourcePreference[src]; ok {
		return r
	}
	return 1 << 30
}

// CompetitionStatsResult aggregates result/goal statistics over a set of
// matches.
type CompetitionStatsResult struct {
	Matches    int
	TotalGoals int
	HomeWins   int
	AwayWins   int
	Draws      int
}

// AvgGoals returns the mean goals per match, or 0 when there are no matches.
func (c CompetitionStatsResult) AvgGoals() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.TotalGoals) / float64(c.Matches)
}

// HomeWinRate returns the percentage of matches won by the home side (0–100).
func (c CompetitionStatsResult) HomeWinRate() float64 {
	if c.Matches == 0 {
		return 0
	}
	return 100 * float64(c.HomeWins) / float64(c.Matches)
}

// CompetitionStats aggregates goal and result statistics over the matches
// selected by f (those with a score). Overlapping datasets are deduplicated
// per (competition, season) so match counts and averages are not inflated.
func (kb *KB) CompetitionStats(f MatchFilter) CompetitionStatsResult {
	var cs CompetitionStatsResult
	for _, m := range kb.DedupedMatches(f) {
		if !m.HasScore {
			continue
		}
		cs.Matches++
		cs.TotalGoals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			cs.HomeWins++
		case m.HomeGoals < m.AwayGoals:
			cs.AwayWins++
		default:
			cs.Draws++
		}
	}
	return cs
}

// BiggestWins returns up to n matches with the largest goal margin among those
// selected by f, sorted by margin descending. Fixtures that are duplicated
// across datasets (same teams and score) are collapsed to one entry.
func (kb *KB) BiggestWins(f MatchFilter, n int) []Match {
	matches := kb.DedupedMatches(f)
	seen := map[string]bool{}
	var uniq []Match
	for _, m := range matches {
		if !m.HasScore || m.HomeGoals == m.AwayGoals {
			continue
		}
		key := NormalizeTeam(m.HomeTeam) + "|" + NormalizeTeam(m.AwayTeam) +
			"|" + itoa(m.HomeGoals) + "-" + itoa(m.AwayGoals) + "|" + itoa(m.Season)
		if seen[key] {
			continue
		}
		seen[key] = true
		uniq = append(uniq, m)
	}
	sort.SliceStable(uniq, func(i, j int) bool {
		if margin(uniq[i]) != margin(uniq[j]) {
			return margin(uniq[i]) > margin(uniq[j])
		}
		// Deterministic tiebreaks: more recent first, then by teams.
		if !uniq[i].Date.Equal(uniq[j].Date) {
			return uniq[i].Date.After(uniq[j].Date)
		}
		if uniq[i].HomeTeam != uniq[j].HomeTeam {
			return uniq[i].HomeTeam < uniq[j].HomeTeam
		}
		return uniq[i].AwayTeam < uniq[j].AwayTeam
	})
	if n > 0 && len(uniq) > n {
		uniq = uniq[:n]
	}
	return uniq
}

func margin(m Match) int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}
