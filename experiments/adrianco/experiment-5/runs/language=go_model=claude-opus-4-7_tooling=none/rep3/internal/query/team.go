package query

import (
	"sort"
	"strings"

	"github.com/adrian/brazilian-soccer-mcp/internal/data"
	"github.com/adrian/brazilian-soccer-mcp/internal/normalize"
)

// TeamRecord aggregates a team's results.
type TeamRecord struct {
	Team         string
	Competition  string
	Season       int
	HomeOrAway   string // "home", "away", "" (any)
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int
}

// WinRate returns wins / matches as a percentage (0 when no matches).
func (r TeamRecord) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Matches) * 100.0
}

// TeamStats computes a TeamRecord for a team filtered by optional competition,
// season, and home/away venue.
func TeamStats(ds *data.Dataset, team, competition string, season int, venue string) TeamRecord {
	r := TeamRecord{
		Team:        team,
		Competition: competition,
		Season:      season,
		HomeOrAway:  venue,
	}
	for _, m := range ds.Matches {
		if season > 0 && m.Season != season {
			continue
		}
		if competition != "" &&
			!strings.EqualFold(string(m.Competition), competition) &&
			!strings.Contains(strings.ToLower(string(m.Competition)), strings.ToLower(competition)) {
			continue
		}
		isHome := normalize.Matches(m.HomeTeam, team)
		isAway := normalize.Matches(m.AwayTeam, team)
		if !isHome && !isAway {
			continue
		}
		if venue == "home" && !isHome {
			continue
		}
		if venue == "away" && !isAway {
			continue
		}
		r.Matches++
		var gf, ga int
		if isHome {
			gf, ga = m.HomeGoal, m.AwayGoal
		} else {
			gf, ga = m.AwayGoal, m.HomeGoal
		}
		r.GoalsFor += gf
		r.GoalsAgainst += ga
		switch {
		case gf > ga:
			r.Wins++
			r.Points += 3
		case gf < ga:
			r.Losses++
		default:
			r.Draws++
			r.Points++
		}
	}
	return r
}

// TopScoringTeams returns the top-N teams by total goals scored within an
// optional competition/season.
func TopScoringTeams(ds *data.Dataset, competition string, season int, n int) []TeamRecord {
	tally := make(map[string]*TeamRecord)
	for _, m := range ds.Matches {
		if season > 0 && m.Season != season {
			continue
		}
		if competition != "" &&
			!strings.EqualFold(string(m.Competition), competition) &&
			!strings.Contains(strings.ToLower(string(m.Competition)), strings.ToLower(competition)) {
			continue
		}
		accumulate(tally, m.HomeTeam, m.HomeGoal, m.AwayGoal)
		accumulate(tally, m.AwayTeam, m.AwayGoal, m.HomeGoal)
	}
	records := make([]TeamRecord, 0, len(tally))
	for _, r := range tally {
		records = append(records, *r)
	}
	sort.Slice(records, func(i, j int) bool {
		if records[i].GoalsFor == records[j].GoalsFor {
			return records[i].Wins > records[j].Wins
		}
		return records[i].GoalsFor > records[j].GoalsFor
	})
	if n > 0 && len(records) > n {
		records = records[:n]
	}
	return records
}

func accumulate(tally map[string]*TeamRecord, team string, gf, ga int) {
	key := normalize.Key(team)
	if key == "" {
		return
	}
	r, ok := tally[key]
	if !ok {
		r = &TeamRecord{Team: team}
		tally[key] = r
	}
	r.Matches++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
		r.Points += 3
	case gf < ga:
		r.Losses++
	default:
		r.Draws++
		r.Points++
	}
}
