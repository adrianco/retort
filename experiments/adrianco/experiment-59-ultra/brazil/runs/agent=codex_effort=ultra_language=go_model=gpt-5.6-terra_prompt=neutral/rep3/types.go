package main

import "time"

// Match is a single fixture from one of the supplied match datasets. Scores are
// pointers because the source files also contain scheduled or incomplete matches.
type Match struct {
	Date        time.Time `json:"-"`
	DateText    string    `json:"date,omitempty"`
	Competition string    `json:"competition"`
	Source      string    `json:"source"`
	HomeTeam    string    `json:"home_team"`
	AwayTeam    string    `json:"away_team"`
	HomeGoals   *int      `json:"home_goals"`
	AwayGoals   *int      `json:"away_goals"`
	Season      int       `json:"season,omitempty"`
	Round       string    `json:"round,omitempty"`
	Stage       string    `json:"stage,omitempty"`
	Stadium     string    `json:"stadium,omitempty"`
}

// Played reports whether both final scores are available. A match with no final
// result remains searchable, but never contributes to calculated statistics.
func (m Match) Played() bool {
	return m.HomeGoals != nil && m.AwayGoals != nil
}

// GoalDifference returns the absolute winning margin for a completed match.
func (m Match) GoalDifference() int {
	if !m.Played() {
		return 0
	}
	difference := *m.HomeGoals - *m.AwayGoals
	if difference < 0 {
		return -difference
	}
	return difference
}

// Player contains the searchable FIFA fields that are relevant to the server's
// public API. The source has many more ratings; this compact model is deliberate.
type Player struct {
	ID          string `json:"id,omitempty"`
	Name        string `json:"name"`
	Age         int    `json:"age,omitempty"`
	Nationality string `json:"nationality,omitempty"`
	Overall     int    `json:"overall,omitempty"`
	Potential   int    `json:"potential,omitempty"`
	Club        string `json:"club,omitempty"`
	Position    string `json:"position,omitempty"`
	Jersey      string `json:"jersey_number,omitempty"`
	Height      string `json:"height,omitempty"`
	Weight      string `json:"weight,omitempty"`
}

// DatasetInfo describes one file successfully loaded by the server.
type DatasetInfo struct {
	File    string `json:"file"`
	Kind    string `json:"kind"`
	Records int    `json:"records"`
}

// DataStore is read-only after loading. Keeping the data in memory makes common
// lookup and aggregate requests comfortably fit the required response budgets.
type DataStore struct {
	Matches  []Match
	Players  []Player
	Datasets []DatasetInfo
}

type MatchFilter struct {
	Team              string
	Opponent          string
	HomeTeam          string
	AwayTeam          string
	Competition       string
	Source            string
	Season            int
	Round             string
	Stage             string
	StartDate         time.Time
	EndDate           time.Time
	Limit             int
	IncludeAllSources bool
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
	Team            string  `json:"team"`
	Venue           string  `json:"venue"`
	Competition     string  `json:"competition,omitempty"`
	Season          int     `json:"season,omitempty"`
	Source          string  `json:"source,omitempty"`
	Matches         int     `json:"matches"`
	Wins            int     `json:"wins"`
	Draws           int     `json:"draws"`
	Losses          int     `json:"losses"`
	GoalsFor        int     `json:"goals_for"`
	GoalsAgainst    int     `json:"goals_against"`
	GoalDifference  int     `json:"goal_difference"`
	WinRate         float64 `json:"win_rate_percent"`
	GoalsPerMatch   float64 `json:"goals_per_match"`
	PlayedFixtures  int     `json:"played_fixtures"`
	UnplayedMatches int     `json:"unplayed_matches"`
}

type HeadToHead struct {
	TeamA       string  `json:"team_a"`
	TeamB       string  `json:"team_b"`
	TeamAWins   int     `json:"team_a_wins"`
	TeamBWins   int     `json:"team_b_wins"`
	Draws       int     `json:"draws"`
	Played      int     `json:"played_matches"`
	Unplayed    int     `json:"unplayed_matches"`
	Matches     []Match `json:"matches"`
	Total       int     `json:"total_matches"`
	Competition string  `json:"competition,omitempty"`
	Season      int     `json:"season,omitempty"`
}

type Standing struct {
	Rank           int    `json:"rank"`
	Team           string `json:"team"`
	Played         int    `json:"played"`
	Wins           int    `json:"wins"`
	Draws          int    `json:"draws"`
	Losses         int    `json:"losses"`
	GoalsFor       int    `json:"goals_for"`
	GoalsAgainst   int    `json:"goals_against"`
	GoalDifference int    `json:"goal_difference"`
	Points         int    `json:"points"`
}

type StandingsResult struct {
	Competition    string     `json:"competition"`
	Season         int        `json:"season"`
	SourcePolicy   string     `json:"source_policy"`
	Sources        []string   `json:"sources"`
	PlayedMatches  int        `json:"played_matches"`
	IgnoredMatches int        `json:"ignored_unplayed_matches"`
	Standings      []Standing `json:"standings"`
}

type CompetitionStats struct {
	Competition     string   `json:"competition"`
	Season          int      `json:"season,omitempty"`
	SourcePolicy    string   `json:"source_policy"`
	Sources         []string `json:"sources"`
	Fixtures        int      `json:"fixtures"`
	PlayedMatches   int      `json:"played_matches"`
	UnplayedMatches int      `json:"unplayed_matches"`
	TotalGoals      int      `json:"total_goals"`
	AverageGoals    float64  `json:"average_goals_per_match"`
	HomeWins        int      `json:"home_wins"`
	AwayWins        int      `json:"away_wins"`
	Draws           int      `json:"draws"`
	HomeWinRate     float64  `json:"home_win_rate_percent"`
	AwayWinRate     float64  `json:"away_win_rate_percent"`
	BiggestWins     []Match  `json:"biggest_wins"`
}

type TeamRanking struct {
	Rank    int     `json:"rank"`
	Team    string  `json:"team"`
	Value   float64 `json:"value"`
	Matches int     `json:"matches"`
	Goals   int     `json:"goals,omitempty"`
}
