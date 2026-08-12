package main

import "time"

// Match is the common representation used for every match CSV in the dataset.
// Optional statistics are pointers so a real zero is distinguishable from
// information that was not present in the source file.
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
	HomeState   string    `json:"home_state,omitempty"`
	AwayState   string    `json:"away_state,omitempty"`
	Venue       string    `json:"venue,omitempty"`
	HomeCorners *int      `json:"home_corners,omitempty"`
	AwayCorners *int      `json:"away_corners,omitempty"`
	HomeAttacks *int      `json:"home_attacks,omitempty"`
	AwayAttacks *int      `json:"away_attacks,omitempty"`
	HomeShots   *int      `json:"home_shots,omitempty"`
	AwayShots   *int      `json:"away_shots,omitempty"`
	Source      string    `json:"source"`
}

type Player struct {
	ID          int            `json:"id"`
	Name        string         `json:"name"`
	Age         int            `json:"age"`
	Nationality string         `json:"nationality"`
	Overall     int            `json:"overall"`
	Potential   int            `json:"potential"`
	Club        string         `json:"club"`
	Position    string         `json:"position"`
	Jersey      string         `json:"jersey_number,omitempty"`
	Height      string         `json:"height,omitempty"`
	Weight      string         `json:"weight,omitempty"`
	Attributes  map[string]int `json:"attributes,omitempty"`
}

type MatchFilter struct {
	Team        string
	Opponent    string
	Competition string
	Season      int
	StartDate   time.Time
	EndDate     time.Time
	Stage       string
	HomeOnly    bool
	AwayOnly    bool
	Limit       int
}

type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

type TeamStats struct {
	Team         string  `json:"team"`
	Competition  string  `json:"competition,omitempty"`
	Season       int     `json:"season,omitempty"`
	Matches      int     `json:"matches"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	Points       int     `json:"points"`
	WinRate      float64 `json:"win_rate"`
	HomeMatches  int     `json:"home_matches"`
	AwayMatches  int     `json:"away_matches"`
	HomeWins     int     `json:"home_wins"`
	AwayWins     int     `json:"away_wins"`
}

type Standing struct {
	Position     int    `json:"position"`
	Team         string `json:"team"`
	Played       int    `json:"played"`
	Wins         int    `json:"wins"`
	Draws        int    `json:"draws"`
	Losses       int    `json:"losses"`
	GoalsFor     int    `json:"goals_for"`
	GoalsAgainst int    `json:"goals_against"`
	GoalDiff     int    `json:"goal_difference"`
	Points       int    `json:"points"`
}

type HeadToHead struct {
	Team1     string  `json:"team1"`
	Team2     string  `json:"team2"`
	Matches   int     `json:"matches"`
	Team1Wins int     `json:"team1_wins"`
	Team2Wins int     `json:"team2_wins"`
	Draws     int     `json:"draws"`
	Goals1    int     `json:"team1_goals"`
	Goals2    int     `json:"team2_goals"`
	Results   []Match `json:"results"`
}

type CompetitionStats struct {
	Competition   string  `json:"competition,omitempty"`
	Season        int     `json:"season,omitempty"`
	Matches       int     `json:"matches"`
	Goals         int     `json:"goals"`
	GoalsPerMatch float64 `json:"goals_per_match"`
	HomeWins      int     `json:"home_wins"`
	AwayWins      int     `json:"away_wins"`
	Draws         int     `json:"draws"`
	HomeWinRate   float64 `json:"home_win_rate"`
	AwayWinRate   float64 `json:"away_win_rate"`
	DrawRate      float64 `json:"draw_rate"`
}

type Database struct {
	Matches []Match
	Players []Player
}
