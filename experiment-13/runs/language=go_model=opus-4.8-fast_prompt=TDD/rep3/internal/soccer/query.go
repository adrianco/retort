// Context: Brazilian Soccer MCP Server.
// File: query.go
// Purpose: The query engine over the in-memory DB — match search with flexible
// filters, head-to-head records, team records, league standings computed from
// results, player search, and aggregate statistics. All team matching is
// accent/suffix-insensitive via TeamMatches.
package soccer

import (
	"sort"
	"strings"
	"time"
)

// Venue selects which side of a match a team's record is computed from.
type Venue int

const (
	VenueAny Venue = iota
	VenueHome
	VenueAway
)

// MatchFilter describes criteria for selecting matches. Zero-valued fields are
// treated as "any".
type MatchFilter struct {
	Team        string    // matches either home or away
	Opponent    string    // when combined with Team, restricts to that matchup
	HomeTeam    string    // restricts the home side
	AwayTeam    string    // restricts the away side
	Competition string    // substring/normalized competition match
	Season      int       // exact season; 0 = any
	From        time.Time // inclusive lower date bound; zero = unbounded
	To          time.Time // inclusive upper date bound; zero = unbounded
}

func competitionMatches(filter, comp string) bool {
	if filter == "" {
		return true
	}
	f := strings.ToLower(removeAccents(filter))
	c := strings.ToLower(removeAccents(comp))
	return strings.Contains(c, f) || strings.Contains(f, c)
}

func (m Match) matches(f MatchFilter) bool {
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	if !competitionMatches(f.Competition, m.Competition) {
		return false
	}
	if f.Team != "" {
		if !TeamMatches(f.Team, m.HomeTeam) && !TeamMatches(f.Team, m.AwayTeam) {
			return false
		}
	}
	if f.Opponent != "" {
		if !TeamMatches(f.Opponent, m.HomeTeam) && !TeamMatches(f.Opponent, m.AwayTeam) {
			return false
		}
	}
	if f.HomeTeam != "" && !TeamMatches(f.HomeTeam, m.HomeTeam) {
		return false
	}
	if f.AwayTeam != "" && !TeamMatches(f.AwayTeam, m.AwayTeam) {
		return false
	}
	if !f.From.IsZero() && (!m.HasDate || m.Date.Before(f.From)) {
		return false
	}
	if !f.To.IsZero() && (!m.HasDate || m.Date.After(f.To)) {
		return false
	}
	return true
}

// FindMatches returns all matches satisfying the filter, sorted by date
// ascending (undated matches sort last).
func (db *DB) FindMatches(f MatchFilter) []Match {
	var out []Match
	for _, m := range db.Matches {
		if m.matches(f) {
			out = append(out, m)
		}
	}
	sortByDate(out)
	return out
}

func sortByDate(ms []Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		a, b := ms[i], ms[j]
		if a.HasDate != b.HasDate {
			return a.HasDate // dated before undated
		}
		return a.Date.Before(b.Date)
	})
}

// H2H is a head-to-head record between two teams.
type H2H struct {
	TeamA   string
	TeamB   string
	AWins   int
	BWins   int
	Draws   int
	AGoals  int
	BGoals  int
	Matches []Match
}

// HeadToHead computes the head-to-head record between teamA and teamB across
// all competitions, from teamA's perspective.
func (db *DB) HeadToHead(teamA, teamB string) H2H {
	h := H2H{TeamA: teamA, TeamB: teamB}
	matchups := db.FindMatches(MatchFilter{Team: teamA, Opponent: teamB})
	for _, m := range matchups {
		if !m.HasScore {
			continue
		}
		aIsHome := TeamMatches(teamA, m.HomeTeam)
		var aGoals, bGoals int
		if aIsHome {
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
		h.Matches = append(h.Matches, m)
	}
	return h
}

// TeamFilter selects matches for computing a team's record.
type TeamFilter struct {
	Team        string
	Season      int
	Competition string
	Venue       Venue
}

// TeamRecord is an aggregate win/draw/loss and goals record for a team.
type TeamRecord struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

// Points returns league points (3 per win, 1 per draw).
func (r TeamRecord) Points() int { return r.Wins*3 + r.Draws }

// GoalDifference returns goals for minus goals against.
func (r TeamRecord) GoalDifference() int { return r.GoalsFor - r.GoalsAgainst }

// WinRate returns the fraction of matches won (0..1).
func (r TeamRecord) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Matches)
}

// accumulate folds a single match into the record from the team's perspective.
func (r *TeamRecord) accumulate(m Match, isHome bool) {
	var gf, ga int
	if isHome {
		gf, ga = m.HomeGoals, m.AwayGoals
	} else {
		gf, ga = m.AwayGoals, m.HomeGoals
	}
	r.Matches++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
	case ga > gf:
		r.Losses++
	default:
		r.Draws++
	}
}

// TeamRecord computes a team's aggregate record under the given filter.
func (db *DB) TeamRecord(f TeamFilter) TeamRecord {
	r := TeamRecord{Team: f.Team}
	for _, m := range db.Matches {
		if !m.HasScore {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !competitionMatches(f.Competition, m.Competition) {
			continue
		}
		isHome := TeamMatches(f.Team, m.HomeTeam)
		isAway := TeamMatches(f.Team, m.AwayTeam)
		if isHome && (f.Venue == VenueAny || f.Venue == VenueHome) {
			r.accumulate(m, true)
		} else if isAway && (f.Venue == VenueAny || f.Venue == VenueAway) {
			r.accumulate(m, false)
		}
	}
	return r
}

// Standings computes the league table for a season/competition from match
// results, sorted by points, then goal difference, then goals for.
func (db *DB) Standings(season int, competition string) []TeamRecord {
	records := map[string]*TeamRecord{}
	get := func(team string) *TeamRecord {
		key := NormalizeTeamName(team)
		if r, ok := records[key]; ok {
			return r
		}
		r := &TeamRecord{Team: team}
		records[key] = r
		return r
	}
	for _, m := range db.Matches {
		if !m.HasScore || m.Season != season {
			continue
		}
		if !competitionMatches(competition, m.Competition) {
			continue
		}
		get(m.HomeTeam).accumulate(m, true)
		get(m.AwayTeam).accumulate(m, false)
	}
	table := make([]TeamRecord, 0, len(records))
	for _, r := range records {
		table = append(table, *r)
	}
	sort.SliceStable(table, func(i, j int) bool {
		a, b := table[i], table[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.GoalDifference() != b.GoalDifference() {
			return a.GoalDifference() > b.GoalDifference()
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	return table
}

// PlayerFilter describes criteria for selecting players.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int // 0 = no limit
}

// FindPlayers returns players matching the filter, sorted by overall rating
// descending (ties broken by name), optionally limited.
func (db *DB) FindPlayers(f PlayerFilter) []Player {
	var out []Player
	for _, p := range db.Players {
		if f.Name != "" && !containsFold(p.Name, f.Name) {
			continue
		}
		if f.Nationality != "" && !containsFold(p.Nationality, f.Nationality) {
			continue
		}
		if f.Club != "" && !TeamMatches(f.Club, p.Club) {
			continue
		}
		if f.Position != "" && !strings.EqualFold(p.Position, f.Position) {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].Name < out[j].Name
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func containsFold(haystack, needle string) bool {
	return strings.Contains(
		strings.ToLower(removeAccents(haystack)),
		strings.ToLower(removeAccents(needle)),
	)
}

// AverageGoals returns the mean total goals per match for matches matching the
// filter that have a recorded score.
func (db *DB) AverageGoals(f MatchFilter) float64 {
	var total, n int
	for _, m := range db.Matches {
		if !m.HasScore || !m.matches(f) {
			continue
		}
		total += m.HomeGoals + m.AwayGoals
		n++
	}
	if n == 0 {
		return 0
	}
	return float64(total) / float64(n)
}

// HomeWinRate returns the fraction of matched matches won by the home side.
func (db *DB) HomeWinRate(f MatchFilter) float64 {
	var homeWins, n int
	for _, m := range db.Matches {
		if !m.HasScore || !m.matches(f) {
			continue
		}
		n++
		if m.HomeGoals > m.AwayGoals {
			homeWins++
		}
	}
	if n == 0 {
		return 0
	}
	return float64(homeWins) / float64(n)
}

// BiggestWins returns up to n matched matches with the largest goal margin,
// ordered by descending margin.
func (db *DB) BiggestWins(f MatchFilter, n int) []Match {
	var scored []Match
	for _, m := range db.Matches {
		if m.HasScore && m.matches(f) && m.HomeGoals != m.AwayGoals {
			scored = append(scored, m)
		}
	}
	sort.SliceStable(scored, func(i, j int) bool {
		return margin(scored[i]) > margin(scored[j])
	})
	if n > 0 && len(scored) > n {
		scored = scored[:n]
	}
	return scored
}

func margin(m Match) int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}
