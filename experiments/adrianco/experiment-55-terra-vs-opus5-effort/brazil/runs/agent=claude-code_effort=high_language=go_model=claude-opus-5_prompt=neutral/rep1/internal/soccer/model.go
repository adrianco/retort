// model.go defines the node and edge types of the knowledge graph:
// Competition, Team, Match and Player, plus the JSON-facing view types that
// MCP tools return.
package soccer

import (
	"sort"
	"strings"
	"time"
)

// Competition identifiers.
const (
	CompSerieA       = "serie-a"
	CompSerieB       = "serie-b"
	CompSerieC       = "serie-c"
	CompCopaDoBrasil = "copa-do-brasil"
	CompLibertadores = "libertadores"
)

// Competition is a tournament node.
type Competition struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	Kind    string `json:"kind"` // "league" or "knockout"
	Country string `json:"country"`
}

var competitionCatalog = map[string]Competition{
	CompSerieA:       {CompSerieA, "Campeonato Brasileiro Série A", "league", "Brazil"},
	CompSerieB:       {CompSerieB, "Campeonato Brasileiro Série B", "league", "Brazil"},
	CompSerieC:       {CompSerieC, "Campeonato Brasileiro Série C", "league", "Brazil"},
	CompCopaDoBrasil: {CompCopaDoBrasil, "Copa do Brasil", "knockout", "Brazil"},
	CompLibertadores: {CompLibertadores, "Copa Libertadores", "knockout", "South America"},
}

// Team is a club node in the graph.
type Team struct {
	ID      string   `json:"id"`
	Name    string   `json:"name"`
	Base    string   `json:"base"`
	Region  string   `json:"region,omitempty"`
	State   string   `json:"state,omitempty"`   // expanded Brazilian state name
	Country string   `json:"country,omitempty"` // "Brazil" for domestic clubs
	Aliases []string `json:"aliases,omitempty"` // raw spellings seen in the data

	matchCount int
}

// MatchCount is the number of (deduplicated) matches the club appears in.
func (t *Team) MatchCount() int { return t.matchCount }

// MatchStats holds the extended per-match statistics available only in
// BR-Football-Dataset.csv.
type MatchStats struct {
	HomeCorners  int    `json:"home_corners"`
	AwayCorners  int    `json:"away_corners"`
	TotalCorners int    `json:"total_corners"`
	HomeAttacks  int    `json:"home_attacks"`
	AwayAttacks  int    `json:"away_attacks"`
	HomeShots    int    `json:"home_shots"`
	AwayShots    int    `json:"away_shots"`
	HomeHTResult string `json:"home_half_time_result,omitempty"`
	AwayHTResult string `json:"away_half_time_result,omitempty"`
}

// Match is a match node, linked to two Team nodes and one Competition node.
type Match struct {
	ID          string
	Competition string
	Season      int
	Round       int
	Stage       string
	Date        time.Time
	HasTime     bool
	KickOff     string
	HomeTeamID  string
	AwayTeamID  string
	HomeGoals   int
	AwayGoals   int
	Venue       string
	Stats       *MatchStats
	Sources     []string
}

// GoalDiff is the (signed) home-minus-away goal difference.
func (m *Match) GoalDiff() int { return m.HomeGoals - m.AwayGoals }

// TotalGoals is the number of goals scored in the match.
func (m *Match) TotalGoals() int { return m.HomeGoals + m.AwayGoals }

// Involves reports whether teamID played in the match.
func (m *Match) Involves(teamID string) bool {
	return m.HomeTeamID == teamID || m.AwayTeamID == teamID
}

// WinnerID returns the winning team ID, or "" for a draw.
func (m *Match) WinnerID() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return m.HomeTeamID
	case m.AwayGoals > m.HomeGoals:
		return m.AwayTeamID
	}
	return ""
}

// Player is a FIFA player node.
type Player struct {
	ID             int
	Name           string
	Age            int
	Nationality    string
	Overall        int
	Potential      int
	Club           string
	ClubTeamID     string // resolved link into the Team nodes, when possible
	Position       string
	JerseyNumber   int
	Height         string
	Weight         string
	Value          string
	Wage           string
	ValueEUR       float64
	WageEUR        float64
	PreferredFoot  string
	WorkRate       string
	BodyType       string
	Joined         string
	ContractUntil  string
	ReleaseClause  string
	IntlReputation int
	WeakFoot       int
	SkillMoves     int
	Skills         map[string]int
}

// ---------------------------------------------------------------------------
// JSON view types returned by MCP tools.
// ---------------------------------------------------------------------------

// MatchView is the wire representation of a match.
type MatchView struct {
	Date        string      `json:"date"`
	KickOff     string      `json:"kickoff,omitempty"`
	Competition string      `json:"competition"`
	Season      int         `json:"season"`
	Round       int         `json:"round,omitempty"`
	Stage       string      `json:"stage,omitempty"`
	HomeTeam    string      `json:"home_team"`
	AwayTeam    string      `json:"away_team"`
	HomeGoals   int         `json:"home_goals"`
	AwayGoals   int         `json:"away_goals"`
	Score       string      `json:"score"`
	Result      string      `json:"result"` // home_win | away_win | draw
	Venue       string      `json:"venue,omitempty"`
	Stats       *MatchStats `json:"stats,omitempty"`
	Sources     []string    `json:"sources,omitempty"`
	Summary     string      `json:"summary"`
}

// TeamView is the wire representation of a club.
type TeamView struct {
	ID         string   `json:"id"`
	Name       string   `json:"name"`
	State      string   `json:"state,omitempty"`
	Country    string   `json:"country,omitempty"`
	MatchCount int      `json:"match_count"`
	Aliases    []string `json:"aliases,omitempty"`
}

// Record is a win/draw/loss record with the derived points and rates.
type Record struct {
	Played        int     `json:"played"`
	Wins          int     `json:"wins"`
	Draws         int     `json:"draws"`
	Losses        int     `json:"losses"`
	GoalsFor      int     `json:"goals_for"`
	GoalsAgainst  int     `json:"goals_against"`
	GoalDiff      int     `json:"goal_difference"`
	Points        int     `json:"points"`
	WinRate       float64 `json:"win_rate_pct"`
	PointsPerGame float64 `json:"points_per_game"`
}

func (r *Record) add(gf, ga int) {
	r.Played++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
	case gf < ga:
		r.Losses++
	default:
		r.Draws++
	}
}

func (r *Record) finalize() {
	r.GoalDiff = r.GoalsFor - r.GoalsAgainst
	r.Points = r.Wins*3 + r.Draws
	if r.Played > 0 {
		r.WinRate = round1(float64(r.Wins) * 100 / float64(r.Played))
		r.PointsPerGame = round2(float64(r.Points) / float64(r.Played))
	}
}

func round1(v float64) float64 { return float64(int(v*10+0.5)) / 10 }
func round2(v float64) float64 { return float64(int(v*100+0.5)) / 100 }

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

func sortedKeys[V any](m map[string]V) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func pairKey(a, b string) string {
	if a > b {
		a, b = b, a
	}
	return a + "|" + b
}

func addAlias(list []string, s string) []string {
	s = strings.TrimSpace(s)
	if s == "" {
		return list
	}
	for _, v := range list {
		if v == s {
			return list
		}
	}
	return append(list, s)
}
