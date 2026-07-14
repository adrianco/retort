package loader

import (
	"regexp"
	"time"
)

type BrasileiraoMatch struct {
	Datetime      time.Time
	HomeTeam      string
	HomeTeamState string
	AwayTeam      string
	AwayTeamState string
	HomeGoal      int
	AwayGoal      int
	Season        int
	Round         int
}

type CupMatch struct {
	Round    string
	Datetime time.Time
	HomeTeam string
	AwayTeam string
	HomeGoal int
	AwayGoal int
	Season   int
}

type LibertadoresMatch struct {
	Datetime time.Time
	HomeTeam string
	AwayTeam string
	HomeGoal int
	AwayGoal int
	Season   int
	Stage    string
}

type ExtendedMatch struct {
	Tournament   string
	HomeTeam     string
	AwayTeam     string
	HomeGoal     float64
	AwayGoal     float64
	HomeCorner   float64
	AwayCorner   float64
	HomeAttack   float64
	AwayAttack   float64
	HomeShots    float64
	AwayShots    float64
	Time         string
	Date         time.Time
	TotalCorners float64
}

type HistoricalMatch struct {
	ID              string
	Date            time.Time
	Year            int
	Round           int
	HomeTeam        string
	AwayTeam        string
	HomeGoals       int
	AwayGoals       int
	HomeState       string
	AwayState       string
	Winner          string
	Arena           string
}

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
	Crossing              int
	Finishing             int
	Dribbling             int
	SprintSpeed           int
	Reactions             int
	Stamina               int
}

var (
	reStateSuffixSpaced = regexp.MustCompile(` - [A-Z]{2}$`)
	reStateSuffixDash   = regexp.MustCompile(`-[A-Z]{2}$`)
)

// NormalizeTeamName strips state suffixes for consistent matching.
// Handles formats like "Palmeiras-SP" and "América - MG".
func NormalizeTeamName(name string) string {
	n := reStateSuffixSpaced.ReplaceAllString(name, "")
	n = reStateSuffixDash.ReplaceAllString(n, "")
	return n
}
