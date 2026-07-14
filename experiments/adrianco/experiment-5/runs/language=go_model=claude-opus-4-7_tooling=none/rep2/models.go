package main

import "time"

// Match represents a single soccer match. Source identifies which CSV
// file the match was loaded from so callers can attribute results.
type Match struct {
	Source      string
	Competition string
	Date        time.Time
	Season      int
	Round       string
	Stage       string
	HomeTeam    string
	AwayTeam    string
	HomeState   string
	AwayState   string
	HomeGoals   int
	AwayGoals   int
	Arena       string

	HomeCorners float64
	AwayCorners float64
	HomeShots   float64
	AwayShots   float64
	HomeAttacks float64
	AwayAttacks float64
	HTResult    string
	ATResult    string
}

// Player represents a single FIFA player entry.
type Player struct {
	ID           int
	Name         string
	Age          int
	Nationality  string
	Overall      int
	Potential    int
	Club         string
	Position     string
	JerseyNumber string
	Height       string
	Weight       string
	PreferredFoot string
	Value        string
	Wage         string
}

// Dataset bundles all the in-memory data the query layer needs.
type Dataset struct {
	Matches []Match
	Players []Player
}

// Outcome returns "home", "away", or "draw" for the match.
func (m Match) Outcome() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return "home"
	case m.AwayGoals > m.HomeGoals:
		return "away"
	default:
		return "draw"
	}
}
