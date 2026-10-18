package models

import (
	"time"
)

// Match represents a soccer match
type Match struct {
	Id          string    `json:"id"`
	Datetime    time.Time `json:"datetime"`
	HomeTeam    string    `json:"home_team"`
	HomeTeamState string  `json:"home_team_state"`
	AwayTeam    string    `json:"away_team"`
	AwayTeamState string  `json:"away_team_state"`
	HomeGoals   int       `json:"home_goal"`
	AwayGoals   int       `json:"away_goal"`
	Season      int       `json:"season"`
	Round       int       `json:"round"`
	Tournament  string    `json:"tournament,omitempty"`
	Stage       string    `json:"stage,omitempty"`
}

// Player represents a soccer player
type Player struct {
	Id              string `json:"id"`
	Name            string `json:"name"`
	Age             int    `json:"age"`
	Nationality     string `json:"nationality"`
	Overall         int    `json:"overall"`
	Potential       int    `json:"potential"`
	Club            string `json:"club"`
	Position        string `json:"position"`
	JerseyNumber    int    `json:"jersey_number"`
	Height          string `json:"height"`
	Weight          string `json:"weight"`
	// ... more skill ratings
}

// TeamStats represents team statistics
type TeamStats struct {
	TeamName    string `json:"team_name"`
	Wins        int    `json:"wins"`
	Draws       int    `json:"draws"`
	Losses      int    `json:"losses"`
	GoalsFor    int    `json:"goals_for"`
	GoalsAgainst int   `json:"goals_against"`
	WinRate     float64 `json:"win_rate"`
	Matches     int    `json:"matches"`
}

// CompetitionStandings represents competition standings
type CompetitionStandings struct {
	Position    int    `json:"position"`
	TeamName    string `json:"team_name"`
	Points      int    `json:"points"`
	Wins        int    `json:"wins"`
	Draws       int    `json:"draws"`
	Losses      int    `json:"losses"`
	GoalsFor    int    `json:"goals_for"`
	GoalsAgainst int   `json:"goals_against"`
}
