// model.go defines the core data types of the knowledge graph (matches,
// players and the team registry) plus the canonical competition names.
package soccer

import (
	"sort"
	"time"
)

// Canonical competition names.
const (
	CompBrasileiraoA = "Brasileirão Série A"
	CompBrasileiraoB = "Brasileirão Série B"
	CompBrasileiraoC = "Brasileirão Série C"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Match is a single normalized fixture, merged from any of the source files.
type Match struct {
	Competition string
	Season      int
	Round       string // round number/name where available
	Stage       string // tournament stage (Libertadores) where available
	Stadium     string // arena where available

	Date    time.Time
	HasDate bool

	HomeKey string // canonical key for the home team
	AwayKey string // canonical key for the away team

	// Intermediate fields populated during loading and resolved into the
	// canonical keys above by finalizeTeams.
	homeBase, homeRegion, homeDisplay string
	awayBase, awayRegion, awayDisplay string

	HomeGoals int
	AwayGoals int
	HasScore  bool

	// Optional extended statistics (only the BR-Football dataset provides these).
	HomeShots, AwayShots     int
	HomeCorners, AwayCorners int
	HasStats                 bool

	Source string // originating CSV file
}

// Winner returns "home", "away" or "draw" for a match with a known score.
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

// Player is a row from the FIFA player database.
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

// DB is the loaded, queryable knowledge graph.
type DB struct {
	Matches []Match
	Players []Player

	// teams maps a canonical team key to the best display name observed.
	teams map[string]string
	// playerClubKey -> nothing; clubs are matched on the fly.
}

// newDB returns an empty database ready to be populated.
func newDB() *DB {
	return &DB{teams: make(map[string]string)}
}

// TeamDisplay returns the canonical display name for a team key.
func (db *DB) TeamDisplay(key string) string {
	if d, ok := db.teams[key]; ok {
		return d
	}
	return key
}

// queryDisplay returns a friendly display name for a user-supplied team query
// whose normalized key may not be registered verbatim (e.g. the region-less
// "atletico"). It prefers an exact registry hit, then the cleaned raw query.
func (db *DB) queryDisplay(raw, key string) string {
	if d, ok := db.teams[key]; ok {
		return d
	}
	if c := CleanTeamName(raw); c != "" {
		return c
	}
	return key
}

// TeamCount returns the number of distinct teams in the graph.
func (db *DB) TeamCount() int { return len(db.teams) }

// Competitions returns the sorted list of distinct competition names.
func (db *DB) Competitions() []string {
	set := map[string]bool{}
	for _, m := range db.Matches {
		set[m.Competition] = true
	}
	out := make([]string, 0, len(set))
	for c := range set {
		out = append(out, c)
	}
	sort.Strings(out)
	return out
}
