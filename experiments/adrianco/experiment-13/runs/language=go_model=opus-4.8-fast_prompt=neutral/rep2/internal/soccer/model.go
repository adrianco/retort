// Package soccer provides the in-memory knowledge base for Brazilian soccer
// data. It loads the Kaggle CSV datasets described in TASK.md into normalized
// Go structures and exposes query helpers used by the MCP server.
//
// Context: this package is intentionally storage-agnostic and free of any MCP
// concerns. It owns the domain model (Match, Player), the loaders that parse
// each CSV file, the team-name normalization logic that reconciles the many
// naming conventions across datasets, and the query/aggregation functions
// (search, head-to-head, standings, statistics). The MCP transport layer in
// internal/mcp calls into the DB type defined here.
package soccer

import "time"

// Competition names used as the canonical labels across the loaded datasets.
const (
	CompBrasileirao  = "Brasileirão"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Libertadores"
	CompOther        = "Other" // tournaments seen only in BR-Football-Dataset
)

// Match is a single game from any of the match datasets. Team names are stored
// both raw (as they appeared in the source file) and in a cleaned display form;
// HomeKey/AwayKey hold the accent-folded lowercase keys used for matching.
type Match struct {
	Competition string
	Source      string // originating CSV file
	Date        time.Time
	HasDate     bool
	Season      int
	Round       string
	Stage       string

	HomeTeam  string // cleaned display name, e.g. "Palmeiras"
	AwayTeam  string
	HomeRaw   string // original name, e.g. "Palmeiras-SP"
	AwayRaw   string
	HomeKey   string // match key, e.g. "palmeiras"
	AwayKey   string
	HomeState string
	AwayState string
	HomeGoals int
	AwayGoals int
	HasScore  bool
	Stadium   string

	// Extended statistics, populated only from BR-Football-Dataset.csv.
	HasStats    bool
	HomeShots   int
	AwayShots   int
	HomeCorners int
	AwayCorners int
	HomeAttacks int
	AwayAttacks int
}

// Winner returns "home", "away", or "draw" for a match with a score.
func (m Match) Winner() string {
	switch {
	case !m.HasScore:
		return "unknown"
	case m.HomeGoals > m.AwayGoals:
		return "home"
	case m.AwayGoals > m.HomeGoals:
		return "away"
	default:
		return "draw"
	}
}

// Player is a single row from the FIFA player dataset.
type Player struct {
	ID            int
	Name          string
	NameKey       string // accent-folded lowercase for matching
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	ClubKey       string
	Position      string
	JerseyNumber  string
	Height        string
	Weight        string
	PreferredFoot string
	Value         string
	Wage          string
}
