package main

import "time"

// Match represents a single football match normalized from any of the
// provided Kaggle CSV datasets into a common shape.
type Match struct {
	Competition string
	Source      string
	Date        time.Time
	HasDate     bool
	Season      int
	Round       string
	Stage       string
	HomeTeam    string // canonical/display name
	AwayTeam    string // canonical/display name
	HomeTeamKey string // normalized key used for matching
	AwayTeamKey string
	HomeGoals   int
	AwayGoals   int
	HomeState   string
	AwayState   string
	Arena       string
}

// Winner returns "home", "away" or "draw".
func (m Match) Winner() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return "home"
	case m.AwayGoals > m.HomeGoals:
		return "away"
	default:
		return "draw"
	}
}

// GoalDiff returns the absolute goal difference of the match.
func (m Match) GoalDiff() int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		d = -d
	}
	return d
}

// Player represents a single row from the FIFA player dataset.
type Player struct {
	ID           int
	Name         string
	Age          int
	Nationality  string
	Overall      int
	Potential    int
	Club         string
	ClubKey      string
	Position     string
	JerseyNumber int
	Height       string
	Weight       string
}
