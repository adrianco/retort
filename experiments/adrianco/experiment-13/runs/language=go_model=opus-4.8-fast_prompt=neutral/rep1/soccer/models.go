// models.go: data model for the knowledge graph — a unified Match record (the
// five match datasets are normalized into one shape) and a Player record (FIFA
// data). Canonical competition names are defined here too.
package soccer

import "time"

// Canonical competition names. Several datasets describe the same competition
// under different labels (e.g. "Serie A" == Brasileirão Série A); loaders map
// onto these constants so cross-file queries are consistent.
const (
	CompSerieA       = "Brasileirão Série A"
	CompSerieB       = "Brasileirão Série B"
	CompSerieC       = "Brasileirão Série C"
	CompCopaBrasil   = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Match is a single game from any of the match datasets, normalized.
type Match struct {
	Competition string    // canonical competition name
	Date        time.Time // kickoff (or midnight if only a date is known)
	HasTime     bool      // whether Date carries a meaningful time-of-day
	Season      int       // year of the season (0 if unknown)
	Round       string    // league round / cup round label (may be empty)
	Stage       string    // tournament stage, e.g. "group stage", "final"
	HomeTeam    string    // cleaned display name
	AwayTeam    string    // cleaned display name
	HomeKey     string    // normalized matching key
	AwayKey     string    // normalized matching key
	HomeGoals   int
	AwayGoals   int
	Stadium     string // arena/venue if known
	Source      string // originating CSV file

	rawHome string // original home name, before key assignment (set by loader)
	rawAway string // original away name

	// Extended statistics (only set for the BR-Football dataset).
	HasStats    bool
	HomeShots   int
	AwayShots   int
	HomeCorners int
	AwayCorners int
}

// Winner returns the cleaned display name of the winning team, or "" for a draw.
func (m Match) Winner() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return m.HomeTeam
	case m.AwayGoals > m.HomeGoals:
		return m.AwayTeam
	default:
		return ""
	}
}

// Margin returns the absolute goal difference of the match.
func (m Match) Margin() int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}

// Player is a single FIFA-database player record (subset of the columns).
type Player struct {
	ID            int
	Name          string
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	ClubKey       string // normalized club key
	Position      string
	Jersey        string
	Height        string
	Weight        string
	PreferredFoot string
	Value         string
	Wage          string

	NameKey   string // normalized name key
	NationKey string // normalized nationality key
}
