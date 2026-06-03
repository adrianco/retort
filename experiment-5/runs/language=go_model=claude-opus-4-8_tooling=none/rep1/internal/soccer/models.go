// Package soccer provides the in-memory data model, CSV loaders, name
// normalization and query functions for the Brazilian Soccer knowledge base.
//
// Context:
//   - This file defines the unified domain model used across the whole
//     application: Match (a single game from any of the match CSV files) and
//     Player (a row from the FIFA player database).
//   - All six provided CSV files use different column names, date formats and
//     team-naming conventions. The loaders (loader.go) translate each source
//     format into these common structs so that the query layer (queries.go) and
//     the MCP tool layer (../mcpserver) can work against a single shape.
//   - Canonical competition names are declared here and used everywhere a
//     competition is referenced.
package soccer

import "time"

// Canonical competition names. Every match is mapped onto exactly one of these
// regardless of which source file (and which raw label) it came from.
const (
	CompSerieA       = "Brasileirão Série A"
	CompSerieB       = "Brasileirão Série B"
	CompSerieC       = "Brasileirão Série C"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Match is a single game, unified across all match data sources.
//
// Display names (HomeTeam/AwayTeam) keep their accents and casing but have the
// state/country suffix stripped (e.g. "Palmeiras-SP" -> "Palmeiras"). The
// normalized keys (HomeNorm/AwayNorm) are accent-free, lower-cased forms used
// for matching and de-duplication.
type Match struct {
	Competition string
	Season      int
	Date        time.Time
	HasDate     bool
	Round       string
	Stage       string

	HomeTeam string
	AwayTeam string
	HomeNorm string
	AwayNorm string

	HomeGoals int
	AwayGoals int
	HasScore  bool

	HomeState string
	AwayState string
	Arena     string

	// Sources lists the CSV file(s) that contributed to this (possibly merged)
	// record.
	Sources []string
}

// Played reports whether the match has a usable final score.
func (m Match) Played() bool { return m.HasScore }

// Winner returns "home", "away" or "draw" for a played match, and "" otherwise.
func (m Match) Winner() string {
	if !m.HasScore {
		return ""
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

// TotalGoals returns the combined goal count of a played match.
func (m Match) TotalGoals() int { return m.HomeGoals + m.AwayGoals }

// Player is a single row from the FIFA player database.
type Player struct {
	ID            int
	Name          string
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	Position      string
	JerseyNumber  string
	Height        string
	Weight        string
	PreferredFoot string
	Value         string
	Wage          string

	NameNorm string // accent-free lower-cased name, for searching
	ClubNorm string
}
