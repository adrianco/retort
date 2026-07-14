package soccer

import "time"

// Competition name constants used to label matches loaded from the
// single-competition datasets.
const (
	CompBrasileirao  = "Brasileirão"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Libertadores"
)

// Match is a normalized representation of a single fixture drawn from any of
// the match datasets. Not every field is populated by every source; HasScore
// and HasDate indicate whether the corresponding values are present.
type Match struct {
	Competition string
	Season      int
	Round       string
	Stage       string

	Date    time.Time
	HasDate bool

	HomeTeam string
	AwayTeam string

	HomeGoals int
	AwayGoals int
	HasScore  bool

	Stadium string
	Source  string // originating dataset file

	// Extended statistics (BR-Football dataset only).
	HomeCorners int
	AwayCorners int
	HomeShots   int
	AwayShots   int
}

// Player is a normalized FIFA player record.
type Player struct {
	ID           int
	Name         string
	Age          int
	Nationality  string
	Overall      int
	Potential    int
	Club         string
	Position     string
	JerseyNumber string
	Height       string
	Weight       string
}

// KB is the in-memory knowledge base: all matches and players loaded from the
// provided datasets.
type KB struct {
	Matches []Match
	Players []Player
}
