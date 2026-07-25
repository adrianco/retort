package model

// Match represents a soccer match from any dataset
type Match struct {
	ID              string   `json:"id"`
	Tournament      string   `json:"tournament"`
	HomeTeam        string   `json:"home_team"`
	AwayTeam        string   `json:"away_team"`
	HomeTeamState   string   `json:"home_team_state,omitempty"`
	AwayTeamState   string   `json:"away_team_state,omitempty"`
	HomeGoal        int      `json:"home_goal"`
	AwayGoal        int      `json:"away_goal"`
	HomeCorner      int      `json:"home_corner,omitempty"`
	AwayCorner      int      `json:"away_corner,omitempty"`
	HomeAttack      int      `json:"home_attack,omitempty"`
	AwayAttack      int      `json:"away_attack,omitempty"`
	HomeShot        int      `json:"home_shot,omitempty"`
	AwayShot        int      `json:"away_shot,omitempty"`
	DateTime        string   `json:"datetime"`
	Season          string   `json:"season"`
	Round           string   `json:"round,omitempty"`
	Stage           string   `json:"stage,omitempty"`
	Time            string   `json:"time,omitempty"`
	Date            string   `json:"date,omitempty"`
	HTResult        string   `json:"ht_result,omitempty"`
	ATResult        string   `json:"at_result,omitempty"`
	TotalCorners    int      `json:"total_corners,omitempty"`
	Winner          string   `json:"winner,omitempty"`
	Arena           string   `json:"arena,omitempty"`
	MatchDateParsed DateType `json:"-"`
}

// DateType is a parsed date
type DateType struct {
	Year  int
	Month int
	Day   int
}

// TeamStats represents statistics for a team
type TeamStats struct {
	Team            string `json:"team"`
	Matches         int    `json:"matches"`
	Wins            int    `json:"wins"`
	Draws           int    `json:"draws"`
	Losses          int    `json:"losses"`
	GoalsFor        int    `json:"goals_for"`
	GoalsAgainst    int    `json:"goals_against"`
	GoalDifference  int    `json:"goal_difference"`
	Points          int    `json:"points"`
	HomeMatches     int    `json:"home_matches,omitempty"`
	HomeWins        int    `json:"home_wins,omitempty"`
	HomeDraws       int    `json:"home_draws,omitempty"`
	HomeLosses      int    `json:"home_losses,omitempty"`
	HomeGoalsFor    int    `json:"home_goals_for,omitempty"`
	HomeGoalsAgainst int   `json:"home_goals_against,omitempty"`
	AwayMatches     int    `json:"away_matches,omitempty"`
	AwayWins        int    `json:"away_wins,omitempty"`
	AwayDraws       int    `json:"away_draws,omitempty"`
	AwayLosses      int    `json:"away_losses,omitempty"`
	AwayGoalsFor    int    `json:"away_goals_for,omitempty"`
	AwayGoalsAgainst int   `json:"away_goals_against,omitempty"`
}

// Player represents a soccer player from the FIFA dataset
type Player struct {
	ID           string   `json:"id"`
	Name         string   `json:"name"`
	Age          int      `json:"age"`
	Nationality  string   `json:"nationality"`
	Overall      int      `json:"overall"`
	Potential    int      `json:"potential"`
	Club         string   `json:"club"`
	Position     string   `json:"position"`
	JerseyNumber int      `json:"jersey_number,omitempty"`
	Height       string   `json:"height,omitempty"`
	Weight       string   `json:"weight,omitempty"`
	PreferredFoot string  `json:"preferred_foot,omitempty"`
	Rating       float64  `json:"rating,omitempty"`
	Skills       []Skill  `json:"skills,omitempty"`
}

// Skill represents a player's skill rating
type Skill struct {
	Name  string `json:"name"`
	Value int    `json:"value"`
}

// Competition represents a tournament/competition
type Competition struct {
	Name        string `json:"name"`
	Season      string `json:"season"`
	Teams       int    `json:"teams,omitempty"`
	Matches     int    `json:"matches,omitempty"`
	TopScorer   string `json:"top_scorer,omitempty"`
	Champion    string `json:"champion,omitempty"`
	RunnerUp    string `json:"runner_up,omitempty"`
}

// TeamHeadToHead represents head-to-head record between two teams
type TeamHeadToHead struct {
	Team1         string `json:"team1"`
	Team2         string `json:"team2"`
	Matches       int    `json:"matches"`
	Team1Wins     int    `json:"team1_wins"`
	Team2Wins     int    `json:"team2_wins"`
	Draws         int    `json:"draws"`
	Team1GoalsFor int    `json:"team1_goals_for"`
	Team2GoalsFor int    `json:"team2_goals_for"`
	MatchesList   []Match `json:"matches_list,omitempty"`
}

// BigWin represents a match with a large goal difference
type BigWin struct {
	Match
	GoalDifference int `json:"goal_difference"`
}

// CompetitionStandings represents the standings for a competition
type CompetitionStandings struct {
	Competition string      `json:"competition"`
	Season      string      `json:"season"`
	Standings   []TeamStats `json:"standings"`
}

// QueryResult represents a query response
type QueryResult struct {
	Query     string      `json:"query"`
	Results   interface{} `json:"results"`
	Count     int         `json:"count"`
	ElapsedMs int         `json:"elapsed_ms"`
}
