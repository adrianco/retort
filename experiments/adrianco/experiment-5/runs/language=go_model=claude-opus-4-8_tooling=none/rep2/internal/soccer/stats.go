// stats.go computes aggregate statistics across matches.
package soccer

import (
	"sort"
	"strings"
)

// CompetitionStats summarises aggregate numbers for a competition/season slice.
type CompetitionStats struct {
	Competition string
	Season      int // 0 = all seasons
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
	BiggestWins []Match // top results by goal margin, descending
}

// AvgGoals returns the mean goals per match.
func (c CompetitionStats) AvgGoals() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.TotalGoals) / float64(c.Matches)
}

// HomeWinRate returns the fraction of matches won by the home side.
func (c CompetitionStats) HomeWinRate() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.HomeWins) / float64(c.Matches)
}

// Stats aggregates scored matches for an optional competition and season.
// topWins controls how many "biggest win" matches are returned (default 5 when
// <= 0).
func (s *Store) Stats(competition string, season, topWins int) CompetitionStats {
	if topWins <= 0 {
		topWins = 5
	}
	c := CompetitionStats{Competition: competition, Season: season}
	var scored []Match
	for _, m := range s.Matches {
		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if !m.HasScore {
			continue
		}
		c.Matches++
		c.TotalGoals += m.HomeGoals + m.AwayGoals
		switch m.Result() {
		case "home":
			c.HomeWins++
		case "away":
			c.AwayWins++
		default:
			c.Draws++
		}
		scored = append(scored, m)
	}
	sort.SliceStable(scored, func(i, j int) bool {
		mi, mj := scored[i], scored[j]
		di := abs(mi.HomeGoals - mi.AwayGoals)
		dj := abs(mj.HomeGoals - mj.AwayGoals)
		if di != dj {
			return di > dj
		}
		return (mi.HomeGoals + mi.AwayGoals) > (mj.HomeGoals + mj.AwayGoals)
	})
	if len(scored) > topWins {
		scored = scored[:topWins]
	}
	c.BiggestWins = scored
	return c
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}
