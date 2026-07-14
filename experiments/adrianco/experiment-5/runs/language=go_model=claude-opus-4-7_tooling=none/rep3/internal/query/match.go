package query

import (
	"sort"
	"strings"
	"time"

	"github.com/adrian/brazilian-soccer-mcp/internal/data"
	"github.com/adrian/brazilian-soccer-mcp/internal/normalize"
)

// MatchFilter describes search criteria for finding matches.
type MatchFilter struct {
	Team        string // any team (home or away)
	HomeTeam    string
	AwayTeam    string
	Opponent    string // pair with Team: find Team vs Opponent
	Season      int
	Competition string
	From        time.Time
	To          time.Time
	Limit       int
}

// FindMatches returns matches matching the filter, sorted most-recent first.
func FindMatches(ds *data.Dataset, f MatchFilter) []data.Match {
	out := make([]data.Match, 0)
	for _, m := range ds.Matches {
		if !matchPasses(m, f) {
			continue
		}
		out = append(out, m)
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].Date.After(out[j].Date)
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func matchPasses(m data.Match, f MatchFilter) bool {
	if f.Competition != "" && !strings.EqualFold(string(m.Competition), f.Competition) &&
		!strings.Contains(strings.ToLower(string(m.Competition)), strings.ToLower(f.Competition)) {
		return false
	}
	if f.Season > 0 && m.Season != f.Season {
		return false
	}
	if !f.From.IsZero() && m.Date.Before(f.From) {
		return false
	}
	if !f.To.IsZero() && m.Date.After(f.To) {
		return false
	}
	if f.HomeTeam != "" && !normalize.Matches(m.HomeTeam, f.HomeTeam) {
		return false
	}
	if f.AwayTeam != "" && !normalize.Matches(m.AwayTeam, f.AwayTeam) {
		return false
	}
	if f.Team != "" {
		if !normalize.Matches(m.HomeTeam, f.Team) && !normalize.Matches(m.AwayTeam, f.Team) {
			return false
		}
	}
	if f.Opponent != "" {
		if !normalize.Matches(m.HomeTeam, f.Opponent) && !normalize.Matches(m.AwayTeam, f.Opponent) {
			return false
		}
	}
	return true
}

// HeadToHead reports cumulative results between two teams across all data.
type HeadToHead struct {
	TeamA      string
	TeamB      string
	Matches    []data.Match
	TotalGames int
	AWins      int
	BWins      int
	Draws      int
	AGoals     int
	BGoals     int
}

// ComputeHeadToHead returns aggregated head-to-head between two teams.
func ComputeHeadToHead(ds *data.Dataset, a, b string) HeadToHead {
	h := HeadToHead{TeamA: a, TeamB: b}
	for _, m := range ds.Matches {
		var aHome, aAway, bHome, bAway bool
		aHome = normalize.Matches(m.HomeTeam, a)
		aAway = normalize.Matches(m.AwayTeam, a)
		bHome = normalize.Matches(m.HomeTeam, b)
		bAway = normalize.Matches(m.AwayTeam, b)
		if !((aHome && bAway) || (aAway && bHome)) {
			continue
		}
		h.Matches = append(h.Matches, m)
		h.TotalGames++
		var aGoals, bGoals int
		if aHome {
			aGoals, bGoals = m.HomeGoal, m.AwayGoal
		} else {
			aGoals, bGoals = m.AwayGoal, m.HomeGoal
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
	sort.Slice(h.Matches, func(i, j int) bool {
		return h.Matches[i].Date.After(h.Matches[j].Date)
	})
	return h
}

// BiggestWins returns the matches with the largest goal margin (descending),
// optionally restricted to a competition.
func BiggestWins(ds *data.Dataset, competition string, limit int) []data.Match {
	type scored struct {
		m      data.Match
		margin int
	}
	var list []scored
	for _, m := range ds.Matches {
		if competition != "" &&
			!strings.EqualFold(string(m.Competition), competition) &&
			!strings.Contains(strings.ToLower(string(m.Competition)), strings.ToLower(competition)) {
			continue
		}
		margin := m.HomeGoal - m.AwayGoal
		if margin < 0 {
			margin = -margin
		}
		list = append(list, scored{m, margin})
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].margin == list[j].margin {
			return list[i].m.HomeGoal+list[i].m.AwayGoal > list[j].m.HomeGoal+list[j].m.AwayGoal
		}
		return list[i].margin > list[j].margin
	})
	if limit == 0 {
		limit = 10
	}
	if len(list) > limit {
		list = list[:limit]
	}
	out := make([]data.Match, len(list))
	for i, s := range list {
		out[i] = s.m
	}
	return out
}
