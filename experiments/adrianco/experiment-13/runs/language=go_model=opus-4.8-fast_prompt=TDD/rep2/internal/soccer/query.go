package soccer

import (
	"sort"
	"time"
)

// MatchFilter selects matches for SearchMatches. Zero-valued fields are
// ignored, so an empty filter matches every match.
type MatchFilter struct {
	Team        string // matches either home or away
	Opponent    string // combined with Team: the other side of the fixture
	HomeTeam    string // matches the home side only
	AwayTeam    string // matches the away side only
	Competition string
	Season      int
	SeasonFrom  int
	SeasonTo    int
	DateFrom    time.Time
	DateTo      time.Time
	Limit       int // 0 = no limit
}

// SearchMatches returns the matches satisfying the filter, sorted most-recent
// first (matches without a date sort last). Limit, if positive, caps the
// number returned.
func (kb *KB) SearchMatches(f MatchFilter) []Match {
	var out []Match
	for _, m := range kb.Matches {
		if !matchPasses(m, f) {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool {
		return out[i].Date.After(out[j].Date)
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func matchPasses(m Match, f MatchFilter) bool {
	if f.Team != "" {
		if !TeamsMatch(m.HomeTeam, f.Team) && !TeamsMatch(m.AwayTeam, f.Team) {
			return false
		}
	}
	if f.Opponent != "" {
		if !TeamsMatch(m.HomeTeam, f.Opponent) && !TeamsMatch(m.AwayTeam, f.Opponent) {
			return false
		}
	}
	if f.HomeTeam != "" && !TeamsMatch(m.HomeTeam, f.HomeTeam) {
		return false
	}
	if f.AwayTeam != "" && !TeamsMatch(m.AwayTeam, f.AwayTeam) {
		return false
	}
	if f.Competition != "" && !competitionMatches(m.Competition, f.Competition) {
		return false
	}
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	if f.SeasonFrom != 0 && m.Season < f.SeasonFrom {
		return false
	}
	if f.SeasonTo != 0 && m.Season > f.SeasonTo {
		return false
	}
	if !f.DateFrom.IsZero() && (!m.HasDate || m.Date.Before(f.DateFrom)) {
		return false
	}
	if !f.DateTo.IsZero() && (!m.HasDate || m.Date.After(f.DateTo)) {
		return false
	}
	return true
}

// competitionMatches reports whether a match's competition satisfies the
// requested competition filter, tolerating accent and case differences.
func competitionMatches(have, want string) bool {
	return NormalizeTeam(have) == NormalizeTeam(want)
}
