// Context: Brazilian Soccer MCP Server.
// File: model.go
// Purpose: Core domain types shared across loaders and queries — Match and
// Player — plus competition name constants. Teams are stored in their cleaned
// display form (suffix stripped, accents preserved); the original raw strings
// are retained for reference.
package soccer

import "time"

// Competition name constants used to label matches from the various sources.
const (
	CompBrasileirao  = "Brasileirão"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Match is a single game from any of the match datasets.
type Match struct {
	Competition string    // e.g. "Brasileirão"
	Season      int       // year
	Round       string    // round/stage label (may be empty)
	Stage       string    // tournament stage (Libertadores)
	Date        time.Time // kick-off; zero when unknown
	HasDate     bool
	HomeTeam    string // cleaned display name
	AwayTeam    string
	HomeRaw     string // original name as it appeared in the source
	AwayRaw     string
	HomeGoals   int
	AwayGoals   int
	HasScore    bool
	Source      string // originating dataset/file
}

// Player is a single entry from the FIFA player database.
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

// Winner returns "home", "away" or "draw" for a match with a known score.
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
