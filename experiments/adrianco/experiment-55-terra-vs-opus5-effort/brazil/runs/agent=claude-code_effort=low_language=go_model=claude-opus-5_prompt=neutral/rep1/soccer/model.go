// model.go defines the entities of the knowledge graph: matches (edges between
// two team nodes, tagged with a competition and season) and players (nodes
// attached to a club node).
package soccer

import (
	"strings"
	"time"
)

// Competition names used throughout the server.
const (
	CompSerieA       = "Brasileirão Série A"
	CompSerieB       = "Brasileirão Série B"
	CompSerieC       = "Brasileirão Série C"
	CompCopaBrasil   = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// MatchStats holds the extended per match counters that are only available in
// the BR-Football dataset.
type MatchStats struct {
	HomeCorners int `json:"home_corners"`
	AwayCorners int `json:"away_corners"`
	HomeShots   int `json:"home_shots"`
	AwayShots   int `json:"away_shots"`
	HomeAttacks int `json:"home_attacks"`
	AwayAttacks int `json:"away_attacks"`
}

// Match is one played fixture. Team names are stored both as displayed and as
// canonical keys so that queries can match across datasets.
type Match struct {
	Date        time.Time `json:"-"`
	DateString  string    `json:"date"`
	HasTime     bool      `json:"-"`
	Competition string    `json:"competition"`
	Season      int       `json:"season"`
	Round       string    `json:"round,omitempty"`
	Stage       string    `json:"stage,omitempty"`
	Venue       string    `json:"venue,omitempty"`

	HomeTeam  string `json:"home_team"`
	AwayTeam  string `json:"away_team"`
	HomeState string `json:"home_state,omitempty"`
	AwayState string `json:"away_state,omitempty"`
	HomeGoals int    `json:"home_goals"`
	AwayGoals int    `json:"away_goals"`

	HomeKey string `json:"-"`
	AwayKey string `json:"-"`

	Sources []string    `json:"sources"`
	Stats   *MatchStats `json:"stats,omitempty"`
}

// Involves reports whether the canonical key k played in the match.
func (m *Match) Involves(k string) bool { return m.HomeKey == k || m.AwayKey == k }

// WinnerKey returns the canonical key of the winner, or "" for a draw.
func (m *Match) WinnerKey() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return m.HomeKey
	case m.AwayGoals > m.HomeGoals:
		return m.AwayKey
	default:
		return ""
	}
}

// GoalDiff is the absolute margin of the result.
func (m *Match) GoalDiff() int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}

// Player is a FIFA database entry.
type Player struct {
	ID            int            `json:"id"`
	Name          string         `json:"name"`
	Age           int            `json:"age"`
	Nationality   string         `json:"nationality"`
	Overall       int            `json:"overall"`
	Potential     int            `json:"potential"`
	Club          string         `json:"club"`
	ClubKey       string         `json:"-"`
	Position      string         `json:"position,omitempty"`
	JerseyNumber  int            `json:"jersey_number,omitempty"`
	Height        string         `json:"height,omitempty"`
	Weight        string         `json:"weight,omitempty"`
	Value         string         `json:"value,omitempty"`
	Wage          string         `json:"wage,omitempty"`
	PreferredFoot string         `json:"preferred_foot,omitempty"`
	Skills        map[string]int `json:"skills,omitempty"`
}

// IsBrazilian reports whether the player's nationality is Brazil.
func (p *Player) IsBrazilian() bool { return FoldAccents(p.Nationality) == "brazil" }

// positionGroups maps a broad position word to the FIFA position codes it
// covers, so "forward" or "goalkeeper" can be used as a filter.
var positionGroups = map[string][]string{
	"goalkeeper": {"GK"},
	"defender":   {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
	"midfielder": {"CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"},
	"forward":    {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"},
	"attacker":   {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"},
	"striker":    {"ST", "LS", "RS", "CF"},
}

// PositionMatches reports whether a player's position code satisfies a filter
// that may be either an exact code ("LW") or a group name ("forward").
func PositionMatches(filter, code string) bool {
	f := strings.ToLower(strings.TrimSpace(filter))
	if f == "" {
		return true
	}
	c := strings.ToUpper(strings.TrimSpace(code))
	if strings.EqualFold(f, c) {
		return true
	}
	for _, g := range positionGroups[f] {
		if g == c {
			return true
		}
	}
	return false
}

// competitionAliases maps user phrasing onto canonical competition names. The
// order matters: the first alias contained in the query wins, so more specific
// aliases are listed first.
var competitionAliases = []struct{ alias, comp string }{
	{"brasileirao serie a", CompSerieA},
	{"campeonato brasileiro", CompSerieA},
	{"copa libertadores", CompLibertadores},
	{"copa do brasil", CompCopaBrasil},
	{"brazilian cup", CompCopaBrasil},
	{"libertadores", CompLibertadores},
	{"brasileirao", CompSerieA},
	{"serie a", CompSerieA},
	{"serie b", CompSerieB},
	{"serie c", CompSerieC},
	{"cup", CompCopaBrasil},
}

// ResolveCompetition maps free text onto a canonical competition name.
// It returns "" when the text does not name a known competition.
func ResolveCompetition(s string) string {
	f := strings.Join(strings.Fields(FoldAccents(s)), " ")
	if f == "" {
		return ""
	}
	for _, a := range competitionAliases {
		if strings.Contains(f, a.alias) || strings.Contains(a.alias, f) {
			return a.comp
		}
	}
	return ""
}
