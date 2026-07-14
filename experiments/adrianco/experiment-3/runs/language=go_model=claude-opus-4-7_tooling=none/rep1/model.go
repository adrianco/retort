// Data models for the Brazilian soccer knowledge graph: matches, players and
// the in-memory database that holds them.
package main

import "time"

// Match is a single soccer fixture loaded from one of the CSV datasets.
type Match struct {
	Competition string
	Season      int
	Round       string
	Stage       string
	Stadium     string
	Date        time.Time
	HasDate     bool

	HomeTeam string // display name (accents kept, state/country suffix removed)
	AwayTeam string
	HomeRaw  string // original name as written in the source file
	AwayRaw  string
	HomeID   teamIdentity // normalized identity used for matching and grouping
	AwayID   teamIdentity

	HomeGoal int
	AwayGoal int
	HasScore bool

	// Extended statistics, only present in BR-Football-Dataset.csv.
	HomeShots  int
	AwayShots  int
	HomeCorner int
	AwayCorner int
	HasStats   bool

	Source     string // source CSV file name
	SourcePrio int    // lower wins when deduplicating overlapping sources
}

// GoalMargin is the absolute goal difference of the match.
func (m Match) GoalMargin() int {
	d := m.HomeGoal - m.AwayGoal
	if d < 0 {
		return -d
	}
	return d
}

// Player is a single entry from the FIFA player dataset.
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

// DB is the in-memory knowledge graph queried by the MCP tools.
type DB struct {
	Matches     []Match           // canonical set, deduplicated across sources
	AllMatches  []Match           // every match row, including overlapping sources
	Players     []Player          // FIFA players
	teamDisplay map[string]string // normalized key -> preferred display name
}

// DisplayName returns the best display name known for a team group key.
func (db *DB) DisplayName(groupKey, fallback string) string {
	if d, ok := db.teamDisplay[groupKey]; ok && d != "" {
		return d
	}
	return fallback
}
