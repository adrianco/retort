package main

// Match represents a unified match record from any competition
type Match struct {
	HomeTeam    string
	AwayTeam    string
	HomeGoal    int
	AwayGoal    int
	Season      int
	Round       string
	Date        string // ISO format YYYY-MM-DD
	Competition string
	Stage       string
	Arena       string
	HomeCorner  float64
	AwayCorner  float64
	HomeShots   float64
	AwayShots   float64
}

// Player represents a FIFA player record
type Player struct {
	ID          string
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string
	JerseyNumber string
	Height      string
	Weight      string
}

// Database holds all loaded data
type Database struct {
	Matches []Match
	Players []Player
}

// TeamRecord holds standings statistics for a team
type TeamRecord struct {
	Team   string
	Played int
	Wins   int
	Draws  int
	Losses int
	GF     int // Goals For
	GA     int // Goals Against
	GD     int // Goal Difference
	Points int
}
