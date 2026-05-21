// model.go defines the core data types for the Brazilian Soccer knowledge base:
// matches, players, and the in-memory DataStore that holds them.
package main

import "time"

// Match is a single game from any of the match datasets.
type Match struct {
	Competition string // unified competition name (e.g. "Brasileirão Série A")
	Source      string // originating CSV file, used to de-duplicate overlapping seasons
	Date        time.Time
	HasDate     bool
	Season      int
	Round       string
	Stage       string // tournament stage, when available (Libertadores)
	HomeTeam    string // display name as it appears in the data
	AwayTeam    string
	HomeKey     string // normalized name for matching
	AwayKey     string
	HomeGoal    int
	AwayGoal    int
	HasScore    bool
	Arena       string

	// Extended statistics, only populated by BR-Football-Dataset.csv.
	HasStats    bool
	HomeShots   int
	AwayShots   int
	HomeCorners int
	AwayCorners int
}

// Outcome returns "home", "away" or "draw" for the match result.
func (m Match) Outcome() string {
	switch {
	case m.HomeGoal > m.AwayGoal:
		return "home"
	case m.AwayGoal > m.HomeGoal:
		return "away"
	default:
		return "draw"
	}
}

// GoalMargin is the absolute goal difference of the match.
func (m Match) GoalMargin() int {
	d := m.HomeGoal - m.AwayGoal
	if d < 0 {
		return -d
	}
	return d
}

// DateLabel returns a stable human label for the match date.
func (m Match) DateLabel() string {
	if m.HasDate {
		return m.Date.Format("2006-01-02")
	}
	if m.Season > 0 {
		return itoa(m.Season)
	}
	return "unknown date"
}

// Player is a single entry from the FIFA player database.
type Player struct {
	ID            int
	Name          string
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	ClubKey       string // normalized club name for matching
	Position      string
	JerseyNumber  string
	Height        string
	Weight        string
	Value         string
	Wage          string
	PreferredFoot string
}

// DataStore holds every loaded record and is the root of all queries.
type DataStore struct {
	Matches []Match
	Players []Player
}
