// standings.go computes league tables and per-team records from match results.
package soccer

import (
	"sort"
	"strings"
)

// TeamRecord captures a team's results over a set of matches.
type TeamRecord struct {
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

// Points returns league points (3 per win, 1 per draw).
func (r TeamRecord) Points() int { return r.Wins*3 + r.Draws }

// GoalDiff returns goals for minus goals against.
func (r TeamRecord) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }

// WinRate returns wins as a fraction of matches played (0..1).
func (r TeamRecord) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Played)
}

// Standings computes the final table for a competition and season, ordered by
// points, then goal difference, then goals for.
func (s *Store) Standings(competition string, season int) []TeamRecord {
	records := map[string]*TeamRecord{}
	get := func(name string) *TeamRecord {
		r := records[name]
		if r == nil {
			r = &TeamRecord{Team: name}
			records[name] = r
		}
		return r
	}
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
		home := get(m.HomeTeam)
		away := get(m.AwayTeam)
		home.Played++
		away.Played++
		home.GoalsFor += m.HomeGoals
		home.GoalsAgainst += m.AwayGoals
		away.GoalsFor += m.AwayGoals
		away.GoalsAgainst += m.HomeGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			home.Wins++
			away.Losses++
		case m.AwayGoals > m.HomeGoals:
			away.Wins++
			home.Losses++
		default:
			home.Draws++
			away.Draws++
		}
	}

	out := make([]TeamRecord, 0, len(records))
	for _, r := range records {
		out = append(out, *r)
	}
	sort.SliceStable(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.GoalDiff() != b.GoalDiff() {
			return a.GoalDiff() > b.GoalDiff()
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	return out
}

// TeamStats computes a single team's record under an optional competition,
// season and venue ("home"/"away"/"") filter.
func (s *Store) TeamStats(team, competition string, season int, venue string) TeamRecord {
	rec := TeamRecord{Team: CleanTeamName(team)}
	venue = strings.ToLower(venue)
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
		isHome := TeamMatches(m.HomeRaw, team)
		isAway := TeamMatches(m.AwayRaw, team)
		if !isHome && !isAway {
			continue
		}
		if venue == "home" && !isHome {
			continue
		}
		if venue == "away" && !isAway {
			continue
		}
		// A neutral-ish guard: if a team somehow matches both sides, skip.
		if isHome && isAway {
			continue
		}

		var gf, ga int
		if isHome {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		rec.Played++
		rec.GoalsFor += gf
		rec.GoalsAgainst += ga
		switch {
		case gf > ga:
			rec.Wins++
		case ga > gf:
			rec.Losses++
		default:
			rec.Draws++
		}
	}
	return rec
}
