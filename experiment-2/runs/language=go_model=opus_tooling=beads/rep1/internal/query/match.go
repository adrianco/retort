package query

import (
	"sort"
	"strings"
	"time"

	"brsoccer/internal/data"
)

type MatchFilter struct {
	Team        string // matches home OR away
	HomeTeam    string
	AwayTeam    string
	VsTeam      string // used with Team to find head-to-head
	Competition string
	Season      int
	From        time.Time
	To          time.Time
	Limit       int
}

func FindMatches(db *data.DB, f MatchFilter) []data.Match {
	out := make([]data.Match, 0, 64)
	for _, m := range db.Matches {
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.Competition != "" && !strings.Contains(strings.ToLower(m.Competition), strings.ToLower(f.Competition)) {
			continue
		}
		if !f.From.IsZero() && m.Date.Before(f.From) {
			continue
		}
		if !f.To.IsZero() && m.Date.After(f.To) {
			continue
		}
		if f.HomeTeam != "" && !data.TeamMatches(m.HomeTeam, f.HomeTeam) {
			continue
		}
		if f.AwayTeam != "" && !data.TeamMatches(m.AwayTeam, f.AwayTeam) {
			continue
		}
		if f.Team != "" {
			if !(data.TeamMatches(m.HomeTeam, f.Team) || data.TeamMatches(m.AwayTeam, f.Team)) {
				continue
			}
		}
		if f.VsTeam != "" {
			if !((data.TeamMatches(m.HomeTeam, f.Team) && data.TeamMatches(m.AwayTeam, f.VsTeam)) ||
				(data.TeamMatches(m.AwayTeam, f.Team) && data.TeamMatches(m.HomeTeam, f.VsTeam))) {
				continue
			}
		}
		out = append(out, m)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

type HeadToHead struct {
	TeamA    string
	TeamB    string
	AWins    int
	BWins    int
	Draws    int
	AGoals   int
	BGoals   int
	Matches  int
	Examples []data.Match
}

func H2H(db *data.DB, a, b string) HeadToHead {
	h := HeadToHead{TeamA: a, TeamB: b}
	ms := FindMatches(db, MatchFilter{Team: a, VsTeam: b})
	h.Matches = len(ms)
	for _, m := range ms {
		aHome := data.TeamMatches(m.HomeTeam, a)
		var ag, bg int
		if aHome {
			ag, bg = m.HomeGoals, m.AwayGoals
		} else {
			ag, bg = m.AwayGoals, m.HomeGoals
		}
		h.AGoals += ag
		h.BGoals += bg
		switch {
		case ag > bg:
			h.AWins++
		case bg > ag:
			h.BWins++
		default:
			h.Draws++
		}
	}
	if len(ms) > 10 {
		h.Examples = ms[:10]
	} else {
		h.Examples = ms
	}
	return h
}
