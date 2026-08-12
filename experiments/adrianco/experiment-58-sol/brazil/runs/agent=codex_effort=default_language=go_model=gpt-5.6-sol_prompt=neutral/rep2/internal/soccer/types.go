package soccer

import "time"

// Match is the normalized representation shared by every match data source.
type Match struct {
	Date        string         `json:"date"`
	HomeTeam    string         `json:"home_team"`
	AwayTeam    string         `json:"away_team"`
	HomeGoals   int            `json:"home_goals"`
	AwayGoals   int            `json:"away_goals"`
	Completed   bool           `json:"completed"`
	Competition string         `json:"competition"`
	Season      int            `json:"season"`
	Round       string         `json:"round,omitempty"`
	Stage       string         `json:"stage,omitempty"`
	Stadium     string         `json:"stadium,omitempty"`
	Statistics  map[string]int `json:"statistics,omitempty"`
	Source      string         `json:"source"`
	date        time.Time
	homeKey     string
	awayKey     string
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
	Jersey      string         `json:"jersey_number,omitempty"`
	Height      string         `json:"height,omitempty"`
	Weight      string         `json:"weight,omitempty"`
	Attributes  map[string]int `json:"attributes,omitempty"`
	Source      string         `json:"source"`
	nameKey     string
	clubKey     string
}

type SourceSummary struct {
	File    string `json:"file"`
	Kind    string `json:"kind"`
	Records int    `json:"records"`
}

type Catalog struct {
	Matches []Match
	Players []Player
	Sources map[string]SourceSummary
}

type MatchQuery struct {
	Team        string `json:"team,omitempty" jsonschema:"team that participated, matching home or away"`
	Opponent    string `json:"opponent,omitempty" jsonschema:"optional second team; use with team for head-to-head matches"`
	Competition string `json:"competition,omitempty" jsonschema:"competition such as Brasileirao, Copa do Brasil, Libertadores, Serie B or Serie C"`
	Season      int    `json:"season,omitempty" jsonschema:"four-digit season year"`
	From        string `json:"from,omitempty" jsonschema:"inclusive start date in YYYY-MM-DD or DD/MM/YYYY format"`
	To          string `json:"to,omitempty" jsonschema:"inclusive end date in YYYY-MM-DD or DD/MM/YYYY format"`
	Stage       string `json:"stage,omitempty" jsonschema:"round or stage text, for example final or group stage"`
	HomeOnly    bool   `json:"home_only,omitempty" jsonschema:"only matches where team was at home"`
	AwayOnly    bool   `json:"away_only,omitempty" jsonschema:"only matches where team was away"`
	Limit       int    `json:"limit,omitempty" jsonschema:"maximum results, defaults to 50 and is capped at 500"`
}

type MatchSearchResult struct {
	Matches  []Match `json:"matches"`
	Returned int     `json:"returned"`
	Total    int     `json:"total"`
	Summary  string  `json:"summary"`
}

type TeamRecord struct {
	Team         string  `json:"team"`
	Competition  string  `json:"competition,omitempty"`
	Season       int     `json:"season,omitempty"`
	Venue        string  `json:"venue"`
	Matches      int     `json:"matches"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	Points       int     `json:"points"`
	WinRate      float64 `json:"win_rate_percent"`
}

type HeadToHeadResult struct {
	TeamA     string  `json:"team_a"`
	TeamB     string  `json:"team_b"`
	Matches   int     `json:"matches"`
	TeamAWins int     `json:"team_a_wins"`
	TeamBWins int     `json:"team_b_wins"`
	Draws     int     `json:"draws"`
	GoalsA    int     `json:"team_a_goals"`
	GoalsB    int     `json:"team_b_goals"`
	Recent    []Match `json:"recent_matches"`
}

type PlayerQuery struct {
	Name        string `json:"name,omitempty" jsonschema:"player name or partial name"`
	Nationality string `json:"nationality,omitempty" jsonschema:"nationality, for example Brazil"`
	Club        string `json:"club,omitempty" jsonschema:"club name"`
	Position    string `json:"position,omitempty" jsonschema:"FIFA position code or group such as forward, midfielder, defender, goalkeeper"`
	MinOverall  int    `json:"min_overall,omitempty" jsonschema:"minimum FIFA overall rating"`
	Limit       int    `json:"limit,omitempty" jsonschema:"maximum results, defaults to 25 and is capped at 500"`
}

type PlayerSearchResult struct {
	Players  []Player `json:"players"`
	Returned int      `json:"returned"`
	Total    int      `json:"total"`
	Summary  string   `json:"summary"`
}

type Standing struct {
	Position       int    `json:"position"`
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
	Competition string     `json:"competition"`
	Season      int        `json:"season"`
	Standings   []Standing `json:"standings"`
	Champion    string     `json:"champion,omitempty"`
	Note        string     `json:"note"`
}

type BiggestVictory struct {
	Match  Match `json:"match"`
	Margin int   `json:"margin"`
}

type AggregateResult struct {
	Competition      string           `json:"competition,omitempty"`
	Season           int              `json:"season,omitempty"`
	Matches          int              `json:"matches"`
	Goals            int              `json:"goals"`
	GoalsPerMatch    float64          `json:"goals_per_match"`
	HomeWins         int              `json:"home_wins"`
	AwayWins         int              `json:"away_wins"`
	Draws            int              `json:"draws"`
	HomeWinRate      float64          `json:"home_win_rate_percent"`
	BiggestVictories []BiggestVictory `json:"biggest_victories"`
}

type ClubOverview struct {
	Team          string     `json:"team"`
	Record        TeamRecord `json:"match_record"`
	Players       []Player   `json:"fifa_players"`
	PlayerCount   int        `json:"player_count"`
	AverageRating float64    `json:"average_player_rating,omitempty"`
}
