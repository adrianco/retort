package soccer

// Match represents a single soccer match from any competition.
type Match struct {
	Date        string
	HomeTeam    string
	AwayTeam    string
	HomeGoals   int
	AwayGoals   int
	Season      int
	Round       string
	Competition string // "brasileirao", "copa_brasil", "libertadores", "other"
	Stage       string
	Arena       string
	Source      string
}

// Player represents a player from the FIFA dataset.
type Player struct {
	ID           string
	Name         string
	Age          int
	Nationality  string
	Overall      int
	Potential    int
	Club         string
	Position     string
	JerseyNumber string
	Height       string
	Weight       string
}

// TeamStats aggregates win/draw/loss stats for a team.
type TeamStats struct {
	Team         string
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Matches      int
	Competition  string
	Season       int
}

// StandingEntry is one row in a league table.
type StandingEntry struct {
	Position     int
	Team         string
	Played       int
	Won          int
	Drawn        int
	Lost         int
	GoalsFor     int
	GoalsAgainst int
	GoalDiff     int
	Points       int
}

// HeadToHead holds head-to-head stats between two teams.
type HeadToHead struct {
	Team1      string
	Team2      string
	Team1Wins  int
	Draws      int
	Team2Wins  int
	Team1Goals int
	Team2Goals int
	Matches    []Match
}

// Store holds all loaded match and player data.
type Store struct {
	Matches []Match
	Players []Player
}
