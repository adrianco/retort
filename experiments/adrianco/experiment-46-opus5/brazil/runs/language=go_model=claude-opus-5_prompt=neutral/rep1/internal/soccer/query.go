// query.go - club lookup and match filtering.
//
// Context
//
//	Everything a user asks starts with a name they typed. ResolveClub turns
//	"flamengo", "Flamengo-RJ", "CR Flamengo" or "flamengo rj" into the single
//	club node, and falls back to a ranked fuzzy search when the exact machinery
//	comes up empty so the MCP tools can offer "did you mean" suggestions
//	instead of an error.
//
//	MatchFilter is the one filtering primitive behind every match-shaped
//	question: by team, by opponent, by home/away, by competition, by season, by
//	date range and by stage. All indexes are pre-sorted chronologically, so
//	filtering is a linear scan over the smallest available index (a club's own
//	match list when a team is named, the competition-season bucket otherwise).
package soccer

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// ClubMatch is a scored fuzzy-search hit.
type ClubMatch struct {
	Club  *Club
	Score int
}

// ResolveClub finds the club a user means. It returns the club, or nil plus a
// list of ranked suggestions when the name is ambiguous or unknown.
func (g *Graph) ResolveClub(query string) (*Club, []*Club) {
	query = strings.TrimSpace(query)
	if query == "" {
		return nil, nil
	}
	// An exact club ID always wins.
	if c, ok := g.clubs[strings.ToLower(query)]; ok {
		return c, nil
	}
	if id := g.resolver.resolve(query); id != "" {
		if c, ok := g.clubs[id]; ok {
			return c, nil
		}
	}
	suggestions := g.SearchClubs(query, 8)
	if len(suggestions) == 1 {
		return suggestions[0], nil
	}
	// A clearly dominant hit (an exact name match, or far more matches played
	// than the runner-up) is treated as the answer rather than a suggestion.
	if len(suggestions) > 1 && normalizeText(suggestions[0].Name) == normalizeText(query) &&
		normalizeText(suggestions[1].Name) != normalizeText(query) {
		return suggestions[0], nil
	}
	return nil, suggestions
}

// MustResolveClub is ResolveClub with an error describing the alternatives.
func (g *Graph) MustResolveClub(query string) (*Club, error) {
	c, suggestions := g.ResolveClub(query)
	if c != nil {
		return c, nil
	}
	if len(suggestions) == 0 {
		return nil, fmt.Errorf("no club matching %q; try search_teams to browse the %d clubs in the graph", query, len(g.clubs))
	}
	names := make([]string, 0, len(suggestions))
	for _, s := range suggestions {
		names = append(names, fmt.Sprintf("%s (id %s)", s.Label(), s.ID))
	}
	return nil, fmt.Errorf("%q is ambiguous; did you mean %s?", query, strings.Join(names, ", "))
}

// SearchClubs ranks clubs against a free-text query.
func (g *Graph) SearchClubs(query string, limit int) []*Club {
	q := normalizeText(query)
	if q == "" {
		out := g.Clubs()
		if limit > 0 && len(out) > limit {
			out = out[:limit]
		}
		return out
	}
	parsed := ParseTeamName(query)
	var hits []ClubMatch
	for _, id := range g.clubIDs {
		c := g.clubs[id]
		// Take the best of every way the query could match. An alias whose base
		// name equals the query beats a mere prefix of the display name, so
		// searching "atletico" surfaces Athletico Paranaense (spelled with an h
		// in the data) above Atlético Nacional of Colombia.
		score := 0
		best := func(v int) {
			if v > score {
				score = v
			}
		}
		if id == q || strings.ReplaceAll(id, "-", " ") == q {
			best(100)
		}
		if c.sortName == q {
			best(90)
		}
		if parsed.Base != "" && c.sortName == parsed.Base {
			best(85)
		}
		for i, na := range c.aliasNames {
			switch {
			case na == q:
				best(88)
			case parsed.Base != "" && c.aliasBases[i] == parsed.Base:
				best(82)
			case strings.Contains(na, q):
				best(40)
			}
		}
		if strings.HasPrefix(c.sortName, q) {
			best(70)
		} else if strings.Contains(c.sortName, q) {
			best(50)
		}
		if score == 0 {
			continue
		}
		// Break ties towards clubs with more data behind them.
		hits = append(hits, ClubMatch{Club: c, Score: score*1000 + min(c.Matches, 999)})
	}
	sort.Slice(hits, func(i, j int) bool {
		if hits[i].Score != hits[j].Score {
			return hits[i].Score > hits[j].Score
		}
		return hits[i].Club.ID < hits[j].Club.ID
	})
	out := make([]*Club, 0, len(hits))
	for _, h := range hits {
		out = append(out, h.Club)
	}
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// Venue restricts a query to home or away fixtures.
type Venue string

// Venue values.
const (
	VenueAny  Venue = "any"
	VenueHome Venue = "home"
	VenueAway Venue = "away"
)

// ParseVenue normalizes user input for the venue filter.
func ParseVenue(s string) Venue {
	switch normalizeText(s) {
	case "home":
		return VenueHome
	case "away":
		return VenueAway
	default:
		return VenueAny
	}
}

// MatchFilter describes a match search.
type MatchFilter struct {
	ClubID      string // the team of interest
	OpponentID  string // restrict to fixtures against this club
	Venue       Venue  // ClubID's venue
	Competition Competition
	Season      int
	SeasonFrom  int
	SeasonTo    int
	DateFrom    time.Time
	DateTo      time.Time
	Stage       string // substring match on stage or round label
	MinGoalDiff int
	OnlyPlayed  bool
	Newest      bool // sort newest first
	Limit       int
}

// FindMatches applies a filter across the graph.
func (g *Graph) FindMatches(f MatchFilter) []*Match {
	var pool []*Match
	switch {
	case f.ClubID != "":
		pool = g.byClub[f.ClubID]
	case f.Competition != "" && f.Season != 0:
		pool = g.CompetitionMatches(f.Competition, f.Season)
	default:
		pool = g.matches
	}

	out := make([]*Match, 0, 64)
	for _, m := range pool {
		if !f.accepts(m) {
			continue
		}
		out = append(out, m)
	}
	if f.Newest {
		// pool is ascending by date; reverse into descending.
		for i, j := 0, len(out)-1; i < j; i, j = i+1, j-1 {
			out[i], out[j] = out[j], out[i]
		}
	}
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func (f MatchFilter) accepts(m *Match) bool {
	if f.Competition != "" && m.Competition != f.Competition {
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
	if f.ClubID != "" {
		switch f.Venue {
		case VenueHome:
			if m.HomeClubID != f.ClubID {
				return false
			}
		case VenueAway:
			if m.AwayClubID != f.ClubID {
				return false
			}
		default:
			if !m.Involves(f.ClubID) {
				return false
			}
		}
	}
	if f.OpponentID != "" {
		if f.ClubID == "" {
			if !m.Involves(f.OpponentID) {
				return false
			}
		} else if m.Opponent(f.ClubID) != f.OpponentID {
			return false
		}
	}
	if !f.DateFrom.IsZero() {
		if !m.HasDate || m.Date.Before(f.DateFrom) {
			return false
		}
	}
	if !f.DateTo.IsZero() {
		if !m.HasDate || m.Date.After(f.DateTo) {
			return false
		}
	}
	if f.Stage != "" {
		needle := normalizeText(f.Stage)
		if !strings.Contains(normalizeText(m.Stage), needle) &&
			!strings.Contains(normalizeText("round "+m.Round), needle) {
			return false
		}
	}
	if f.OnlyPlayed && !m.HasScore {
		return false
	}
	if f.MinGoalDiff > 0 && (!m.HasScore || m.GoalDifference() < f.MinGoalDiff) {
		return false
	}
	return true
}

// ParseDateArg accepts "2023", "2023-09" and "2023-09-24" and returns the
// first instant of the period.
func ParseDateArg(s string, endOfPeriod bool) (time.Time, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, nil
	}
	switch len(s) {
	case 4:
		y, err := time.Parse("2006", s)
		if err != nil {
			return time.Time{}, fmt.Errorf("invalid date %q", s)
		}
		if endOfPeriod {
			return y.AddDate(1, 0, 0).Add(-time.Nanosecond), nil
		}
		return y, nil
	case 7:
		mth, err := time.Parse("2006-01", s)
		if err != nil {
			return time.Time{}, fmt.Errorf("invalid date %q", s)
		}
		if endOfPeriod {
			return mth.AddDate(0, 1, 0).Add(-time.Nanosecond), nil
		}
		return mth, nil
	default:
		d, err := time.Parse("2006-01-02", s)
		if err != nil {
			return time.Time{}, fmt.Errorf("invalid date %q (expected YYYY, YYYY-MM or YYYY-MM-DD)", s)
		}
		if endOfPeriod {
			return d.AddDate(0, 0, 1).Add(-time.Nanosecond), nil
		}
		return d, nil
	}
}
