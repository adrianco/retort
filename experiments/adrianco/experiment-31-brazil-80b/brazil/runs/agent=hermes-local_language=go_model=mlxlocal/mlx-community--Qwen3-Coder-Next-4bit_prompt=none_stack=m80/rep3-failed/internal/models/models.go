// Package models contains data structures for the Brazilian Soccer MCP Server
package models

import (
	"regexp"
	"strings"
	"time"
)

// Match represents a soccer match from any dataset
type Match struct {
	ID                int
	Datetime          time.Time
	HomeTeam          string
	HomeTeamState     string
	AwayTeam          string
	AwayTeamState     string
	HomeGoal          int
	AwayGoal          int
	Season            int
	Round             int
	Competition       string // Brasileirao, CopaDoBrasil, Libertadores, Extended
	Stage             string // For Libertadores
	HomeCorner        int
	AwayCorner        int
	HomeAttack        int
	AwayAttack        int
	HomeShots         int
	AwayShots         int
	Time              string // Kick-off time
	Date              time.Time
	HtResult          string // Half-time result
	AtResult          string // Full-time result
	TotalCorners      int
	TeamName          string // Normalized team name
	TeamState         string // Normalized team state
	OpponentName      string // Normalized opponent name
	OpponentState     string // Normalized opponent state
	TeamGoals         int    // Goals for the specified team
	TeamOpponentGoals int    // Goals against the specified team
}

// Team represents a soccer team
type Team struct {
	Name           string
	State          string
	Matches        int
	Wins           int
	Draws          int
	Losses         int
	GoalsFor       int
	GoalsAgainst   int
	Points         int
	Competition    string
	Season         int
}

// Player represents a FIFA player record
type Player struct {
	ID                    int
	Name                  string
	Age                   int
	Nationality           string
	Overall               int
	Potential             int
	Club                  string
	Position              string
	JerseyNumber          int
	Height                string
	Weight                string
	PreferredFoot         string
	InternationalReputation int
	WeakFoot              int
	SkillMoves            int
	WorkRate              string
	BodyType              string
	PositionLS            int
	PositionST            int
	PositionRS            int
	PositionLW            int
	PositionLF            int
	PositionCF            int
	PositionRF            int
	PositionRW            int
	PositionLAM           int
	PositionCAM           int
	PositionRAM           int
	PositionLM            int
	PositionLCM           int
	PositionCM            int
	PositionRCM           int
	PositionRM            int
	PositionLWB           int
	PositionLDM           int
	PositionCDM           int
	PositionRDM           int
	PositionRWB           int
	PositionLB            int
	PositionLCB           int
	PositionCB            int
	PositionRCB           int
	PositionRB            int
	Crossing              int
	Finishing             int
	HeadingAccuracy       int
	ShortPassing          int
	Volleys               int
	Dribbling             int
	Curve                 int
	FKAccuracy            int
	LongPassing           int
	BallControl           int
	Acceleration          int
	SprintSpeed           int
	Agility               int
	Reactions             int
	Balance               int
	ShotPower             int
	Jumping               int
	Stamina               int
	Strength              int
	LongShots             int
	Aggression            int
	Interceptions         int
	Positioning           int
	Vision                int
	Penalties             int
	Composure             int
	Marking               int
	StandingTackle        int
	SlidingTackle         int
	GKDiving              int
	GKHandling            int
	GKKicking             int
	GKPositioning         int
	GKReflexes            int
	ReleaseClause         string
}

// CompetitionResult represents standings for a competition
type CompetitionResult struct {
	Team           string
	Matches        int
	Wins           int
	Draws          int
	Losses         int
	GoalsFor       int
	GoalsAgainst   int
	GoalDifference int
	Points         int
	Season         int
	Competition    string
}

// QueryRequest represents a query from the MCP client
type QueryRequest struct {
	Type    string                 // match, team, player, competition, statistics
	Params  map[string]interface{} // Query parameters
}

// QueryResponse represents a response to a query
type QueryResponse struct {
	Success bool        `json:"success"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
	Total   int         `json:"total"`
	Page    int         `json:"page"`
	PageSize int         `json:"pageSize"`
	Error   string      `json:"error,omitempty"`
}

// TeamStats represents statistics for a team
type TeamStats struct {
	Team          string
	Competition   string
	Season        int
	Matches       int
	Wins          int
	Draws         int
	Losses        int
	GoalsFor      int
	GoalsAgainst  int
	Points        int
	WinRate       float64
	HomeWins      int
	HomeLosses    int
	HomeDraws     int
	AwayWins      int
	AwayLosses    int
	AwayDraws     int
}

// HeadToHead represents head-to-head records between two teams
type HeadToHead struct {
	Team1         string
	Team2         string
	Matches       []Match
	Team1Wins     int
	Team2Wins     int
	Draws         int
	Team1Goals    int
	Team2Goals    int
}

// BigWin represents a large victory in a match
type BigWin struct {
	Match          Match
	GoalDifference int
}

// TopScorer represents top scorers (inferred from match data)
type TopScorer struct {
	PlayerName    string
	Team          string
	Goals         int
	Matches       int
}

// MatchFilter represents filter criteria for match queries
type MatchFilter struct {
	HomeTeam      string
	AwayTeam      string
	Competition   string
	Season        int
	Round         int
	StartDate     time.Time
	EndDate       time.Time
	Page          int
	PageSize      int
}

// NormalizeTeamName normalizes team names by removing state suffixes
func NormalizeTeamName(name string) string {
	// Pattern: dash followed by 2 uppercase letters
	re := regexp.MustCompile(`-[A-Z]{2}$`)
	return re.ReplaceAllString(name, "")
}

// GetTeamNameWithoutState extracts team name without state suffix
func GetTeamNameWithoutState(name string) string {
	// Handle various formats
	// "Palmeiras-SP" -> "Palmeiras"
	// "Flamengo-RJ" -> "Flamengo"
	// "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ" -> "Boavista Sport Club"
	
	// Try to find " - XX" pattern first
	re := regexp.MustCompile(`\s+-\s+[A-Z]{2}$`)
	if re.MatchString(name) {
		return strings.TrimSpace(re.ReplaceAllString(name, ""))
	}
	
	// Try "XX-XX" pattern
	re2 := regexp.MustCompile(`-[A-Z]{2}$`)
	if re2.MatchString(name) {
		return strings.TrimSpace(re2.ReplaceAllString(name, ""))
	}
	
	return name
}

// GetTeamState extracts state from team name
func GetTeamState(name string) string {
	re := regexp.MustCompile(`-([A-Z]{2})$`)
	matches := re.FindStringSubmatch(name)
	if len(matches) == 2 {
		return matches[1]
	}
	return ""
}
