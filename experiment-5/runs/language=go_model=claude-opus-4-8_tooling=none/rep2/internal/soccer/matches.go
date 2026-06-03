// matches.go implements match search and head-to-head queries.
package soccer

import (
	"sort"
	"strings"
	"time"
)

// MatchFilter describes the criteria for SearchMatches. Empty fields are
// ignored. Team and Opponent are matched against both home and away sides
// using normalized team-name matching.
type MatchFilter struct {
	Team        string // any team in the match (home or away)
	Opponent    string // restrict to matches that also involve this team
	Venue       string // "home", "away" or "" — interpreted relative to Team
	Competition string
	Season      int
	DateFrom    time.Time
	DateTo      time.Time
	Limit       int // 0 = no limit
}

// SearchMatches returns the matches satisfying the filter, most recent first.
func (s *Store) SearchMatches(f MatchFilter) []Match {
	var out []Match
	for _, m := range s.Matches {
		if !f.matches(m) {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool {
		return matchAfter(out[i], out[j])
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func (f MatchFilter) matches(m Match) bool {
	if f.Competition != "" && !strings.EqualFold(m.Competition, f.Competition) {
		return false
	}
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	if !f.DateFrom.IsZero() && (!m.HasDate || m.Date.Before(f.DateFrom)) {
		return false
	}
	if !f.DateTo.IsZero() && (!m.HasDate || m.Date.After(f.DateTo)) {
		return false
	}

	if f.Team != "" {
		homeHit := TeamMatches(m.HomeRaw, f.Team)
		awayHit := TeamMatches(m.AwayRaw, f.Team)
		switch strings.ToLower(f.Venue) {
		case "home":
			if !homeHit {
				return false
			}
		case "away":
			if !awayHit {
				return false
			}
		default:
			if !homeHit && !awayHit {
				return false
			}
		}
	}

	if f.Opponent != "" {
		if !TeamMatches(m.HomeRaw, f.Opponent) && !TeamMatches(m.AwayRaw, f.Opponent) {
			return false
		}
		// when both Team and Opponent are set, ensure they are on opposite sides
		if f.Team != "" {
			if !oppositeSides(m, f.Team, f.Opponent) {
				return false
			}
		}
	}
	return true
}

func oppositeSides(m Match, a, b string) bool {
	aHome, aAway := TeamMatches(m.HomeRaw, a), TeamMatches(m.AwayRaw, a)
	bHome, bAway := TeamMatches(m.HomeRaw, b), TeamMatches(m.AwayRaw, b)
	return (aHome && bAway) || (aAway && bHome)
}

// matchAfter reports whether match x is more recent than y (for descending
// sort). Dated matches sort before undated ones.
func matchAfter(x, y Match) bool {
	if x.HasDate != y.HasDate {
		return x.HasDate
	}
	if x.HasDate && y.HasDate && !x.Date.Equal(y.Date) {
		return x.Date.After(y.Date)
	}
	return x.Season > y.Season
}

// HeadToHead summarises the all-time record between two teams.
type HeadToHead struct {
	TeamA   string
	TeamB   string
	Matches []Match
	AWins   int
	BWins   int
	Draws   int
	AGoals  int
	BGoals  int
}

// HeadToHead computes the record between teamA and teamB across all competitions.
func (s *Store) HeadToHead(teamA, teamB string) HeadToHead {
	h := HeadToHead{TeamA: teamA, TeamB: teamB}
	for _, m := range s.Matches {
		if !oppositeSides(m, teamA, teamB) {
			continue
		}
		h.Matches = append(h.Matches, m)
		if !m.HasScore {
			continue
		}
		aHome := TeamMatches(m.HomeRaw, teamA)
		var aGoals, bGoals int
		if aHome {
			aGoals, bGoals = m.HomeGoals, m.AwayGoals
		} else {
			aGoals, bGoals = m.AwayGoals, m.HomeGoals
		}
		h.AGoals += aGoals
		h.BGoals += bGoals
		switch {
		case aGoals > bGoals:
			h.AWins++
		case bGoals > aGoals:
			h.BWins++
		default:
			h.Draws++
		}
	}
	sort.SliceStable(h.Matches, func(i, j int) bool {
		return matchAfter(h.Matches[i], h.Matches[j])
	})
	return h
}
