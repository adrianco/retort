package query

import (
	"strings"

	"github.com/adrian/brazilian-soccer-mcp/internal/data"
)

// Stats summarises a slice of matches.
type Stats struct {
	Competition  string
	Season       int
	Matches      int
	TotalGoals   int
	HomeWins     int
	AwayWins     int
	Draws        int
	HomeGoals    int
	AwayGoals    int
	AvgGoals     float64
	HomeWinRate  float64
	AwayWinRate  float64
	DrawRate     float64
	HomeGoalsAvg float64
	AwayGoalsAvg float64
}

// AggregateStats computes summary statistics across matches matching the
// optional competition/season filter.
func AggregateStats(ds *data.Dataset, competition string, season int) Stats {
	s := Stats{Competition: competition, Season: season}
	for _, m := range ds.Matches {
		if season > 0 && m.Season != season {
			continue
		}
		if competition != "" &&
			!strings.EqualFold(string(m.Competition), competition) &&
			!strings.Contains(strings.ToLower(string(m.Competition)), strings.ToLower(competition)) {
			continue
		}
		s.Matches++
		s.HomeGoals += m.HomeGoal
		s.AwayGoals += m.AwayGoal
		s.TotalGoals += m.HomeGoal + m.AwayGoal
		switch {
		case m.HomeGoal > m.AwayGoal:
			s.HomeWins++
		case m.AwayGoal > m.HomeGoal:
			s.AwayWins++
		default:
			s.Draws++
		}
	}
	if s.Matches > 0 {
		fm := float64(s.Matches)
		s.AvgGoals = float64(s.TotalGoals) / fm
		s.HomeWinRate = float64(s.HomeWins) / fm * 100.0
		s.AwayWinRate = float64(s.AwayWins) / fm * 100.0
		s.DrawRate = float64(s.Draws) / fm * 100.0
		s.HomeGoalsAvg = float64(s.HomeGoals) / fm
		s.AwayGoalsAvg = float64(s.AwayGoals) / fm
	}
	return s
}
