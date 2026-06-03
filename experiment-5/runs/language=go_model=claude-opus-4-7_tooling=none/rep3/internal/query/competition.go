package query

import (
	"sort"
	"strings"

	"github.com/adrian/brazilian-soccer-mcp/internal/data"
	"github.com/adrian/brazilian-soccer-mcp/internal/normalize"
)

// Standing is a single row of a competition table.
type Standing struct {
	Position     int
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	GoalDiff     int
	Points       int
}

// Standings computes a league table for a competition and season using simple
// 3-1-0 points. Teams are sorted by points, then goal difference, then
// goals for.
func Standings(ds *data.Dataset, competition string, season int) []Standing {
	tally := make(map[string]*Standing)
	display := make(map[string]string)
	for _, m := range ds.Matches {
		if season > 0 && m.Season != season {
			continue
		}
		if competition != "" &&
			!strings.EqualFold(string(m.Competition), competition) &&
			!strings.Contains(strings.ToLower(string(m.Competition)), strings.ToLower(competition)) {
			continue
		}
		updateStanding(tally, display, m.HomeTeam, m.HomeGoal, m.AwayGoal)
		updateStanding(tally, display, m.AwayTeam, m.AwayGoal, m.HomeGoal)
	}
	out := make([]Standing, 0, len(tally))
	for k, s := range tally {
		s.GoalDiff = s.GoalsFor - s.GoalsAgainst
		if display[k] != "" {
			s.Team = display[k]
		}
		out = append(out, *s)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Points != out[j].Points {
			return out[i].Points > out[j].Points
		}
		if out[i].GoalDiff != out[j].GoalDiff {
			return out[i].GoalDiff > out[j].GoalDiff
		}
		if out[i].GoalsFor != out[j].GoalsFor {
			return out[i].GoalsFor > out[j].GoalsFor
		}
		return out[i].Team < out[j].Team
	})
	for i := range out {
		out[i].Position = i + 1
	}
	return out
}

func updateStanding(tally map[string]*Standing, display map[string]string, team string, gf, ga int) {
	key := normalize.Key(team)
	if key == "" {
		return
	}
	s, ok := tally[key]
	if !ok {
		s = &Standing{Team: team}
		tally[key] = s
	}
	if _, ok := display[key]; !ok {
		display[key] = team
	} else if len(team) > len(display[key]) {
		display[key] = team
	}
	s.Played++
	s.GoalsFor += gf
	s.GoalsAgainst += ga
	switch {
	case gf > ga:
		s.Wins++
		s.Points += 3
	case gf < ga:
		s.Losses++
	default:
		s.Draws++
		s.Points++
	}
}

// Seasons returns the distinct seasons present for a competition (or across
// all data when competition is empty), sorted ascending.
func Seasons(ds *data.Dataset, competition string) []int {
	seen := make(map[int]struct{})
	for _, m := range ds.Matches {
		if competition != "" &&
			!strings.EqualFold(string(m.Competition), competition) &&
			!strings.Contains(strings.ToLower(string(m.Competition)), strings.ToLower(competition)) {
			continue
		}
		if m.Season == 0 {
			continue
		}
		seen[m.Season] = struct{}{}
	}
	out := make([]int, 0, len(seen))
	for s := range seen {
		out = append(out, s)
	}
	sort.Ints(out)
	return out
}
