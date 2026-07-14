package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// MatchFilter narrows the set of matches returned by FindMatches.
// Any zero-valued field is ignored.
type MatchFilter struct {
	Team        string // matches if either team
	HomeTeam    string
	AwayTeam    string
	Opponent    string // used with Team to find head-to-head
	Competition string
	Season      int
	From        time.Time
	To          time.Time
	Stage       string
	Limit       int
}

// FindMatches returns matches in the dataset that satisfy the filter,
// sorted by date descending (most recent first).
func (d *Dataset) FindMatches(f MatchFilter) []Match {
	out := make([]Match, 0, 128)
	for _, m := range d.Matches {
		if !matchPassesFilter(m, f) {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func matchPassesFilter(m Match, f MatchFilter) bool {
	if f.Team != "" {
		if !(TeamMatches(f.Team, m.HomeTeam) || TeamMatches(f.Team, m.AwayTeam)) {
			return false
		}
	}
	if f.Opponent != "" {
		if !(TeamMatches(f.Opponent, m.HomeTeam) || TeamMatches(f.Opponent, m.AwayTeam)) {
			return false
		}
	}
	if f.HomeTeam != "" && !TeamMatches(f.HomeTeam, m.HomeTeam) {
		return false
	}
	if f.AwayTeam != "" && !TeamMatches(f.AwayTeam, m.AwayTeam) {
		return false
	}
	if f.Competition != "" && !ContainsFold(m.Competition, f.Competition) {
		return false
	}
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	if !f.From.IsZero() && m.Date.Before(f.From) {
		return false
	}
	if !f.To.IsZero() && m.Date.After(f.To) {
		return false
	}
	if f.Stage != "" && !ContainsFold(m.Stage, f.Stage) {
		return false
	}
	return true
}

// TeamStats describes a team's record over a set of matches.
type TeamStats struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int // 3 per win, 1 per draw
}

// WinRate returns wins / matches as a percentage.
func (s TeamStats) WinRate() float64 {
	if s.Matches == 0 {
		return 0
	}
	return 100 * float64(s.Wins) / float64(s.Matches)
}

// ComputeTeamStats summarises performance for `team` across `matches`.
// If `homeOnly` is true only matches where the team is home count, similarly
// for `awayOnly`.
func ComputeTeamStats(team string, matches []Match, homeOnly, awayOnly bool) TeamStats {
	stats := TeamStats{Team: team}
	for _, m := range matches {
		home := TeamMatches(team, m.HomeTeam)
		away := TeamMatches(team, m.AwayTeam)
		if !home && !away {
			continue
		}
		if homeOnly && !home {
			continue
		}
		if awayOnly && !away {
			continue
		}
		stats.Matches++
		var gf, ga int
		var win, loss, draw bool
		if home {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		stats.GoalsFor += gf
		stats.GoalsAgainst += ga
		switch {
		case gf > ga:
			win = true
		case gf < ga:
			loss = true
		default:
			draw = true
		}
		if win {
			stats.Wins++
			stats.Points += 3
		}
		if draw {
			stats.Draws++
			stats.Points++
		}
		if loss {
			stats.Losses++
		}
	}
	return stats
}

// HeadToHead summarises results between two teams.
type HeadToHead struct {
	TeamA      string
	TeamB      string
	Matches    int
	AWins      int
	BWins      int
	Draws      int
	AGoals     int
	BGoals     int
	MatchList  []Match
}

// ComputeHeadToHead summarises all matches in `matches` involving both teams.
func ComputeHeadToHead(a, b string, matches []Match) HeadToHead {
	h := HeadToHead{TeamA: a, TeamB: b}
	for _, m := range matches {
		aHome := TeamMatches(a, m.HomeTeam)
		bHome := TeamMatches(b, m.HomeTeam)
		aAway := TeamMatches(a, m.AwayTeam)
		bAway := TeamMatches(b, m.AwayTeam)
		var aFor, bFor int
		switch {
		case aHome && bAway:
			aFor, bFor = m.HomeGoals, m.AwayGoals
		case bHome && aAway:
			aFor, bFor = m.AwayGoals, m.HomeGoals
		default:
			continue
		}
		h.Matches++
		h.AGoals += aFor
		h.BGoals += bFor
		switch {
		case aFor > bFor:
			h.AWins++
		case bFor > aFor:
			h.BWins++
		default:
			h.Draws++
		}
		h.MatchList = append(h.MatchList, m)
	}
	sort.SliceStable(h.MatchList, func(i, j int) bool { return h.MatchList[i].Date.After(h.MatchList[j].Date) })
	return h
}

// StandingsEntry is one row of a calculated standings table.
type StandingsEntry struct {
	TeamStats
	GoalDifference int
}

// Standings produces a standings table from the matches in `matches`. Teams
// are ranked by points desc, goal difference desc, goals for desc.
func Standings(matches []Match) []StandingsEntry {
	stats := make(map[string]*TeamStats)
	canon := make(map[string]string)
	get := func(name string) *TeamStats {
		k := NormalizeTeam(name)
		if s, ok := stats[k]; ok {
			return s
		}
		s := &TeamStats{Team: name}
		stats[k] = s
		canon[k] = name
		return s
	}
	for _, m := range matches {
		if m.HomeTeam == "" || m.AwayTeam == "" {
			continue
		}
		h := get(m.HomeTeam)
		a := get(m.AwayTeam)
		h.Matches++
		a.Matches++
		h.GoalsFor += m.HomeGoals
		h.GoalsAgainst += m.AwayGoals
		a.GoalsFor += m.AwayGoals
		a.GoalsAgainst += m.HomeGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			h.Wins++
			h.Points += 3
			a.Losses++
		case m.AwayGoals > m.HomeGoals:
			a.Wins++
			a.Points += 3
			h.Losses++
		default:
			h.Draws++
			h.Points++
			a.Draws++
			a.Points++
		}
	}
	out := make([]StandingsEntry, 0, len(stats))
	for _, s := range stats {
		out = append(out, StandingsEntry{
			TeamStats:      *s,
			GoalDifference: s.GoalsFor - s.GoalsAgainst,
		})
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Points != out[j].Points {
			return out[i].Points > out[j].Points
		}
		if out[i].GoalDifference != out[j].GoalDifference {
			return out[i].GoalDifference > out[j].GoalDifference
		}
		if out[i].GoalsFor != out[j].GoalsFor {
			return out[i].GoalsFor > out[j].GoalsFor
		}
		return out[i].Team < out[j].Team
	})
	return out
}

// PlayerFilter narrows the set of players returned by FindPlayers.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// FindPlayers returns matching players, sorted by Overall rating desc.
func (d *Dataset) FindPlayers(f PlayerFilter) []Player {
	out := make([]Player, 0, 64)
	for _, p := range d.Players {
		if f.Name != "" && !ContainsFold(p.Name, f.Name) {
			continue
		}
		if f.Nationality != "" && !ContainsFold(p.Nationality, f.Nationality) {
			continue
		}
		if f.Club != "" && !ContainsFold(p.Club, f.Club) {
			continue
		}
		if f.Position != "" && !ContainsFold(p.Position, f.Position) {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Overall > out[j].Overall })
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// BiggestWins returns the top `limit` matches by goal margin.
func (d *Dataset) BiggestWins(competition string, season int, limit int) []Match {
	matches := d.Matches
	if competition != "" || season != 0 {
		matches = d.FindMatches(MatchFilter{Competition: competition, Season: season})
	}
	out := make([]Match, 0, len(matches))
	out = append(out, matches...)
	sort.SliceStable(out, func(i, j int) bool {
		di := abs(out[i].HomeGoals - out[i].AwayGoals)
		dj := abs(out[j].HomeGoals - out[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		ti := out[i].HomeGoals + out[i].AwayGoals
		tj := out[j].HomeGoals + out[j].AwayGoals
		return ti > tj
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// AverageGoals returns the average total goals per match over the slice.
func AverageGoals(matches []Match) float64 {
	if len(matches) == 0 {
		return 0
	}
	tot := 0
	for _, m := range matches {
		tot += m.HomeGoals + m.AwayGoals
	}
	return float64(tot) / float64(len(matches))
}

// HomeWinRate returns the percentage of matches won by the home team.
func HomeWinRate(matches []Match) float64 {
	if len(matches) == 0 {
		return 0
	}
	wins := 0
	for _, m := range matches {
		if m.HomeGoals > m.AwayGoals {
			wins++
		}
	}
	return 100 * float64(wins) / float64(len(matches))
}

// FormatMatch renders a one-line summary of a match suitable for tool output.
func FormatMatch(m Match) string {
	date := "?"
	if !m.Date.IsZero() {
		date = m.Date.Format("2006-01-02")
	}
	suffix := m.Competition
	if m.Round != "" {
		suffix = fmt.Sprintf("%s Round %s", suffix, m.Round)
	}
	if m.Stage != "" {
		suffix = fmt.Sprintf("%s %s", suffix, m.Stage)
	}
	return fmt.Sprintf("%s: %s %d-%d %s (%s)",
		date, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, strings.TrimSpace(suffix))
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
