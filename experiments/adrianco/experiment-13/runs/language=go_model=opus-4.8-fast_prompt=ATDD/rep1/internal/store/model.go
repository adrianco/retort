// Package store loads the provided Brazilian soccer datasets from CSV files and
// answers domain queries about matches, teams, players and competitions.
//
// It is the engine behind the MCP tools: the MCP layer translates tool calls
// into method calls on a *Store and serialises the typed results below.
package store

import "time"

// Canonical competition names used throughout the system.
const (
	CompBrasileirao  = "Brasileirao"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Libertadores"
)

// Match is a single normalised match across any of the provided datasets.
type Match struct {
	Competition string
	Season      int
	Round       string
	Stage       string

	Date    time.Time
	HasDate bool

	// HomeTeam/AwayTeam are cleaned display names (state suffixes and country
	// codes removed); HomeKey/AwayKey are the normalised identity keys (which
	// retain the state code so e.g. Atletico-MG and Atletico-GO stay distinct).
	HomeTeam string
	AwayTeam string
	HomeKey  string
	AwayKey  string

	// HomeState/AwayState are optional UF codes from a dataset's state columns,
	// used during loading to build identity keys.
	HomeState string
	AwayState string

	HomeGoals int
	AwayGoals int
}

// Player is a normalised FIFA player record.
type Player struct {
	ID          string
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string
	JerseyNo    string
	Height      string
	Weight      string
}

// DateString renders the match date as ISO-8601 (YYYY-MM-DD), or "" if unknown.
func (m Match) DateString() string {
	if !m.HasDate {
		return ""
	}
	return m.Date.Format("2006-01-02")
}
