// model.go defines the in-memory data model shared across the query engine.
package soccer

import "time"

// Competition canonical names.
const (
	CompSerieA       = "Brasileirão Série A"
	CompSerieB       = "Brasileirão Série B"
	CompSerieC       = "Brasileirão Série C"
	CompCopaBrasil   = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Match is a single game, unified across every source dataset. Not all fields
// are populated for every source (e.g. stadium only exists in the historical
// Brasileirão file); zero values indicate "unknown".
type Match struct {
	Competition string
	Season      int
	Round       string
	Stage       string
	Date        time.Time
	HasDate     bool
	HomeTeam    string // cleaned display name
	AwayTeam    string // cleaned display name
	HomeRaw     string // original name as found in the source
	AwayRaw     string
	HomeGoals   int
	AwayGoals   int
	HasScore    bool
	Stadium     string
	Source      string // originating CSV file
}

// Result returns "home", "away" or "draw" from the perspective of the result.
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

// DateString renders the match date as YYYY-MM-DD or "?" when unknown.
func (m Match) DateString() string {
	if !m.HasDate {
		return "?"
	}
	return m.Date.Format("2006-01-02")
}

// Player is one row of the FIFA player database. Only the columns relevant to
// the specified query capabilities are retained.
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
}
