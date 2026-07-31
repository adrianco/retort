// model.go defines the entities of the knowledge graph: teams, matches,
// players and the value types used to represent optional statistics.
package soccer

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

// Team is a canonical club identity. Every raw spelling found in the CSVs
// resolves to exactly one Team.
type Team struct {
	ID      string   `json:"id"`
	Name    string   `json:"name"`
	State   string   `json:"state,omitempty"`
	Country string   `json:"country,omitempty"`
	Aliases []string `json:"aliases,omitempty"` // raw spellings observed in the data
	Curated bool     `json:"curated,omitempty"` // came from the curated table
	Matches int      `json:"matches,omitempty"` // number of matches in the store
	Sources []string `json:"sources,omitempty"` // datasets the club appears in
	Seasons []int    `json:"seasons,omitempty"` // seasons the club appears in
	CompIDs []string `json:"competitions,omitempty"`
	Squad   int      `json:"squad_size,omitempty"` // players linked from fifa_data.csv
}

// Display returns the preferred human readable name, with the state appended
// when the plain name would be ambiguous.
func (t *Team) Display() string {
	return t.Name
}

// Outcome is the result of a match from the home team's point of view.
type Outcome string

// Match outcomes.
const (
	HomeWin Outcome = "home_win"
	AwayWin Outcome = "away_win"
	Draw    Outcome = "draw"
)

// OptInt is an integer that may be absent (BR-Football-Dataset.csv is missing
// shots and attacks for roughly a quarter of its rows).
type OptInt struct {
	Value int
	Valid bool
}

// MarshalJSON renders an absent value as null.
func (o OptInt) MarshalJSON() ([]byte, error) {
	if !o.Valid {
		return []byte("null"), nil
	}
	return json.Marshal(o.Value)
}

// UnmarshalJSON accepts null or a number.
func (o *OptInt) UnmarshalJSON(b []byte) error {
	if string(b) == "null" {
		o.Value, o.Valid = 0, false
		return nil
	}
	if err := json.Unmarshal(b, &o.Value); err != nil {
		return err
	}
	o.Valid = true
	return nil
}

// String renders the value or "-".
func (o OptInt) String() string {
	if !o.Valid {
		return "-"
	}
	return fmt.Sprint(o.Value)
}

// NewOptInt builds a present value.
func NewOptInt(v int) OptInt { return OptInt{Value: v, Valid: true} }

// ExtendedStats holds the per-match detail that only
// BR-Football-Dataset.csv carries.
type ExtendedStats struct {
	HomeCorners  OptInt `json:"home_corners"`
	AwayCorners  OptInt `json:"away_corners"`
	HomeShots    OptInt `json:"home_shots"`
	AwayShots    OptInt `json:"away_shots"`
	HomeAttacks  OptInt `json:"home_attacks"`
	AwayAttacks  OptInt `json:"away_attacks"`
	TotalCorners OptInt `json:"total_corners"`
	HTHomeResult string `json:"ht_home_result,omitempty"`
	HTAwayResult string `json:"ht_away_result,omitempty"`
}

// Match is one played fixture, merged from every dataset that describes it.
type Match struct {
	ID            string    `json:"id"`
	Date          time.Time `json:"date"`
	HasTime       bool      `json:"-"`
	CompetitionID string    `json:"competition"`
	Season        int       `json:"season"`
	Round         int       `json:"round,omitempty"`
	Stage         string    `json:"stage,omitempty"`

	HomeTeamID string `json:"home_team_id"`
	AwayTeamID string `json:"away_team_id"`
	HomeName   string `json:"home_team"`
	AwayName   string `json:"away_team"`
	HomeGoals  int    `json:"home_goals"`
	AwayGoals  int    `json:"away_goals"`

	Venue   string         `json:"venue,omitempty"`
	Sources []string       `json:"sources"`
	Stats   *ExtendedStats `json:"stats,omitempty"`
}

// Outcome reports who won.
func (m *Match) Outcome() Outcome {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return HomeWin
	case m.AwayGoals > m.HomeGoals:
		return AwayWin
	default:
		return Draw
	}
}

// TotalGoals is the combined score.
func (m *Match) TotalGoals() int { return m.HomeGoals + m.AwayGoals }

// GoalMargin is the absolute goal difference.
func (m *Match) GoalMargin() int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}

// Involves reports whether teamID played in the match.
func (m *Match) Involves(teamID string) bool {
	return m.HomeTeamID == teamID || m.AwayTeamID == teamID
}

// Opponent returns the other team's id, or "" when teamID did not play.
func (m *Match) Opponent(teamID string) string {
	switch teamID {
	case m.HomeTeamID:
		return m.AwayTeamID
	case m.AwayTeamID:
		return m.HomeTeamID
	}
	return ""
}

// GoalsFor returns the goals scored by teamID.
func (m *Match) GoalsFor(teamID string) int {
	if teamID == m.HomeTeamID {
		return m.HomeGoals
	}
	return m.AwayGoals
}

// GoalsAgainst returns the goals conceded by teamID.
func (m *Match) GoalsAgainst(teamID string) int {
	if teamID == m.HomeTeamID {
		return m.AwayGoals
	}
	return m.HomeGoals
}

// ResultFor returns "W", "D" or "L" from teamID's point of view.
func (m *Match) ResultFor(teamID string) string {
	gf, ga := m.GoalsFor(teamID), m.GoalsAgainst(teamID)
	switch {
	case gf > ga:
		return "W"
	case gf < ga:
		return "L"
	default:
		return "D"
	}
}

// Label renders "Flamengo 2-1 Fluminense".
func (m *Match) Label() string {
	return fmt.Sprintf("%s %d-%d %s", m.HomeName, m.HomeGoals, m.AwayGoals, m.AwayName)
}

// DateString renders the ISO date (kick-off time is dropped: only some rows
// carry it).
func (m *Match) DateString() string { return m.Date.Format("2006-01-02") }

// RoundLabel renders the round or stage in a human readable way.
func (m *Match) RoundLabel() string {
	switch {
	case m.Stage != "" && m.Round > 0:
		return fmt.Sprintf("%s, round %d", m.Stage, m.Round)
	case m.Stage != "":
		return m.Stage
	case m.Round > 0:
		return fmt.Sprintf("Round %d", m.Round)
	}
	return ""
}

// Player is one row of fifa_data.csv.
type Player struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	Age         int    `json:"age,omitempty"`
	Nationality string `json:"nationality,omitempty"`
	Overall     int    `json:"overall"`
	Potential   int    `json:"potential,omitempty"`
	Club        string `json:"club,omitempty"`
	TeamID      string `json:"team_id,omitempty"` // linked club when it is in the match data
	Position    string `json:"position,omitempty"`
	Jersey      int    `json:"jersey_number,omitempty"`
	Foot        string `json:"preferred_foot,omitempty"`
	Height      string `json:"height,omitempty"`
	Weight      string `json:"weight,omitempty"`
	Value       string `json:"value,omitempty"`
	Wage        string `json:"wage,omitempty"`
	ReleaseCl   string `json:"release_clause,omitempty"`
	Joined      string `json:"joined,omitempty"`
	ContractEnd string `json:"contract_valid_until,omitempty"`
	WorkRate    string `json:"work_rate,omitempty"`
	skills      []int16
}

// SkillNames lists, in order, the attribute ratings kept for every player.
var SkillNames = []string{
	"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
	"Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
	"Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
	"ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
	"Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
	"Composure", "Marking", "StandingTackle", "SlidingTackle",
	"GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
}

var skillIndex = func() map[string]int {
	m := make(map[string]int, len(SkillNames))
	for i, n := range SkillNames {
		m[n] = i
	}
	return m
}()

// Skill returns one attribute rating.
func (p *Player) Skill(name string) (int, bool) {
	i, ok := skillIndex[name]
	if !ok || i >= len(p.skills) {
		return 0, false
	}
	v := p.skills[i]
	if v < 0 {
		return 0, false
	}
	return int(v), true
}

// Skills returns every attribute rating that is present.
func (p *Player) Skills() map[string]int {
	out := make(map[string]int, len(p.skills))
	for i, v := range p.skills {
		if v >= 0 {
			out[SkillNames[i]] = int(v)
		}
	}
	return out
}

// TopSkills returns the n highest rated attributes, best first.
func (p *Player) TopSkills(n int) []SkillValue {
	all := make([]SkillValue, 0, len(p.skills))
	for i, v := range p.skills {
		if v >= 0 {
			all = append(all, SkillValue{Name: SkillNames[i], Value: int(v)})
		}
	}
	sortSlice(all, func(a, b SkillValue) bool {
		if a.Value != b.Value {
			return a.Value > b.Value
		}
		return a.Name < b.Name
	})
	if n > 0 && len(all) > n {
		all = all[:n]
	}
	return all
}

// SkillValue is a named attribute rating.
type SkillValue struct {
	Name  string `json:"name"`
	Value int    `json:"value"`
}

// IsGoalkeeper reports whether the player's listed position is GK.
func (p *Player) IsGoalkeeper() bool { return strings.EqualFold(p.Position, "GK") }

// PositionGroup buckets the 27 FIFA position codes into
// goalkeeper/defender/midfielder/forward.
func (p *Player) PositionGroup() string { return PositionGroup(p.Position) }

// PositionGroup maps a FIFA position code to a coarse group.
func PositionGroup(pos string) string {
	switch strings.ToUpper(strings.TrimSpace(pos)) {
	case "GK":
		return "goalkeeper"
	case "LB", "LCB", "CB", "RCB", "RB", "LWB", "RWB":
		return "defender"
	case "LDM", "CDM", "RDM", "LM", "LCM", "CM", "RCM", "RM", "LAM", "CAM", "RAM":
		return "midfielder"
	case "LW", "LF", "CF", "RF", "RW", "LS", "ST", "RS":
		return "forward"
	}
	return "unknown"
}

// DatasetInfo describes one source file.
type DatasetInfo struct {
	Key          string   `json:"key"`
	File         string   `json:"file"`
	Description  string   `json:"description"`
	License      string   `json:"license"`
	Rows         int      `json:"rows"`
	Used         int      `json:"rows_used"`
	Competitions []string `json:"competitions,omitempty"`
	SeasonMin    int      `json:"season_min,omitempty"`
	SeasonMax    int      `json:"season_max,omitempty"`
	URL          string   `json:"url"`
}
