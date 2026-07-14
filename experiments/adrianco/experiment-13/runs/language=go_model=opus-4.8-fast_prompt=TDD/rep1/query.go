// Package main — Brazilian Soccer MCP Server.
//
// query.go: The query engine over a loaded Dataset. It implements the five
// capability areas from the specification — match search, team records,
// head-to-head, season standings, player search and aggregate statistics.
//
// Design notes:
//   - Team filtering uses normalized keys (accent/suffix-insensitive) so a
//     query for "Flamengo" matches "Flamengo-RJ".
//   - Standings deliberately group by display name (suffix preserved) within a
//     single source, so same-named clubs from different states (Atlético-MG vs
//     Atlético-PR) stay distinct and seasons aren't double-counted across the
//     overlapping Brasileirão files.
package main

import (
	"sort"
	"strings"
	"time"
)

// Venue selects which side of a match a team's record is computed from.
type Venue int

const (
	VenueAll Venue = iota
	VenueHome
	VenueAway
)

// MatchFilter describes criteria for selecting matches. Zero-valued fields are
// ignored (no constraint).
type MatchFilter struct {
	Team        string    // matches either side
	Opponent    string    // when set with Team, restricts to meetings between the two
	HomeTeam    string    // matches home side only
	AwayTeam    string    // matches away side only
	Competition string    // case/accent-insensitive substring of the competition name
	Source      string    // exact dataset source ("Brasileirao", "Cup", ...)
	Season      int       // 0 = any season
	From        time.Time // inclusive lower date bound (zero = unbounded)
	To          time.Time // inclusive upper date bound (zero = unbounded)
}

// matches reports whether a single match satisfies the filter.
func (f MatchFilter) matches(m Match) bool {
	if f.Source != "" && m.Source != f.Source {
		return false
	}
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	if f.Competition != "" {
		needle := NormalizeTeam(f.Competition)
		if !strings.Contains(NormalizeTeam(m.Competition), needle) {
			return false
		}
	}
	if f.Team != "" {
		if !m.Involves(NormalizeTeam(f.Team)) {
			return false
		}
	}
	if f.Opponent != "" {
		if !m.Involves(NormalizeTeam(f.Opponent)) {
			return false
		}
	}
	if f.HomeTeam != "" && m.HomeTeamKey != NormalizeTeam(f.HomeTeam) {
		return false
	}
	if f.AwayTeam != "" && m.AwayTeamKey != NormalizeTeam(f.AwayTeam) {
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

// FindMatches returns all matches satisfying the filter, most recent first
// (matches without dates sort last, preserving load order among themselves).
func (ds *Dataset) FindMatches(f MatchFilter) []Match {
	var out []Match
	for _, m := range ds.Matches {
		if f.matches(m) {
			out = append(out, m)
		}
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].HasDate != out[j].HasDate {
			return out[i].HasDate // dated matches first
		}
		return out[i].Date.After(out[j].Date)
	})
	return out
}

// Record is a team's win/draw/loss and goal summary over a set of matches.
type Record struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

// WinRate is wins as a fraction of matches played (0 when none).
func (r Record) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Matches)
}

// TeamRecord computes a team's record over matches matching the filter,
// restricted to the requested venue (home, away or all).
func (ds *Dataset) TeamRecord(team string, f MatchFilter, venue Venue) Record {
	key := NormalizeTeam(team)
	rec := Record{Team: team}
	for _, m := range ds.Matches {
		if !m.HasScore || !f.matches(m) {
			continue
		}
		isHome := m.HomeTeamKey == key
		isAway := m.AwayTeamKey == key
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
		rec.Matches++
		var gf, ga int
		if isHome {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
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
	return rec
}

// H2H is the head-to-head summary between two teams.
type H2H struct {
	TeamA   string
	TeamB   string
	AWins   int
	BWins   int
	Draws   int
	Matches []Match
}

// Total is the number of meetings.
func (h H2H) Total() int { return h.AWins + h.BWins + h.Draws }

// HeadToHead returns the all-competition head-to-head record between two teams.
func (ds *Dataset) HeadToHead(teamA, teamB string) H2H {
	keyA, keyB := NormalizeTeam(teamA), NormalizeTeam(teamB)
	h := H2H{TeamA: teamA, TeamB: teamB}
	for _, m := range ds.Matches {
		if !m.HasScore {
			continue
		}
		if !(m.Involves(keyA) && m.Involves(keyB)) {
			continue
		}
		h.Matches = append(h.Matches, m)
		w := m.Winner()
		switch {
		case w == "draw":
			h.Draws++
		case (w == "home" && m.HomeTeamKey == keyA) || (w == "away" && m.AwayTeamKey == keyA):
			h.AWins++
		default:
			h.BWins++
		}
	}
	sort.SliceStable(h.Matches, func(i, j int) bool {
		return h.Matches[i].Date.After(h.Matches[j].Date)
	})
	return h
}

// StandingRow is one team's line in a season table.
type StandingRow struct {
	Team     string
	Played   int
	Wins     int
	Draws    int
	Losses   int
	GoalsFor int
	GoalsAg  int
	Points   int
}

// GoalDiff is goals for minus goals against.
func (s StandingRow) GoalDiff() int { return s.GoalsFor - s.GoalsAg }

// Standings computes a league table for a competition and season, awarding
// 3 points per win and 1 per draw. To avoid double-counting the overlapping
// Brasileirão files, it picks the single source with the most matches for that
// season and groups by display name (so same-named, different-state clubs stay
// separate).
func (ds *Dataset) Standings(competition string, season int) []StandingRow {
	needle := NormalizeTeam(competition)

	// Tally candidate matches per source for this competition+season.
	bySource := map[string][]Match{}
	for _, m := range ds.Matches {
		if m.Season != season || !m.HasScore {
			continue
		}
		if needle != "" && !strings.Contains(NormalizeTeam(m.Competition), needle) {
			continue
		}
		bySource[m.Source] = append(bySource[m.Source], m)
	}
	if len(bySource) == 0 {
		return nil
	}

	// Prefer the source with the most matches; break ties deterministically by
	// source name for reproducibility.
	bestSrc := ""
	for src, ms := range bySource {
		if bestSrc == "" || len(ms) > len(bySource[bestSrc]) ||
			(len(ms) == len(bySource[bestSrc]) && src < bestSrc) {
			bestSrc = src
		}
	}

	table := map[string]*StandingRow{}
	row := func(name string) *StandingRow {
		if r, ok := table[name]; ok {
			return r
		}
		r := &StandingRow{Team: name}
		table[name] = r
		return r
	}
	for _, m := range bySource[bestSrc] {
		h := row(m.HomeTeam)
		a := row(m.AwayTeam)
		h.Played++
		a.Played++
		h.GoalsFor += m.HomeGoals
		h.GoalsAg += m.AwayGoals
		a.GoalsFor += m.AwayGoals
		a.GoalsAg += m.HomeGoals
		switch m.Winner() {
		case "home":
			h.Wins++
			h.Points += 3
			a.Losses++
		case "away":
			a.Wins++
			a.Points += 3
			h.Losses++
		default:
			h.Draws++
			a.Draws++
			h.Points++
			a.Points++
		}
	}

	out := make([]StandingRow, 0, len(table))
	for _, r := range table {
		out = append(out, *r)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Points != out[j].Points {
			return out[i].Points > out[j].Points
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

// PlayerFilter describes criteria for searching the FIFA player database.
type PlayerFilter struct {
	Name        string // case/accent-insensitive substring
	Nationality string // case/accent-insensitive substring
	Club        string // case/accent-insensitive substring
	Position    string // exact (case-insensitive) position code
	MinOverall  int
	Limit       int // 0 = no limit
}

// SearchPlayers returns players matching the filter, sorted by Overall rating
// descending (ties broken by name), truncated to Limit.
func (ds *Dataset) SearchPlayers(f PlayerFilter) []Player {
	name := NormalizeTeam(f.Name)
	nat := NormalizeTeam(f.Nationality)
	club := NormalizeTeam(f.Club)
	pos := strings.ToUpper(strings.TrimSpace(f.Position))

	var out []Player
	for _, p := range ds.Players {
		if name != "" && !strings.Contains(NormalizeTeam(p.Name), name) {
			continue
		}
		if nat != "" && !strings.Contains(NormalizeTeam(p.Nationality), nat) {
			continue
		}
		if club != "" && !strings.Contains(NormalizeTeam(p.Club), club) {
			continue
		}
		if pos != "" && strings.ToUpper(p.Position) != pos {
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

// Stats holds aggregate match statistics over a filtered set.
type Stats struct {
	Matches     int
	TotalGoals  int
	AvgGoals    float64
	HomeWins    int
	AwayWins    int
	Draws       int
	HomeWinRate float64
}

// Stats computes aggregate statistics over matches matching the filter
// (only matches with a recorded score are counted).
func (ds *Dataset) Stats(f MatchFilter) Stats {
	var s Stats
	for _, m := range ds.Matches {
		if !m.HasScore || !f.matches(m) {
			continue
		}
		s.Matches++
		s.TotalGoals += m.HomeGoals + m.AwayGoals
		switch m.Winner() {
		case "home":
			s.HomeWins++
		case "away":
			s.AwayWins++
		default:
			s.Draws++
		}
	}
	if s.Matches > 0 {
		s.AvgGoals = float64(s.TotalGoals) / float64(s.Matches)
		s.HomeWinRate = float64(s.HomeWins) / float64(s.Matches)
	}
	return s
}

// BiggestWins returns the matches with the largest goal margin matching the
// filter, descending by margin, limited to limit results.
func (ds *Dataset) BiggestWins(f MatchFilter, limit int) []Match {
	var out []Match
	for _, m := range ds.Matches {
		if m.HasScore && f.matches(m) {
			out = append(out, m)
		}
	}
	sort.SliceStable(out, func(i, j int) bool {
		mi := out[i].HomeGoals - out[i].AwayGoals
		if mi < 0 {
			mi = -mi
		}
		mj := out[j].HomeGoals - out[j].AwayGoals
		if mj < 0 {
			mj = -mj
		}
		return mi > mj
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}
