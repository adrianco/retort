package main

// BrasileiraoMatch - Brasileirão Serie A Matches
type BrasileiraoMatch struct {
	Datetime      string
	HomeTeam      string
	HomeTeamState string
	AwayTeam      string
	AwayTeamState string
	HomeGoal      int
	AwayGoal      int
	Season        int
	Round         int
}

// CopaDoBrasilMatch - Brazilian Cup Matches
type CopaDoBrasilMatch struct {
	Round       string
	Datetime    string
	HomeTeam    string
	AwayTeam    string
	HomeGoal    int
	AwayGoal    int
	Season      int
	Competition string
}

// LibertadoresMatch - Copa Libertadores Matches
type LibertadoresMatch struct {
	Datetime    string
	HomeTeam    string
	AwayTeam    string
	HomeGoal    int
	AwayGoal    int
	Season      int
	Stage       string
	Competition string
}

// BRFootballMatch - BR Football Dataset
type BRFootballMatch struct {
	Tournament   string
	HomeTeam     string
	HomeGoal     float64
	AwayGoal     float64
	AwayTeam     string
	HomeCorner   float64
	AwayCorner   float64
	HomeAttack   float64
	AwayAttack   float64
	HomeShots    float64
	AwayShots    float64
	Time         string
	Date         string
	HTDiff       float64
	ATDiff       float64
	HTResult     string
	ATResult     string
	TotalCorners float64
}

// NovoCampeonatoMatch - Novo Campeonato Brasileiro
type NovoCampeonatoMatch struct {
	ID            string
	DateStr       string
	Year          int
	Round         int
	HomeTeam      string
	AwayTeam      string
	HomeGoal      int
	AwayGoal      int
	HomeTeamState string
	AwayTeamState string
	Winner        string
	Arena         string
	Note          string
}

// FIFAPlayer - FIFA-style player data
type FIFAPlayer struct {
	ID              string
	Name            string
	Age             int
	Nationality     string
	Overall         int
	Potential       int
	Club            string
	Position        string
	JerseyNumber    string
	Value           string
	Wage            string
	PreferredFoot   string
	InternationalReputation int
	WeakFoot        int
	SkillMoves      int
	WorkRate        string
	BodyType        string
	Height          string
	Weight          string
	LeftFoot        int // sum of all skill attributes (simplified)
	Crossing        int
	Finishing       int
	HeadingAccuracy int
	ShortPassing    int
	Volleys         int
	Dribbling       int
	Curve           int
	FKAccuracy      int
	LongPassing     int
	BallControl     int
	Acceleration    int
	SprintSpeed     int
	Agility         int
	Reactions       int
	Balance         int
	ShotPower       int
	Jumping         int
	Stamina         int
	Strength        int
	LongShots       int
	Aggression      int
	Interceptions   int
	Positioning     int
	Vision          int
	Penalties       int
	Composure       int
	Marking         int
	StandingTackle  int
	SlidingTackle   int
}

// MatchResult is for MCP responses
type MatchResult struct {
	Date         string `json:"date"`
	HomeTeam     string `json:"home_team"`
	AwayTeam     string `json:"away_team"`
	HomeScore    int    `json:"home_score"`
	AwayScore    int    `json:"away_score"`
	Competition  string `json:"competition"`
	RoundOrStage string `json:"round_or_stage,omitempty"`
}

// TeamStats - aggregated team statistics
type TeamStats struct {
	Matches      int     `json:"matches"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	WinRate      float64 `json:"win_rate"`
}

// HeadToHead - head-to-head between two teams
type HeadToHead struct {
	Team1        string       `json:"team1"`
	Team2        string       `json:"team2"`
	Team1Wins    int          `json:"team1_wins"`
	Team2Wins    int          `json:"team2_wins"`
	Draws        int          `json:"draws"`
	TotalMatches int          `json:"total_matches"`
	Matches      []MatchResult `json:"matches,omitempty"`
}

// CompetitionStanding - standings
type CompetitionStanding struct {
	Team         string `json:"team"`
	Matches      int    `json:"matches"`
	Wins         int    `json:"wins"`
	Draws        int    `json:"draws"`
	Losses       int    `json:"losses"`
	GoalsFor     int    `json:"goals_for"`
	GoalsAgainst int    `json:"goals_against"`
	Points       int    `json:"points"`
}

// BigWin - large-margin victories
type BigWin struct {
	Date        string `json:"date"`
	HomeTeam    string `json:"home_team"`
	AwayTeam    string `json:"away_team"`
	HomeScore   int    `json:"home_score"`
	AwayScore   int    `json:"away_score"`
	Margin      int    `json:"margin"`
	Competition string `json:"competition"`
}

// ClubPlayersSummary - Brazilian players per club
type ClubPlayersSummary struct {
	Club        string  `json:"club"`
	PlayerCount int     `json:"player_count"`
	AvgRating   float64 `json:"avg_rating"`
}

// PlayerResult - player info for MCP responses
type PlayerResult struct {
	Name                  string `json:"name"`
	Age                   int    `json:"age"`
	Nationality           string `json:"nationality"`
	Overall               int    `json:"overall"`
	Potential             int    `json:"potential"`
	Club                  string `json:"club"`
	Position              string `json:"position"`
	JerseyNumber          string `json:"jersey_number,omitempty"`
	Crossing              int    `json:"crossing,omitempty"`
	Finishing             int    `json:"finishing,omitempty"`
	HeadingAccuracy       int    `json:"heading_accuracy,omitempty"`
	ShortPassing          int    `json:"short_passing,omitempty"`
	Volleys               int    `json:"volleys,omitempty"`
	Dribbling             int    `json:"dribbling,omitempty"`
	Curve                 int    `json:"curve,omitempty"`
	FKAccuracy            int    `json:"fk_accuracy,omitempty"`
	LongPassing           int    `json:"long_passing,omitempty"`
	BallControl           int    `json:"ball_control,omitempty"`
	Acceleration          int    `json:"acceleration,omitempty"`
	SprintSpeed           int    `json:"sprint_speed,omitempty"`
	Agility               int    `json:"agility,omitempty"`
	Reactions             int    `json:"reactions,omitempty"`
	Balance               int    `json:"balance,omitempty"`
	ShotPower             int    `json:"shot_power,omitempty"`
	Jumping               int    `json:"jumping,omitempty"`
	Stamina               int    `json:"stamina,omitempty"`
	Strength              int    `json:"strength,omitempty"`
	LongShots             int    `json:"long_shots,omitempty"`
	Aggression            int    `json:"aggression,omitempty"`
	Interceptions         int    `json:"interceptions,omitempty"`
	Positioning           int    `json:"positioning,omitempty"`
	Vision                int    `json:"vision,omitempty"`
	Penalties             int    `json:"penalties,omitempty"`
	Composure             int    `json:"composure,omitempty"`
	Marking               int    `json:"marking,omitempty"`
	StandingTackle        int    `json:"standing_tackle,omitempty"`
	SlidingTackle         int    `json:"sliding_tackle,omitempty"`
}

// AverageGoalsStats - goal statistics per competition
type AverageGoalsStats struct {
	TotalMatches     int     `json:"total_matches"`
	TotalGoals       int     `json:"total_goals"`
	AvgGoalsPerMatch float64 `json:"avg_goals_per_match"`
	HomeWins         int     `json:"home_wins"`
	AwayWins         int     `json:"away_wins"`
	Draws            int     `json:"draws"`
	HomeWinRate      float64 `json:"home_win_rate"`
	AwayWinRate      float64 `json:"away_win_rate"`
	DrawRate         float64 `json:"draw_rate"`
}
