// model.go - core domain types for the Brazilian Soccer knowledge graph.
//
// Context
// -------
// The MCP server unifies six heterogeneous CSV datasets (five match files and
// one FIFA player file) into two flat in-memory collections: []*Match and
// []*Player held by a *DB. Every match, regardless of its source file, is
// projected onto the common Match struct so that queries can run uniformly
// across competitions. Source-specific extras (corners, shots, stadium, ...)
// are kept as optional fields and simply left zero/empty when a dataset does
// not provide them.
//
// Competitions are bucketed into canonical keys (see competitions below) so the
// same fixture appearing in more than one dataset can be de-duplicated and so
// that standings/statistics never double count.
package soccer

import "time"

// Canonical competition identifiers. Several datasets describe the same
// competition under different labels ("Serie A" vs "Brasileirão"); these keys
// give us a single bucket per real-world competition.
const (
	CompBrasileirao  = "brasileirao"
	CompCopaDoBrasil = "copa_do_brasil"
	CompLibertadores = "libertadores"
	CompSerieB       = "serie_b"
	CompSerieC       = "serie_c"
	CompOther        = "other"
)

// competitionNames maps canonical keys to their display names.
var competitionNames = map[string]string{
	CompBrasileirao:  "Brasileirão Série A",
	CompCopaDoBrasil: "Copa do Brasil",
	CompLibertadores: "Copa Libertadores",
	CompSerieB:       "Brasileirão Série B",
	CompSerieC:       "Brasileirão Série C",
	CompOther:        "Other",
}

// CompetitionName returns the display name for a canonical competition key.
func CompetitionName(key string) string {
	if n, ok := competitionNames[key]; ok {
		return n
	}
	return key
}

// Match is the unified representation of a single fixture.
type Match struct {
	Date    time.Time // parsed kickoff date (zero if unknown)
	HasDate bool      // true when Date was successfully parsed
	HasTime bool      // true when a wall-clock time was present

	Competition string // canonical competition key (CompBrasileirao, ...)
	Source      string // originating dataset file name (for provenance)

	HomeTeam string // canonical home team display name
	AwayTeam string // canonical away team display name
	HomeRaw  string // original home team string as found in the CSV
	AwayRaw  string // original away team string as found in the CSV

	HomeGoals int
	AwayGoals int
	HasScore  bool // false when the source row lacked a usable score

	Season int    // year of the season/edition
	Round  string // round/matchday label (free form)
	Stage  string // tournament stage, e.g. "group stage", "final"
	Arena  string // stadium name when known

	// Optional extended statistics (BR-Football-Dataset). Zero when absent.
	HomeCorners int
	AwayCorners int
	HomeShots   int
	AwayShots   int
	HomeAttacks int
	AwayAttacks int
	HasExtended bool
}

// Winner returns "home", "away" or "draw" for a scored match. For matches
// without a score it returns the empty string.
func (m *Match) Winner() string {
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

// TotalGoals returns the combined goals in the match (0 when unscored).
func (m *Match) TotalGoals() int {
	if !m.HasScore {
		return 0
	}
	return m.HomeGoals + m.AwayGoals
}

// DateString renders the match date in ISO form, including the time component
// when one was present. Returns "unknown date" when no date was parsed.
func (m *Match) DateString() string {
	if !m.HasDate {
		return "unknown date"
	}
	if m.HasTime {
		return m.Date.Format("2006-01-02 15:04")
	}
	return m.Date.Format("2006-01-02")
}

// Player is the subset of FIFA attributes we expose for player queries.
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

	// A handful of underlying FIFA skill ratings useful for richer answers.
	Finishing      int
	ShortPassing   int
	Dribbling      int
	BallControl    int
	SprintSpeed    int
	StandingTackle int
}

// DB is the loaded, queryable knowledge graph.
type DB struct {
	Matches []*Match
	Players []*Player
}
