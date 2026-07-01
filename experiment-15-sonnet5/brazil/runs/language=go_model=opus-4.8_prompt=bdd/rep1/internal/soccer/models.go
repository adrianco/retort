// Package soccer provides the domain model, data loading and query engine for
// the Brazilian Soccer MCP server.
//
// The package is deliberately free of any transport concerns: it knows nothing
// about MCP or JSON-RPC. It loads the provided Kaggle CSV datasets into an
// in-memory Store and exposes typed query methods (match, team, player,
// competition and statistical queries) on top of that Store. The MCP layer in
// package mcp wires these methods to tool calls.
package soccer

import "time"

// Competition names used as the canonical labels across the datasets.
const (
	CompBrasileirao  = "Brasileirão Série A"
	CompCopaBrasil   = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Result classifies a match outcome from the perspective of a given team.
type Result string

const (
	ResultWin  Result = "win"
	ResultDraw Result = "draw"
	ResultLoss Result = "loss"
)

// Match is a single fixture, normalised across all of the source datasets.
//
// HomeTeam/AwayTeam hold cleaned display names (state/country suffixes removed);
// HomeKey/AwayKey hold the accent-folded lower-case matching keys. Goals are
// integers; Date is best-effort parsed and may be the zero time when a source
// row lacks a usable date. Stat fields are only populated by the extended
// BR-Football dataset and are otherwise -1 to signal "unknown".
type Match struct {
	Competition string
	Season      int
	Round       string
	Stage       string
	Date        time.Time

	HomeTeam string
	AwayTeam string
	HomeKey  string
	AwayKey  string

	HomeGoals int
	AwayGoals int

	// Extended statistics (BR-Football dataset only; -1 when unknown).
	HomeShots   int
	AwayShots   int
	HomeCorners int
	AwayCorners int

	Source string // originating CSV file
}

// Decided reports whether the match has a recorded scoreline.
func (m Match) Decided() bool { return m.HomeGoals >= 0 && m.AwayGoals >= 0 }

// TotalGoals returns the combined goals scored in the match.
func (m Match) TotalGoals() int { return m.HomeGoals + m.AwayGoals }

// ResultFor returns the outcome of the match for the team identified by the
// given matching key, or false if the team did not play in the match.
func (m Match) ResultFor(key string) (Result, bool) {
	switch key {
	case m.HomeKey:
		switch {
		case m.HomeGoals > m.AwayGoals:
			return ResultWin, true
		case m.HomeGoals < m.AwayGoals:
			return ResultLoss, true
		default:
			return ResultDraw, true
		}
	case m.AwayKey:
		switch {
		case m.AwayGoals > m.HomeGoals:
			return ResultWin, true
		case m.AwayGoals < m.HomeGoals:
			return ResultLoss, true
		default:
			return ResultDraw, true
		}
	}
	return "", false
}

// Player is a FIFA-database player row, limited to the attributes the server
// exposes.
type Player struct {
	ID          int
	Name        string
	NameKey     string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	ClubKey     string
	Position    string
	Jersey      int
	Height      string
	Weight      string
}
