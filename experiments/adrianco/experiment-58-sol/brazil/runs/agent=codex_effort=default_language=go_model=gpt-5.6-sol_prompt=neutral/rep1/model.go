package main

import "time"

// Match is the normalized representation shared by all five match datasets.
// Source retains provenance so callers can inspect an individual feed.
type Match struct {
	Date          time.Time `json:"date"`
	HomeTeam      string    `json:"home_team"`
	AwayTeam      string    `json:"away_team"`
	HomeGoals     int       `json:"home_goals"`
	AwayGoals     int       `json:"away_goals"`
	Competition   string    `json:"competition"`
	Season        int       `json:"season"`
	Round         string    `json:"round,omitempty"`
	Stage         string    `json:"stage,omitempty"`
	Arena         string    `json:"arena,omitempty"`
	Source        string    `json:"source"`
	HomeCorners   *int      `json:"home_corners,omitempty"`
	AwayCorners   *int      `json:"away_corners,omitempty"`
	HomeShots     *int      `json:"home_shots,omitempty"`
	AwayShots     *int      `json:"away_shots,omitempty"`
	ResultMissing bool      `json:"result_missing,omitempty"`
}

type Player struct {
	ID          int            `json:"id"`
	Name        string         `json:"name"`
	Age         int            `json:"age"`
	Nationality string         `json:"nationality"`
	Overall     int            `json:"overall"`
	Potential   int            `json:"potential"`
	Club        string         `json:"club,omitempty"`
	Position    string         `json:"position,omitempty"`
	Jersey      int            `json:"jersey_number,omitempty"`
	Height      string         `json:"height,omitempty"`
	Weight      string         `json:"weight,omitempty"`
	Attributes  map[string]int `json:"attributes,omitempty"`
}

type TeamRecord struct {
	Team         string  `json:"team"`
	Matches      int     `json:"matches"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	GoalDiff     int     `json:"goal_difference"`
	Points       int     `json:"points"`
	WinRate      float64 `json:"win_rate_percent"`
}

type Standing struct {
	Position int `json:"position"`
	TeamRecord
}

type DerbyResult struct {
	Derby string `json:"derby"`
	Match
}
