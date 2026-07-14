// Package store: query and aggregation functions.
//
// Context:
//   - All queries operate over the in-memory Match / Player slices.
//   - Team-based filters use TeamMatches (accent-folded, suffix-stripped) so a
//     plain query like "Flamengo" matches every dataset spelling.
//   - Aggregations (records, standings, averages) are computed on demand; no
//     precomputed indexes since the dataset is small.
package store

import (
	"sort"
	"strings"
	"time"
)

// MatchFilter describes criteria for FindMatches. Empty fields are ignored.
type MatchFilter struct {
	Team        string    // matches home OR away
	Opponent    string    // when set with Team, restricts to head-to-head
	Competition string    // substring match on competition label
	Season      int       // exact season year (0 = any)
	DateFrom    time.Time // inclusive lower bound (zero = none)
	DateTo      time.Time // inclusive upper bound (zero = none)
}

// FindMatches returns matches satisfying the filter, sorted most-recent first
// (dateless matches sort last). limit <= 0 means no limit.
func (s *Store) FindMatches(f MatchFilter, limit int) []Match {
	var out []Match
	for _, m := range s.Matches {
		if !matchPasses(m, f) {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.HasDate != b.HasDate {
			return a.HasDate // dated matches first
		}
		return a.Date.After(b.Date)
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

func matchPasses(m Match, f MatchFilter) bool {
	if f.Team != "" && f.Opponent != "" {
		// Head-to-head: the two teams must be the participants (either side).
		if !((TeamMatches(m.HomeTeam, f.Team) && TeamMatches(m.AwayTeam, f.Opponent)) ||
			(TeamMatches(m.HomeTeam, f.Opponent) && TeamMatches(m.AwayTeam, f.Team))) {
			return false
		}
	} else if f.Team != "" {
		if !TeamMatches(m.HomeTeam, f.Team) && !TeamMatches(m.AwayTeam, f.Team) {
			return false
		}
	}
	if f.Competition != "" && !containsFold(m.Competition, f.Competition) {
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
	return true
}

// HeadToHead summarizes results between two teams from teamA's perspective,
// returning teamA's record plus the matching matches (most recent first).
func (s *Store) HeadToHead(teamA, teamB string) (TeamRecord, []Match) {
	matches := s.FindMatches(MatchFilter{Team: teamA, Opponent: teamB}, 0)
	rec := TeamRecord{Team: teamA}
	for _, m := range matches {
		if !m.HasScore {
			continue
		}
		accumulate(&rec, m, teamA)
	}
	return rec, matches
}

// accumulate folds a single match into a team's record (team perspective).
func accumulate(rec *TeamRecord, m Match, team string) {
	var gf, ga int
	isHome := TeamMatches(m.HomeTeam, team)
	if isHome {
		gf, ga = m.HomeGoals, m.AwayGoals
	} else {
		gf, ga = m.AwayGoals, m.HomeGoals
	}
	rec.Matches++
	rec.GoalsFor += gf
	rec.GoalsAgainst += ga
	switch {
	case gf > ga:
		rec.Wins++
	case gf < ga:
		rec.Losses++
	default:
		rec.Draws++
	}
}

// Venue restricts TeamStats to home/away/all matches.
type Venue int

const (
	VenueAll Venue = iota
	VenueHome
	VenueAway
)

// TeamStats computes a team's aggregate record, optionally restricted by
// competition, season, and venue.
func (s *Store) TeamStats(team, competition string, season int, venue Venue) TeamRecord {
	rec := TeamRecord{Team: team}
	for _, m := range s.Matches {
		if !m.HasScore {
			continue
		}
		if competition != "" && !containsFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		isHome := TeamMatches(m.HomeTeam, team)
		isAway := TeamMatches(m.AwayTeam, team)
		if !isHome && !isAway {
			continue
		}
		switch venue {
		case VenueHome:
			if !isHome {
				continue
			}
		case VenueAway:
			if !isAway {
				continue
			}
		}
		accumulate(&rec, m, team)
	}
	return rec
}

// Standings computes a league table for a competition + season from match
// results, sorted by points, then goal difference, then goals for.
func (s *Store) Standings(competition string, season int) []TeamRecord {
	if competition == "" {
		competition = CompBrasileirao
	}
	byTeam := map[string]*TeamRecord{}
	for _, m := range s.Matches {
		if !m.HasScore || !containsFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		homeKey := TeamKey(m.HomeTeam, m.HomeState)
		awayKey := TeamKey(m.AwayTeam, m.AwayState)
		if homeKey == "" || awayKey == "" {
			continue
		}
		home := getOrInit(byTeam, homeKey, m.HomeTeam)
		away := getOrInit(byTeam, awayKey, m.AwayTeam)
		accumulate(home, m, m.HomeTeam)
		accumulate(away, m, m.AwayTeam)
	}
	out := make([]TeamRecord, 0, len(byTeam))
	for _, r := range byTeam {
		out = append(out, *r)
	}
	// Tiebreakers follow Brazilian league rules: points, then wins, then goal
	// difference, then goals scored.
	sort.SliceStable(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDiff() != b.GoalDiff() {
			return a.GoalDiff() > b.GoalDiff()
		}
		return a.GoalsFor > b.GoalsFor
	})
	return out
}

func getOrInit(m map[string]*TeamRecord, key, display string) *TeamRecord {
	if r, ok := m[key]; ok {
		return r
	}
	r := &TeamRecord{Team: display}
	m[key] = r
	return r
}

// CompetitionStats aggregates league-wide statistics for a competition+season.
type CompetitionStats struct {
	Competition string
	Season      int
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
}

// AvgGoals returns average goals per match (0 when no matches).
func (c CompetitionStats) AvgGoals() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.TotalGoals) / float64(c.Matches)
}

// HomeWinRate returns the fraction of matches won by the home team.
func (c CompetitionStats) HomeWinRate() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.HomeWins) / float64(c.Matches)
}

// CompetitionStats computes aggregate stats. Empty competition = all matches.
func (s *Store) CompetitionStats(competition string, season int) CompetitionStats {
	cs := CompetitionStats{Competition: competition, Season: season}
	for _, m := range s.Matches {
		if !m.HasScore {
			continue
		}
		if competition != "" && !containsFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		cs.Matches++
		cs.TotalGoals += m.HomeGoals + m.AwayGoals
		switch m.Result() {
		case "home":
			cs.HomeWins++
		case "away":
			cs.AwayWins++
		default:
			cs.Draws++
		}
	}
	return cs
}

// BiggestWins returns matches with the largest goal margins, optionally
// filtered by competition + season, most lopsided first.
func (s *Store) BiggestWins(competition string, season, limit int) []Match {
	var out []Match
	for _, m := range s.Matches {
		if !m.HasScore {
			continue
		}
		if competition != "" && !containsFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if m.HomeGoals == m.AwayGoals {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool {
		return margin(out[i]) > margin(out[j])
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

func margin(m Match) int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}

// --- Player queries ---

// PlayerFilter describes criteria for SearchPlayers. Empty fields are ignored.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
}

// SearchPlayers returns players matching the filter, sorted by Overall rating
// descending. limit <= 0 means no limit.
func (s *Store) SearchPlayers(f PlayerFilter, limit int) []Player {
	var out []Player
	for _, p := range s.Players {
		if f.Name != "" && !containsFold(p.Name, f.Name) {
			continue
		}
		if f.Nationality != "" && !containsFold(p.Nationality, f.Nationality) {
			continue
		}
		if f.Club != "" && !containsFold(p.Club, f.Club) {
			continue
		}
		if f.Position != "" && !strings.EqualFold(strings.TrimSpace(p.Position), strings.TrimSpace(f.Position)) {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		return out[i].Overall > out[j].Overall
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}
