// Package main implements a Brazilian Soccer MCP Server that provides
// a knowledge graph interface for Brazilian soccer data across multiple
// Kaggle datasets. It supports match queries, team statistics, player
// searches, competition standings, head-to-head comparisons, and
// statistical analysis via MCP tools.
package main

// Match represents a unified match record across all datasets.
type Match struct {
	DateTime    string
	HomeTeam    string
	AwayTeam    string
	HomeScore   int
	AwayScore   int
	Season      int
	Round       string
	Competition string
	Stage       string
	Tournament  string
	Source      string
}

// Player represents a FIFA player record.
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string
}

// TeamStats holds aggregated match statistics for a team.
type TeamStats struct {
	TeamName     string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	WinRate      float64
}

// H2HRecord holds head-to-head match results between two teams.
type H2HRecord struct {
	Team1        string
	Team2        string
	Team1Wins    int
	Team2Wins    int
	Draws        int
	TotalMatches int
	Matches      []Match
}

// StandingsEntry holds a team's standing in a competition.
type StandingsEntry struct {
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	GoalDiff     int
	Points       int
}

// BigWin represents a big victory from the dataset.
type BigWin struct {
	Date        string
	HomeTeam    string
	AwayTeam    string
	HomeScore   int
	AwayScore   int
	Competition string
}

// StatsSummary holds aggregated statistics.
type StatsSummary struct {
	AvgGoalsPerMatch float64
	HomeWinRate      float64
	DrawRate         float64
	AwayWinRate      float64
	TotalMatches     int
	TotalGoals       int
}
