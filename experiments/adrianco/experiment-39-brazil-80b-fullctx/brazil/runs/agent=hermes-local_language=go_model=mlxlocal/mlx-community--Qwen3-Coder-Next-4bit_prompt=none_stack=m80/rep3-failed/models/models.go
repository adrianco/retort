package models

import "time"

// Match represents a soccer match from any dataset
type Match struct {
	ID             int
	Tournament     string
	Date           time.Time
	Season         int
	Round          int
	HomeTeam       string
	AwayTeam       string
	HomeTeamState  string
	AwayTeamState  string
	HomeGoals      int
	AwayGoals      int
	HomeCorners    int
	AwayCorners    int
	HomeAttacks    int
	AwayAttacks    int
	HomeShots      int
	AwayShots      int
	StartTime      string
	HTResult       string
	ATResult       string
	TotalCorners   int
	Stage          string // For Libertadores
	Stadium        string
	Winner         string // "Mandante", "Visitante", "Empate"
	GoalDiff       int
}

// Player represents a FIFA player record
type Player struct {
	ID            int
	Name          string
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	Position      string
	JerseyNum     int
	Height        string
	Weight        string
	// Skill ratings
	Crossing      int
	Finishing     int
	Dribbling     int
	Control       int
	Shooting      int
	Passing       int
	Defense       int
	Physicality   int
	Penalties     int
	FreeKick      int
	Save          int
	Corner        int
	Acceleration  int
	SprintSpeed   int
	Positioning   int
	Reaction      int
	Balanced      int
	Aggression    int
	Interceptions int
	Vision        int
	Composure     int
}

// TeamStats represents aggregated statistics for a team
type TeamStats struct {
	TeamName    string
	Matches     int
	Wins        int
	Draws       int
	Losses      int
	GoalsFor    int
	GoalsAgainst int
	GoalDiff    int
	Points      int
	HomeMatches int
	HomeWins    int
	HomeDraws   int
	HomeLosses  int
	AwayMatches int
	AwayWins    int
	AwayDraws   int
	AwayLosses  int
}

// CompetitionStandings represents league table standings
type CompetitionStandings struct {
	Season       int
	Competition  string
	TeamStats    []TeamStats
}

// HeadToHead represents head-to-head record between two teams
type HeadToHead struct {
	Team1       string
	Team2       string
	Matches     []Match
	Team1Wins   int
	Team2Wins   int
	Draws       int
	Team1Goals  int
	Team2Goals  int
}

// SearchQuery represents a natural language query
type SearchQuery struct {
	Query        string
	EntityType   string // "match", "player", "team", "competition"
	Parameters   map[string]string
}

// SearchResult represents a query result
type SearchResult struct {
	Matches    []Match
	Players    []Player
	Teams      []TeamStats
	Standings  []CompetitionStandings
	HeadToHeads []HeadToHead
	Count      int
}

// MCPResponse represents the MCP server response format
type MCPResponse struct {
	Success   bool        `json:"success"`
	Error     string      `json:"error,omitempty"`
	Data      interface{} `json:"data,omitempty"`
	Metadata  Metadata    `json:"metadata,omitempty"`
}

// Metadata contains response metadata
type Metadata struct {
	Timestamp string `json:"timestamp"`
	Duration  string `json:"duration,omitempty"`
	Source    string `json:"source,omitempty"`
}

// DataStore holds all loaded data
type DataStore struct {
	BrasileiraoMatches   []Match
	CopaDoBrasilMatches  []Match
	LibertadoresMatches  []Match
	ExtendedMatches      []Match
	HistoricalMatches    []Match
	Players              []Player
	TeamAliases          map[string]string // Normalize team names
}

// NewDataStore creates a new empty data store
func NewDataStore() *DataStore {
	return &DataStore{
		TeamAliases: make(map[string]string),
	}
}
