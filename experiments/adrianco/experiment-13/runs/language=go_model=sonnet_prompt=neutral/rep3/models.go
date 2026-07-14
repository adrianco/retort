package main

// Match represents a unified match record across all competitions
type Match struct {
	Competition string
	Date        string // Normalized to YYYY-MM-DD
	HomeTeam    string // Raw name
	AwayTeam    string // Raw name
	HomeNorm    string // Normalized name for matching
	AwayNorm    string // Normalized name for matching
	HomeGoal    int
	AwayGoal    int
	Season      int
	Round       string
	Stage       string // Libertadores stage
	HomeState   string
	AwayState   string
	Arena       string
	// IsPrimary: true for canonical datasets (Brasileirao, Cup, Libertadores, Historical)
	// false for supplemental datasets (BR-Football-Dataset)
	IsPrimary bool
	// Extended stats (from BR-Football-Dataset)
	HasStats     bool
	HomeCorner   int
	AwayCorner   int
	HomeAttack   int
	AwayAttack   int
	HomeShots    int
	AwayShots    int
	TotalCorners int
}

// Player represents a FIFA 19 player
type Player struct {
	ID          string
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string
	Height      string
	Weight      string
	Value       string
	Wage        string
	// Key skills
	Crossing  int
	Finishing int
	Dribbling int
	Passing   int
}

// TeamStats holds calculated statistics for a team
type TeamStats struct {
	Team          string
	Matches       int
	Wins          int
	Draws         int
	Losses        int
	GoalsFor      int
	GoalsAgainst  int
	Points        int
}

func (s TeamStats) WinRate() float64 {
	if s.Matches == 0 {
		return 0
	}
	return float64(s.Wins) / float64(s.Matches) * 100
}

func (s TeamStats) GoalDiff() int {
	return s.GoalsFor - s.GoalsAgainst
}
