// Package soccer implements an in-memory knowledge graph over the Brazilian
// soccer Kaggle datasets and the query layer used by the MCP server.
//
// Context
// -------
// The package loads six CSV files (five match datasets and one FIFA player
// dataset) into normalized Go structs, deduplicates overlapping match records,
// and exposes high level query functions (match search, head-to-head records,
// team statistics, league standings, player search and competition wide
// statistics). It deliberately has no external dependencies so the resulting
// MCP server is a single self-contained binary.
//
// This file defines the core domain models (Match, Player) and the canonical
// competition names shared across the package.
package soccer

import "time"

// Canonical competition names. Source datasets use many spellings; loaders map
// every match onto one of these (or keep the raw tournament name when unknown).
const (
	CompBrasileirao  = "Brasileirão Série A"
	CompCopaBrasil   = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Match is a single normalized match record drawn from any of the match CSVs.
type Match struct {
	Date        time.Time // parsed kickoff date/time (time component may be zero)
	HasTime     bool      // true when the source provided a time component
	Season      int       // calendar year of the season
	Round       string    // round/rodada label when available
	Stage       string    // tournament stage (Libertadores: "group stage", etc.)
	Competition string    // canonical competition name (see constants above)
	Source      string    // originating CSV file name

	HomeTeam  string // normalized display name (state suffix stripped)
	AwayTeam  string // normalized display name
	HomeRaw   string // original team string as it appeared in the CSV
	AwayRaw   string
	HomeState string // home team state/country code (from column or name suffix)
	AwayState string // away team state/country code

	HomeGoals int
	AwayGoals int

	Stadium string // stadium / arena when available

	// Extended statistics (only populated by BR-Football-Dataset.csv).
	HasStats   bool
	HomeShots  int
	AwayShots  int
	HomeCorner int
	AwayCorner int
	HomeAttack int
	AwayAttack int
}

// Winner returns "home", "away" or "draw" for the match result.
func (m Match) Winner() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return "home"
	case m.AwayGoals > m.HomeGoals:
		return "away"
	default:
		return "draw"
	}
}

// TotalGoals returns the combined goal count of the match.
func (m Match) TotalGoals() int { return m.HomeGoals + m.AwayGoals }

// Player is a single FIFA player record.
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string
	Jersey      string
	Height      string
	Weight      string
}
