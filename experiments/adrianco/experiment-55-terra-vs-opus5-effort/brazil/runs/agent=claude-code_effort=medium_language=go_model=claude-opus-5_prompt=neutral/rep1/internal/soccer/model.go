// Package soccer holds the in-memory knowledge graph built from the Kaggle
// CSV files, plus the query layer that the MCP tools expose.
package soccer

import (
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/normalize"
)

// Competition names are canonicalised across datasets so that the same
// tournament loaded from two files ends up under one label.
const (
	SerieA       = "Brasileirão Série A"
	SerieB       = "Brasileirão Série B"
	SerieC       = "Brasileirão Série C"
	CopaDoBrasil = "Copa do Brasil"
	Libertadores = "Copa Libertadores"
)

// TeamRef is a canonical club reference embedded in a match.
type TeamRef struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	State string `json:"state,omitempty"`
	Raw   string `json:"raw,omitempty"` // spelling as it appeared in the CSV
}

// MatchStats carries the extended per-match numbers that only the
// BR-Football-Dataset provides.
type MatchStats struct {
	HomeCorners  int    `json:"home_corners"`
	AwayCorners  int    `json:"away_corners"`
	HomeShots    int    `json:"home_shots"`
	AwayShots    int    `json:"away_shots"`
	HomeAttacks  int    `json:"home_attacks"`
	AwayAttacks  int    `json:"away_attacks"`
	TotalCorners int    `json:"total_corners"`
	HalfTimeHome string `json:"half_time_home,omitempty"`
	HalfTimeAway string `json:"half_time_away,omitempty"`
}

// Match is one fixture, merged from every dataset that describes it.
type Match struct {
	Competition string      `json:"competition"`
	Season      int         `json:"season"`
	Date        time.Time   `json:"date"`
	KickOff     string      `json:"kick_off,omitempty"`
	Round       string      `json:"round,omitempty"`
	Stage       string      `json:"stage,omitempty"`
	Venue       string      `json:"venue,omitempty"`
	Home        TeamRef     `json:"home"`
	Away        TeamRef     `json:"away"`
	HomeGoals   int         `json:"home_goals"`
	AwayGoals   int         `json:"away_goals"`
	Stats       *MatchStats `json:"stats,omitempty"`
	Sources     []string    `json:"sources"` // CSV files this match came from
}

// Result returns "home", "away" or "draw".
func (m Match) Result() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return "home"
	case m.AwayGoals > m.HomeGoals:
		return "away"
	default:
		return "draw"
	}
}

// TotalGoals is the combined score.
func (m Match) TotalGoals() int { return m.HomeGoals + m.AwayGoals }

// Involves reports whether teamID played in the match.
func (m Match) Involves(teamID string) bool {
	return m.Home.ID == teamID || m.Away.ID == teamID
}

// Winner returns the canonical ID of the winning club, or "" for a draw.
func (m Match) Winner() string {
	switch m.Result() {
	case "home":
		return m.Home.ID
	case "away":
		return m.Away.ID
	}
	return ""
}

// Team is a node in the knowledge graph.
type Team struct {
	ID           string   `json:"id"`
	Name         string   `json:"name"`
	State        string   `json:"state,omitempty"`
	StateName    string   `json:"state_name,omitempty"`
	Aliases      []string `json:"aliases,omitempty"`
	Competitions []string `json:"competitions,omitempty"`
	Seasons      []int    `json:"seasons,omitempty"`
	MatchCount   int      `json:"match_count"`

	matchIdx []int
	aliasSet map[string]bool
}

// Player is a FIFA database entry.
type Player struct {
	ID          int            `json:"id"`
	Name        string         `json:"name"`
	Age         int            `json:"age,omitempty"`
	Nationality string         `json:"nationality,omitempty"`
	Overall     int            `json:"overall,omitempty"`
	Potential   int            `json:"potential,omitempty"`
	Club        string         `json:"club,omitempty"`
	ClubID      string         `json:"club_id,omitempty"`
	Position    string         `json:"position,omitempty"`
	Jersey      int            `json:"jersey_number,omitempty"`
	Value       string         `json:"value,omitempty"`
	Wage        string         `json:"wage,omitempty"`
	Foot        string         `json:"preferred_foot,omitempty"`
	Height      string         `json:"height,omitempty"`
	Weight      string         `json:"weight,omitempty"`
	WorkRate    string         `json:"work_rate,omitempty"`
	Skills      map[string]int `json:"skills,omitempty"`
}

func teamRef(t normalize.Team, raw string) TeamRef {
	return TeamRef{ID: t.ID, Name: t.Name, State: t.State, Raw: raw}
}
