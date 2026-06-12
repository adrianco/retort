// Package main — Brazilian Soccer MCP Server.
//
// models.go: Core in-memory data model shared across the loader, query engine
// and MCP tool layer. A single Dataset holds every match (unified from all five
// match CSVs) and every FIFA player, with team names pre-normalized into match
// keys so cross-file lookups are O(n) scans without repeated string work.
package main

import "time"

// Match is a single game unified across all match datasets. HomeTeam/AwayTeam
// preserve a clean display name; HomeTeamKey/AwayTeamKey hold the normalized
// matching key (see NormalizeTeam).
type Match struct {
	Source      string    // dataset of origin: "Brasileirao", "Cup", "Libertadores", "Historico", "BR-Football"
	Competition string    // display competition name
	Date        time.Time // parsed kickoff date (zero if unknown)
	HasDate     bool
	Season      int
	Round       string
	Stage       string // tournament stage, when available (Libertadores)
	Arena       string // stadium, when available (historical)

	HomeTeam    string
	AwayTeam    string
	HomeTeamKey string
	AwayTeamKey string

	HomeGoals int
	AwayGoals int
	HasScore  bool
}

// Player is a FIFA database entry. Only the fields needed for the specified
// query categories are retained.
type Player struct {
	ID           int
	Name         string
	Age          int
	Nationality  string
	Overall      int
	Potential    int
	Club         string
	Position     string
	JerseyNumber string
	Height       string
	Weight       string
}

// Dataset is the fully loaded, queryable corpus.
type Dataset struct {
	Matches []Match
	Players []Player
}

// Winner reports the match outcome from the home team's perspective.
// Returns "home", "away", or "draw"; "unknown" if the match has no score.
func (m Match) Winner() string {
	if !m.HasScore {
		return "unknown"
	}
	switch {
	case m.HomeGoals > m.AwayGoals:
		return "home"
	case m.AwayGoals > m.HomeGoals:
		return "away"
	default:
		return "draw"
	}
}

// Involves reports whether the given normalized team key is either side.
func (m Match) Involves(key string) bool {
	return m.HomeTeamKey == key || m.AwayTeamKey == key
}
