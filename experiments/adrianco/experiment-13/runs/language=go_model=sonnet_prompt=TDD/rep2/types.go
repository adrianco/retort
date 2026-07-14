package main

import "time"

// Competition constants
const (
	CompBrasileirao  = "brasileirao"
	CompCopa         = "copa_do_brasil"
	CompLibertadores = "libertadores"
	CompBRFootball   = "br_football"
	CompHistorico    = "historico"
)

// Match represents a soccer match from any competition
type Match struct {
	DateTime    time.Time
	HomeTeam    string
	AwayTeam    string
	HomeGoals   int
	AwayGoals   int
	Season      int
	Round       string
	Stage       string
	Competition string
	// Additional fields for BR-Football
	HomeCorner float64
	AwayCorner float64
	HomeAttack float64
	AwayAttack float64
	HomeShots  float64
	AwayShots  float64
	Tournament string
}

// Player represents a FIFA player record
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
}

// TeamStats represents aggregated stats for a team
type TeamStats struct {
	Team         string
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Played       int
	Points       int
}

// Standing represents a team's position in standings
type Standing struct {
	Position     int
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

// Database holds all loaded data
type Database struct {
	Brasileirao  []Match
	Copa         []Match
	Libertadores []Match
	BRFootball   []Match
	Historico    []Match
	Players      []Player
}
