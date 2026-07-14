package soccer

import (
	"sort"
	"strings"
)

// PlayerFilter selects players by name, nationality, club, position and/or
// minimum overall rating. Name, Nationality and Club match as
// case-insensitive substrings; Position matches exactly (case-insensitive).
// Zero values mean "no constraint" on that field.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

func containsFold(haystack, needle string) bool {
	return strings.Contains(strings.ToLower(haystack), strings.ToLower(needle))
}

// SearchPlayers returns players satisfying the filter, sorted by Overall
// rating descending.
func (s *Store) SearchPlayers(f PlayerFilter) []Player {
	var out []Player
	for _, p := range s.Players {
		if f.Name != "" && !containsFold(p.Name, f.Name) {
			continue
		}
		if f.Nationality != "" && !containsFold(p.Nationality, f.Nationality) {
			continue
		}
		if f.Club != "" && !containsFold(p.Club, f.Club) {
			continue
		}
		if f.Position != "" && !strings.EqualFold(p.Position, f.Position) {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
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
