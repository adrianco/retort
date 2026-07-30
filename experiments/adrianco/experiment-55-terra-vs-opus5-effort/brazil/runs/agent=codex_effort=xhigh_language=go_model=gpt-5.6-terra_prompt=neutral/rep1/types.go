package main

import "time"

// Match is the common representation used for every supplied match dataset.
// Source is retained so a caller can see which CSV supplied a record.
type Match struct {
	Date        time.Time `json:"date"`
	Competition string    `json:"competition"`
	Season      int       `json:"season"`
	Round       string    `json:"round,omitempty"`
	Stage       string    `json:"stage,omitempty"`
	HomeTeam    string    `json:"home_team"`
	AwayTeam    string    `json:"away_team"`
	HomeGoals   int       `json:"home_goals"`
	AwayGoals   int       `json:"away_goals"`
	Source      string    `json:"source"`
	Venue       string    `json:"venue,omitempty"`
	HomeCorners *int      `json:"home_corners,omitempty"`
	AwayCorners *int      `json:"away_corners,omitempty"`
	HomeShots   *int      `json:"home_shots,omitempty"`
	AwayShots   *int      `json:"away_shots,omitempty"`
}

// Player contains the useful, queryable subset of the FIFA player CSV.  The
// original record has many more rating columns, but retaining them all would
// make MCP responses unnecessarily large.
type Player struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Age         int    `json:"age"`
	Nationality string `json:"nationality"`
	Overall     int    `json:"overall"`
	Potential   int    `json:"potential"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	JerseyNo    string `json:"jersey_number,omitempty"`
	Height      string `json:"height,omitempty"`
	Weight      string `json:"weight,omitempty"`
}

type DataStore struct {
	Matches []Match
	Players []Player
}

type MatchFilter struct {
	Team        string
	Opponent    string
	HomeTeam    string
	AwayTeam    string
	Competition string
	Season      int
	DateFrom    time.Time
	DateTo      time.Time
	Round       string
	Stage       string
	Limit       int
}

type TeamStatistics struct {
	Team            string  `json:"team"`
	Season          int     `json:"season,omitempty"`
	Competition     string  `json:"competition,omitempty"`
	Venue           string  `json:"venue"`
	Matches         int     `json:"matches"`
	Wins            int     `json:"wins"`
	Draws           int     `json:"draws"`
	Losses          int     `json:"losses"`
	GoalsFor        int     `json:"goals_for"`
	GoalsAgainst    int     `json:"goals_against"`
	Points          int     `json:"points"`
	WinRate         float64 `json:"win_rate"`
	GoalsPerMatch   float64 `json:"goals_per_match"`
	ConcededPerGame float64 `json:"goals_conceded_per_match"`
}

type HeadToHead struct {
	TeamA       string  `json:"team_a"`
	TeamB       string  `json:"team_b"`
	Matches     int     `json:"matches"`
	TeamAWins   int     `json:"team_a_wins"`
	TeamBWins   int     `json:"team_b_wins"`
	Draws       int     `json:"draws"`
	TeamAGoals  int     `json:"team_a_goals"`
	TeamBGoals  int     `json:"team_b_goals"`
	MatchesList []Match `json:"match_details"`
}

type Standing struct {
	Position     int     `json:"position"`
	Team         string  `json:"team"`
	Played       int     `json:"played"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	GoalDiff     int     `json:"goal_difference"`
	Points       int     `json:"points"`
	WinRate      float64 `json:"win_rate"`
}

type CompetitionStatistics struct {
	Competition   string  `json:"competition,omitempty"`
	Season        int     `json:"season,omitempty"`
	Matches       int     `json:"matches"`
	Goals         int     `json:"goals"`
	GoalsPerMatch float64 `json:"goals_per_match"`
	HomeWins      int     `json:"home_wins"`
	Draws         int     `json:"draws"`
	AwayWins      int     `json:"away_wins"`
	HomeWinRate   float64 `json:"home_win_rate"`
}
