// Package soccer implements the data layer for the Brazilian Soccer MCP server.
//
// Context:
//   - Loads six pre-downloaded Kaggle CSV datasets (five match files and one
//     FIFA player file) into in-memory slices.
//   - Normalizes the many team-name spellings used across the datasets
//     ("Palmeiras-SP", "Palmeiras", "São Paulo", "Sao Paulo", "Nacional (URU)")
//     into a stable matching key so cross-file queries work.
//   - Exposes a Store that answers the query categories described in TASK.md:
//     match search, team statistics, head-to-head, player search, competition
//     standings and aggregate statistical analysis.
//
// This file defines the in-memory domain model (Match, Player) shared by the
// loaders (load.go), the query engine (query.go) and the MCP tools (mcp.go).
package soccer

import "time"

// Competition identifiers used to tag every Match with a canonical name,
// independent of which source file it was loaded from.
const (
	CompBrasileirao  = "Brasileirão Série A"
	CompCopaBrasil   = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
	CompSerieB       = "Brasileirão Série B"
	CompSerieC       = "Brasileirão Série C"
)

// Match is a single fixture normalized from any of the five match datasets.
type Match struct {
	// Date is the kickoff date/time when parseable. Zero if the source had no
	// usable date. DateStr is always the YYYY-MM-DD string for display.
	Date    time.Time
	DateStr string

	HomeTeam string // display name, cleaned but accent-preserving
	AwayTeam string
	HomeKey  string // normalized matching key (see normalize.go)
	AwayKey  string

	HomeState string // state abbreviation when available (e.g. "SP")
	AwayState string

	HomeGoal int
	AwayGoal int

	Season      int    // year of the season
	Round       string // round/rodada number or label, when available
	Stage       string // tournament stage (Libertadores: "group stage", "final"...)
	Competition string // one of the Comp* constants
	Arena       string // stadium, when available
	Source      string // originating CSV file name

	// HasScore is false for fixtures that were missing goal data.
	HasScore bool
}

// Winner returns "home", "away" or "draw" for a played match.
func (m Match) Winner() string {
	switch {
	case m.HomeGoal > m.AwayGoal:
		return "home"
	case m.AwayGoal > m.HomeGoal:
		return "away"
	default:
		return "draw"
	}
}

// Player is a row from fifa_data.csv (FIFA 19 player database).
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	ClubKey     string // normalized club key for matching
	Position    string
	Jersey      string
	Height      string
	Weight      string
	Value       string
	Wage        string
	PreferredFt string
}
