package query

import (
	"sort"

	"brsoccer/internal/data"
)

type TeamStats struct {
	Team           string
	Season         int
	Competition    string
	Matches        int
	Wins           int
	Draws          int
	Losses         int
	GoalsFor       int
	GoalsAgainst   int
	HomeWins       int
	HomeDraws      int
	HomeLosses     int
	AwayWins       int
	AwayDraws      int
	AwayLosses     int
	Points         int
}

func (s *TeamStats) WinRate() float64 {
	if s.Matches == 0 {
		return 0
	}
	return float64(s.Wins) / float64(s.Matches) * 100
}

func ComputeTeamStats(db *data.DB, team string, season int, competition string) TeamStats {
	s := TeamStats{Team: team, Season: season, Competition: competition}
	ms := FindMatches(db, MatchFilter{Team: team, Season: season, Competition: competition})
	for _, m := range ms {
		s.Matches++
		home := data.TeamMatches(m.HomeTeam, team)
		var gf, ga int
		if home {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		s.GoalsFor += gf
		s.GoalsAgainst += ga
		switch {
		case gf > ga:
			s.Wins++
			if home {
				s.HomeWins++
			} else {
				s.AwayWins++
			}
		case gf < ga:
			s.Losses++
			if home {
				s.HomeLosses++
			} else {
				s.AwayLosses++
			}
		default:
			s.Draws++
			if home {
				s.HomeDraws++
			} else {
				s.AwayDraws++
			}
		}
	}
	s.Points = s.Wins*3 + s.Draws
	return s
}

// Standings returns the league table for a given season + competition.
func Standings(db *data.DB, season int, competition string) []TeamStats {
	teams := map[string]string{} // key -> display name
	for _, m := range db.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if competition != "" && !containsFold(m.Competition, competition) {
			continue
		}
		if kh := data.NormalizeTeam(m.HomeTeam); kh != "" {
			if _, ok := teams[kh]; !ok {
				teams[kh] = m.HomeTeam
			}
		}
		if ka := data.NormalizeTeam(m.AwayTeam); ka != "" {
			if _, ok := teams[ka]; !ok {
				teams[ka] = m.AwayTeam
			}
		}
	}
	out := make([]TeamStats, 0, len(teams))
	for _, display := range teams {
		s := ComputeTeamStats(db, display, season, competition)
		if s.Matches == 0 {
			continue
		}
		out = append(out, s)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Points != out[j].Points {
			return out[i].Points > out[j].Points
		}
		gdI := out[i].GoalsFor - out[i].GoalsAgainst
		gdJ := out[j].GoalsFor - out[j].GoalsAgainst
		if gdI != gdJ {
			return gdI > gdJ
		}
		return out[i].GoalsFor > out[j].GoalsFor
	})
	return out
}

func containsFold(a, b string) bool {
	return data.TeamMatches(a, b) || stringContainsFold(a, b)
}

func stringContainsFold(a, b string) bool {
	la, lb := []rune(a), []rune(b)
	if len(lb) == 0 {
		return true
	}
	if len(la) < len(lb) {
		return false
	}
	for i := 0; i+len(lb) <= len(la); i++ {
		eq := true
		for j := 0; j < len(lb); j++ {
			if toLowerRune(la[i+j]) != toLowerRune(lb[j]) {
				eq = false
				break
			}
		}
		if eq {
			return true
		}
	}
	return false
}

func toLowerRune(r rune) rune {
	if r >= 'A' && r <= 'Z' {
		return r + 32
	}
	return r
}
