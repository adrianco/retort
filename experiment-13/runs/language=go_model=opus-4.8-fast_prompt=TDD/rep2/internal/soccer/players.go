package soccer

import (
	"sort"
	"strings"
)

// PlayerFilter selects players for SearchPlayers. Zero-valued fields are
// ignored. Name, Club and Position match case-insensitively; Name and Club
// match on substring, Position on a normalized equality.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int // 0 = no limit
}

// SearchPlayers returns players satisfying the filter, sorted by Overall
// rating descending (ties broken by name). Limit, if positive, caps results.
func (kb *KB) SearchPlayers(f PlayerFilter) []Player {
	var out []Player
	for _, p := range kb.Players {
		if !playerPasses(p, f) {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].Name < out[j].Name
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func playerPasses(p Player, f PlayerFilter) bool {
	if f.Name != "" && !containsFold(p.Name, f.Name) {
		return false
	}
	if f.Nationality != "" && !strings.EqualFold(p.Nationality, f.Nationality) {
		return false
	}
	if f.Club != "" && !TeamsMatch(p.Club, f.Club) && !containsFold(p.Club, f.Club) {
		return false
	}
	if f.Position != "" && !strings.EqualFold(p.Position, f.Position) {
		return false
	}
	if f.MinOverall != 0 && p.Overall < f.MinOverall {
		return false
	}
	return true
}

// containsFold reports whether s contains substr, case-insensitively.
func containsFold(s, substr string) bool {
	return strings.Contains(strings.ToLower(s), strings.ToLower(substr))
}
