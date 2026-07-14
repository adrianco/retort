package query

import (
	"sort"

	"brsoccer/internal/data"
)

type GlobalStats struct {
	TotalMatches   int
	TotalGoals     int
	HomeWins       int
	AwayWins       int
	Draws          int
	AvgGoalsPerMatch float64
	HomeWinRate    float64
}

func Overall(db *data.DB, competition string, season int) GlobalStats {
	var s GlobalStats
	for _, m := range db.Matches {
		if competition != "" && !data.TeamMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		s.TotalMatches++
		s.TotalGoals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			s.HomeWins++
		case m.AwayGoals > m.HomeGoals:
			s.AwayWins++
		default:
			s.Draws++
		}
	}
	if s.TotalMatches > 0 {
		s.AvgGoalsPerMatch = float64(s.TotalGoals) / float64(s.TotalMatches)
		s.HomeWinRate = float64(s.HomeWins) / float64(s.TotalMatches) * 100
	}
	return s
}

// BiggestWins returns matches sorted by goal difference.
func BiggestWins(db *data.DB, competition string, limit int) []data.Match {
	out := make([]data.Match, 0, len(db.Matches))
	for _, m := range db.Matches {
		if competition != "" && !data.TeamMatches(m.Competition, competition) {
			continue
		}
		out = append(out, m)
	}
	sort.Slice(out, func(i, j int) bool {
		di := abs(out[i].HomeGoals - out[i].AwayGoals)
		dj := abs(out[j].HomeGoals - out[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		return (out[i].HomeGoals + out[i].AwayGoals) > (out[j].HomeGoals + out[j].AwayGoals)
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

func abs(i int) int {
	if i < 0 {
		return -i
	}
	return i
}
