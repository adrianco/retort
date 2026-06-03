package query

import (
	"sort"
	"strings"

	"github.com/adrian/brazilian-soccer-mcp/internal/data"
)

// PlayerFilter filters FIFA players.
type PlayerFilter struct {
	NameContains string
	Nationality  string
	Club         string
	Position     string
	MinOverall   int
	MaxOverall   int
	Limit        int
}

// SearchPlayers returns players matching all set filter fields, sorted by
// Overall descending.
func SearchPlayers(ds *data.Dataset, f PlayerFilter) []data.Player {
	out := make([]data.Player, 0)
	for _, p := range ds.Players {
		if f.NameContains != "" && !strings.Contains(strings.ToLower(p.Name), strings.ToLower(f.NameContains)) {
			continue
		}
		if f.Nationality != "" && !strings.EqualFold(p.Nationality, f.Nationality) {
			continue
		}
		if f.Club != "" && !strings.Contains(strings.ToLower(p.Club), strings.ToLower(f.Club)) {
			continue
		}
		if f.Position != "" && !strings.EqualFold(p.Position, f.Position) {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MaxOverall > 0 && p.Overall > f.MaxOverall {
			continue
		}
		out = append(out, p)
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].Overall > out[j].Overall
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// ClubSummary describes the aggregate FIFA roster for a club.
type ClubSummary struct {
	Club           string
	PlayerCount    int
	AverageOverall float64
	TopOverall     int
}

// TopClubsByNationality returns clubs sorted by number of players of the given
// nationality. Useful for "Brazilian players at Brazilian clubs".
func TopClubsByNationality(ds *data.Dataset, nationality string, n int) []ClubSummary {
	type agg struct {
		count   int
		overall int
		top     int
	}
	tally := make(map[string]*agg)
	for _, p := range ds.Players {
		if nationality != "" && !strings.EqualFold(p.Nationality, nationality) {
			continue
		}
		if p.Club == "" {
			continue
		}
		a, ok := tally[p.Club]
		if !ok {
			a = &agg{}
			tally[p.Club] = a
		}
		a.count++
		a.overall += p.Overall
		if p.Overall > a.top {
			a.top = p.Overall
		}
	}
	out := make([]ClubSummary, 0, len(tally))
	for club, a := range tally {
		avg := 0.0
		if a.count > 0 {
			avg = float64(a.overall) / float64(a.count)
		}
		out = append(out, ClubSummary{Club: club, PlayerCount: a.count, AverageOverall: avg, TopOverall: a.top})
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].PlayerCount == out[j].PlayerCount {
			return out[i].AverageOverall > out[j].AverageOverall
		}
		return out[i].PlayerCount > out[j].PlayerCount
	})
	if n > 0 && len(out) > n {
		out = out[:n]
	}
	return out
}
