// Package soccer implements the Brazilian football knowledge graph that backs
// the MCP server.
//
// Context
//
//	The package loads six Kaggle CSV datasets (five match datasets and one FIFA
//	player dataset, see data/kaggle) into an in-memory knowledge graph:
//
//	    Club ──home_of/away_of──▶ Match ──part_of──▶ Competition/Season
//	    Club ◀──plays_for── Player
//	    Match ──played_at──▶ Stadium
//
//	The datasets overlap heavily (Série A 2012-2019 appears in three files) and
//	spell team names inconsistently ("Palmeiras-SP", "Palmeiras - SP",
//	"Palmeiras"), so loading is a two pass process: pass one harvests every raw
//	team spelling and resolves it to a canonical club identity (see
//	normalize.go and clubs.go), pass two builds matches and de-duplicates
//	fixtures that appear in more than one source (see graph.go).
//
//	This file defines the node/edge types of the graph. Everything here is
//	plain data so that it can be marshalled straight into MCP structured tool
//	output.
package soccer

import (
	"fmt"
	"strings"
	"time"
)

// Competition is the canonical name of a tournament in the knowledge graph.
type Competition string

// The competitions covered by the bundled datasets.
const (
	SerieA       Competition = "Brasileirão Série A"
	SerieB       Competition = "Brasileirão Série B"
	SerieC       Competition = "Brasileirão Série C"
	CopaDoBrasil Competition = "Copa do Brasil"
	Libertadores Competition = "Copa Libertadores"
)

// AllCompetitions lists every competition the graph knows about, in a stable
// order suitable for display.
var AllCompetitions = []Competition{SerieA, SerieB, SerieC, CopaDoBrasil, Libertadores}

// Club is a team node. ID is a stable slug such as "flamengo-rj" or
// "atletico-mg"; clubs whose short name is ambiguous carry the state (or, for
// non-Brazilian clubs in the Libertadores, the country) in the slug.
type Club struct {
	ID      string   `json:"id"`
	Name    string   `json:"name"`
	State   string   `json:"state,omitempty"`
	Country string   `json:"country,omitempty"`
	Aliases []string `json:"aliases,omitempty"`
	Matches int      `json:"matches"`

	// Search indexes, precomputed at load time so that fuzzy club search does
	// not re-normalize every alias of every club on every keystroke.
	sortName   string
	aliasNames []string
	aliasBases []string
}

// Label renders a club with its state so that "Atlético (MG)" is
// distinguishable from "Atlético (PR)".
func (c *Club) Label() string {
	if c == nil {
		return "Unknown"
	}
	if c.State == "" {
		return c.Name
	}
	return fmt.Sprintf("%s (%s)", c.Name, c.State)
}

// ExtendedStats holds the per-match detail that only the
// BR-Football-Dataset.csv source provides. Fields are pointers because the
// source leaves many of them blank.
type ExtendedStats struct {
	HomeCorners  *int   `json:"home_corners,omitempty"`
	AwayCorners  *int   `json:"away_corners,omitempty"`
	TotalCorners *int   `json:"total_corners,omitempty"`
	HomeShots    *int   `json:"home_shots,omitempty"`
	AwayShots    *int   `json:"away_shots,omitempty"`
	HomeAttacks  *int   `json:"home_attacks,omitempty"`
	AwayAttacks  *int   `json:"away_attacks,omitempty"`
	HomeResult   string `json:"home_half_time_result,omitempty"`
	AwayResult   string `json:"away_half_time_result,omitempty"`
	KickOff      string `json:"kick_off,omitempty"`
}

// Match is the central edge of the graph: it connects two clubs to a
// competition, a season and a date.
type Match struct {
	ID          string         `json:"id"`
	Competition Competition    `json:"competition"`
	Season      int            `json:"season"`
	Round       string         `json:"round,omitempty"`
	Stage       string         `json:"stage,omitempty"`
	Date        time.Time      `json:"date"`
	HasTime     bool           `json:"-"`
	HasDate     bool           `json:"-"`
	HomeClubID  string         `json:"home_club_id"`
	AwayClubID  string         `json:"away_club_id"`
	HomeTeam    string         `json:"home_team"`
	AwayTeam    string         `json:"away_team"`
	HomeGoals   int            `json:"home_goals"`
	AwayGoals   int            `json:"away_goals"`
	HasScore    bool           `json:"played"`
	Stadium     string         `json:"stadium,omitempty"`
	Sources     []string       `json:"sources,omitempty"`
	Stats       *ExtendedStats `json:"stats,omitempty"`
}

// DateString formats the match date, falling back to "unknown date" for the
// handful of rows with no usable timestamp.
func (m *Match) DateString() string {
	if !m.HasDate {
		return "unknown date"
	}
	return m.Date.Format("2006-01-02")
}

// Outcome reports "home", "away" or "draw"; it returns "" when the match has
// no recorded score.
func (m *Match) Outcome() string {
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

// WinnerClubID returns the winning club ID, or "" for a draw or unplayed match.
func (m *Match) WinnerClubID() string {
	switch m.Outcome() {
	case "home":
		return m.HomeClubID
	case "away":
		return m.AwayClubID
	}
	return ""
}

// TotalGoals is the combined score, valid only when HasScore is true.
func (m *Match) TotalGoals() int { return m.HomeGoals + m.AwayGoals }

// GoalDifference is the absolute margin of victory.
func (m *Match) GoalDifference() int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}

// Involves reports whether the club took part in the match.
func (m *Match) Involves(clubID string) bool {
	return m.HomeClubID == clubID || m.AwayClubID == clubID
}

// Opponent returns the other club's ID.
func (m *Match) Opponent(clubID string) string {
	if m.HomeClubID == clubID {
		return m.AwayClubID
	}
	return m.HomeClubID
}

// ScoreLine renders "Flamengo 2-1 Fluminense".
func (m *Match) ScoreLine() string {
	if !m.HasScore {
		return fmt.Sprintf("%s vs %s (no score recorded)", m.HomeTeam, m.AwayTeam)
	}
	return fmt.Sprintf("%s %d-%d %s", m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam)
}

// Context renders the competition/season/round part of a match description.
func (m *Match) Context() string {
	parts := []string{string(m.Competition), fmt.Sprint(m.Season)}
	switch {
	case m.Stage != "":
		parts = append(parts, m.Stage)
	case m.Round != "":
		parts = append(parts, "Round "+m.Round)
	}
	return strings.Join(parts, " ")
}

// Describe renders a full one-line summary of the match.
func (m *Match) Describe() string {
	return fmt.Sprintf("%s: %s (%s)", m.DateString(), m.ScoreLine(), m.Context())
}

// Player is a node sourced from the FIFA player dataset.
type Player struct {
	ID            int            `json:"id"`
	Name          string         `json:"name"`
	Age           int            `json:"age"`
	Nationality   string         `json:"nationality"`
	Overall       int            `json:"overall"`
	Potential     int            `json:"potential"`
	Club          string         `json:"club,omitempty"`
	ClubID        string         `json:"club_id,omitempty"`
	Position      string         `json:"position,omitempty"`
	PositionGroup string         `json:"position_group,omitempty"`
	JerseyNumber  int            `json:"jersey_number,omitempty"`
	Height        string         `json:"height,omitempty"`
	Weight        string         `json:"weight,omitempty"`
	Value         string         `json:"value,omitempty"`
	Wage          string         `json:"wage,omitempty"`
	PreferredFoot string         `json:"preferred_foot,omitempty"`
	WorkRate      string         `json:"work_rate,omitempty"`
	Skills        map[string]int `json:"skills,omitempty"`
}

// Describe renders a one-line player summary.
func (p *Player) Describe() string {
	club := p.Club
	if club == "" {
		club = "no club"
	}
	pos := p.Position
	if pos == "" {
		pos = "?"
	}
	return fmt.Sprintf("%s - Overall: %d, Potential: %d, Position: %s, Club: %s, Age: %d, Nationality: %s",
		p.Name, p.Overall, p.Potential, pos, club, p.Age, p.Nationality)
}

// DatasetInfo records provenance for one loaded CSV file.
type DatasetInfo struct {
	File         string   `json:"file"`
	Description  string   `json:"description"`
	License      string   `json:"license"`
	Source       string   `json:"source"`
	Rows         int      `json:"rows"`
	Loaded       int      `json:"loaded"`
	Rejected     int      `json:"rejected,omitempty"`
	Competitions []string `json:"competitions,omitempty"`
	SeasonMin    int      `json:"season_min,omitempty"`
	SeasonMax    int      `json:"season_max,omitempty"`
}
