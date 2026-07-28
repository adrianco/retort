package models

import "time"

// Match represents a soccer match
type Match struct {
	ID           int
	Datetime     time.Time
	HomeTeam     string
	HomeTeamState string
	AwayTeam     string
	AwayTeamState string
	HomeGoal   int
	AwayGoal   int
	Season     int
	Round      int
	Stage      string // For Libertadores
	Tournament string // For BR-Football dataset
}

// Player represents a FIFA player
type Player struct {
	ID           int
	Name         string
	Age          int
	Nationality  string
	Overall      int
	Potential    int
	Club         string
	Position     string
	JerseyNumber int
	Height       string
	Weight       string
	// Additional skill attributes
	Crossing      int
	Finishing     int
	HeadingAccuracy int
	ShortPassing  int
	Volleys       int
	Dribbling     int
	Curve         int
	FKAccuracy    int
	LongPassing   int
	BallControl   int
	Acceleration  int
	SprintSpeed   int
	Agility       int
	Reactions     int
	Balance       int
	ShotPower     int
	Jumping       int
	Stamina       int
	Strength      int
	LongShots     int
	Aggression    int
	Interceptions int
	Positioning   int
	Vision        int
	Penalties     int
	Composure     int
	Marking       int
	StandingTackle int
	SlidingTackle int
	GKDiving      int
	GKHandling    int
	GKKicking     int
	GKPositioning int
	GKReflexes    int
	ReleaseClause string
}

// TeamStats represents aggregated statistics for a team
type TeamStats struct {
	TeamName     string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int
	WinRate      float64
	HomeMatches  int
	AwayMatches  int
	HomeWins     int
	AwayWins     int
	HomeDraws    int
	AwayDraws    int
	HomeLosses   int
	AwayLosses   int
}

// CompetitionResult represents a competition standings table
type CompetitionResult struct {
	TeamName     string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int
	Round        int
	Season       int
}

// HeadToHead represents head-to-head record between two teams
type HeadToHead struct {
	Team1    string
	Team2    string
	Matches  int
	Team1Wins int
	Team2Wins int
	Draws    int
	Team1Goals int
	Team2Goals int
}

// BigWin represents a match with a large goal difference
type BigWin struct {
	Date       time.Time
	HomeTeam   string
	AwayTeam   string
	HomeGoal   int
	AwayGoal   int
	GoalDiff   int
	Tournament string
}

// QueryResult is the response format for queries
type QueryResult struct {
	Success    bool   `json:"success"`
	Message    string `json:"message"`
	Data       interface{} `json:"data,omitempty"`
	Error      string `json:"error,omitempty"`
}
