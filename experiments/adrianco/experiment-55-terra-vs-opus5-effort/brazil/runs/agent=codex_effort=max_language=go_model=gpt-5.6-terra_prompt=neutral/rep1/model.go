package main

import "time"

// Match is the normalized representation used for every supplied match CSV.
// Dates are retained as time.Time internally and exposed as ISO-8601 strings.
type Match struct {
	ID          string      `json:"id"`
	Date        time.Time   `json:"-"`
	DateText    string      `json:"date"`
	HomeTeam    string      `json:"home_team"`
	AwayTeam    string      `json:"away_team"`
	HomeState   string      `json:"home_team_state,omitempty"`
	AwayState   string      `json:"away_team_state,omitempty"`
	Venue       string      `json:"venue,omitempty"`
	KickoffTime string      `json:"kickoff_time,omitempty"`
	HomeKey     string      `json:"-"`
	AwayKey     string      `json:"-"`
	HomeGoals   int         `json:"home_goals"`
	AwayGoals   int         `json:"away_goals"`
	HasScore    bool        `json:"has_score"`
	Competition string      `json:"competition"`
	Season      int         `json:"season,omitempty"`
	Round       string      `json:"round,omitempty"`
	Stage       string      `json:"stage,omitempty"`
	Source      string      `json:"source"`
	Statistics  *MatchStats `json:"statistics,omitempty"`
}

// MatchStats is available for rows from BR-Football-Dataset.csv.  The other
// sources do not provide these values, so the pointer fields stay nil.
type MatchStats struct {
	HomeCorners  *int   `json:"home_corners,omitempty"`
	AwayCorners  *int   `json:"away_corners,omitempty"`
	HomeAttacks  *int   `json:"home_attacks,omitempty"`
	AwayAttacks  *int   `json:"away_attacks,omitempty"`
	HomeShots    *int   `json:"home_shots,omitempty"`
	AwayShots    *int   `json:"away_shots,omitempty"`
	TotalCorners *int   `json:"total_corners,omitempty"`
	HomeHalfTime string `json:"home_half_time_result,omitempty"`
	AwayHalfTime string `json:"away_half_time_result,omitempty"`
}

// Player contains the useful, queryable portion of the FIFA player data.
// Skills intentionally contain a small set of commonly requested attributes
// rather than serialising the complete raw CSV row for every result.
type Player struct {
	ID            int            `json:"id"`
	Name          string         `json:"name"`
	Age           int            `json:"age,omitempty"`
	Nationality   string         `json:"nationality"`
	Overall       int            `json:"overall"`
	Potential     int            `json:"potential,omitempty"`
	Club          string         `json:"club"`
	Position      string         `json:"position"`
	JerseyNumber  int            `json:"jersey_number,omitempty"`
	Height        string         `json:"height,omitempty"`
	Weight        string         `json:"weight,omitempty"`
	PreferredFoot string         `json:"preferred_foot,omitempty"`
	Skills        map[string]int `json:"skills,omitempty"`
}

// DataSource describes one loaded input file.
type DataSource struct {
	File        string `json:"file"`
	Kind        string `json:"kind"`
	RecordCount int    `json:"record_count"`
	Description string `json:"description"`
}

// MatchFilter is shared by the focused MCP tools and natural-language router.
type MatchFilter struct {
	Team              string
	Opponent          string
	HomeTeam          string
	AwayTeam          string
	Competition       string
	Season            int
	StartDate         *time.Time
	EndDate           *time.Time
	Round             string
	Stage             string
	Source            string
	DerbiesOnly       bool
	FinalsOnly        bool
	IncludeDuplicates bool
	Limit             int
	Descending        bool
}

// TeamStatistics is calculated from match results, not copied from a source.
type TeamStatistics struct {
	Team           string  `json:"team"`
	Competition    string  `json:"competition,omitempty"`
	Season         int     `json:"season,omitempty"`
	Scope          string  `json:"scope"`
	Matches        int     `json:"matches"`
	Wins           int     `json:"wins"`
	Draws          int     `json:"draws"`
	Losses         int     `json:"losses"`
	GoalsFor       int     `json:"goals_for"`
	GoalsAgainst   int     `json:"goals_against"`
	GoalDifference int     `json:"goal_difference"`
	Points         int     `json:"points"`
	WinRate        float64 `json:"win_rate"`
	GoalsPerMatch  float64 `json:"goals_per_match"`
}

// HeadToHeadRecord describes a two-team comparison from a chosen match set.
type HeadToHeadRecord struct {
	Team          string  `json:"team"`
	Opponent      string  `json:"opponent"`
	Matches       int     `json:"matches"`
	TeamWins      int     `json:"team_wins"`
	OpponentWins  int     `json:"opponent_wins"`
	Draws         int     `json:"draws"`
	TeamGoals     int     `json:"team_goals"`
	OpponentGoals int     `json:"opponent_goals"`
	TeamWinRate   float64 `json:"team_win_rate"`
}

// Standing is a calculated league-table row.
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

// CompetitionSummary is a compact aggregate for a competition or season.
type CompetitionSummary struct {
	Competition  string  `json:"competition,omitempty"`
	Season       int     `json:"season,omitempty"`
	Matches      int     `json:"matches"`
	TotalGoals   int     `json:"total_goals"`
	AverageGoals float64 `json:"average_goals_per_match"`
	HomeWins     int     `json:"home_wins"`
	Draws        int     `json:"draws"`
	AwayWins     int     `json:"away_wins"`
	HomeWinRate  float64 `json:"home_win_rate"`
	DrawRate     float64 `json:"draw_rate"`
	AwayWinRate  float64 `json:"away_win_rate"`
}
