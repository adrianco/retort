package query

import (
	"sort"
	"strings"

	"brsoccer/internal/data"
)

type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

func FindPlayers(db *data.DB, f PlayerFilter) []data.Player {
	out := make([]data.Player, 0, 32)
	for _, p := range db.Players {
		if f.Name != "" && !strings.Contains(strings.ToLower(p.Name), strings.ToLower(f.Name)) {
			continue
		}
		if f.Nationality != "" && !strings.EqualFold(p.Nationality, f.Nationality) {
			continue
		}
		if f.Club != "" && !data.TeamMatches(p.Club, f.Club) {
			continue
		}
		if f.Position != "" && !strings.EqualFold(p.Position, f.Position) {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Overall > out[j].Overall })
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}
