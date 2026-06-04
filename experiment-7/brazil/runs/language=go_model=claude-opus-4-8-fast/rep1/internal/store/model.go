// Package store loads the Brazilian soccer datasets (matches + FIFA players)
// from the bundled Kaggle CSV files and exposes query helpers used by the MCP
// tool layer.
//
// Context:
//   - Data sources live in data/kaggle/*.csv (see README.md for licenses).
//   - Six CSV files are normalized into two in-memory collections: Matches and
//     Players. All lookups are performed against these slices; the dataset is
//     small enough (~24k matches, ~18k players) to keep entirely in memory.
//   - Team names appear in many forms across files ("Palmeiras-SP",
//     "Palmeiras", "São Paulo"). NormalizeTeam folds accents / strips state &
//     country suffixes so queries match consistently.
//
// This file defines the core data model types shared across the package.
package store

import "time"

// Competition labels used to tag matches by their source dataset.
const (
	CompBrasileirao  = "Brasileirão Série A"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Match is the unified representation of a single fixture from any dataset.
type Match struct {
	Competition string    // e.g. "Brasileirão Série A"
	Date        time.Time // zero value when the source has no parseable date
	HasDate     bool
	Season      int    // year of the season (0 when unknown)
	Round       string // round number/label when available
	Stage       string // tournament stage (Libertadores)
	HomeTeam    string // display name as it appears in the dataset
	AwayTeam    string
	HomeState   string // home team state abbreviation when available (e.g. "MG")
	AwayState   string // away team state abbreviation when available
	HomeGoals   int
	AwayGoals   int
	HasScore    bool
	Arena       string // stadium when available
	Source      string // originating dataset filename
}

// Result returns "home", "away", or "draw" from the home team's perspective.
func (m Match) Result() string {
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

// Player is a single row from the FIFA player database.
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string
	JerseyNum   string
	Height      string
	Weight      string
}

// TeamRecord aggregates win/draw/loss and goal stats for a team.
type TeamRecord struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

// Points returns the standard 3-1-0 points total.
func (r TeamRecord) Points() int { return r.Wins*3 + r.Draws }

// WinRate returns wins as a fraction of matches played (0 when none played).
func (r TeamRecord) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Matches)
}

// GoalDiff returns goals for minus goals against.
func (r TeamRecord) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }
