// players.go implements FIFA player-database queries.
package soccer

import (
	"sort"
	"strings"
)

// PlayerFilter describes search criteria for SearchPlayers. Empty fields are
// ignored. Name, Nationality, Club and Position use case- and accent-
// insensitive substring matching.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	SortBy      string // "overall" (default), "potential", "age", "name"
	Limit       int    // 0 = no limit
}

// SearchPlayers returns players matching the filter, sorted per SortBy
// (descending for ratings, ascending for name/age).
func (s *Store) SearchPlayers(f PlayerFilter) []Player {
	var out []Player
	for _, p := range s.Players {
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		if !containsFold(p.Name, f.Name) {
			continue
		}
		if !containsFold(p.Nationality, f.Nationality) {
			continue
		}
		if !containsFold(p.Club, f.Club) {
			continue
		}
		if !containsFold(p.Position, f.Position) {
			continue
		}
		out = append(out, p)
	}
	sortPlayers(out, f.SortBy)
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func sortPlayers(ps []Player, by string) {
	switch strings.ToLower(by) {
	case "name":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Name < ps[j].Name })
	case "age":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Age < ps[j].Age })
	case "potential":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Potential > ps[j].Potential })
	default: // overall
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Overall > ps[j].Overall })
	}
}

// ClubSummary aggregates players grouped by club.
type ClubSummary struct {
	Club       string
	Count      int
	AvgOverall float64
}

// PlayersByClub groups the players matching the (optional) nationality filter
// by club, returning the summaries sorted by player count descending.
func (s *Store) PlayersByClub(nationality string) []ClubSummary {
	type acc struct {
		count int
		total int
	}
	groups := map[string]*acc{}
	for _, p := range s.Players {
		if p.Club == "" {
			continue
		}
		if !containsFold(p.Nationality, nationality) {
			continue
		}
		a := groups[p.Club]
		if a == nil {
			a = &acc{}
			groups[p.Club] = a
		}
		a.count++
		a.total += p.Overall
	}
	out := make([]ClubSummary, 0, len(groups))
	for club, a := range groups {
		avg := 0.0
		if a.count > 0 {
			avg = float64(a.total) / float64(a.count)
		}
		out = append(out, ClubSummary{Club: club, Count: a.count, AvgOverall: avg})
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Count != out[j].Count {
			return out[i].Count > out[j].Count
		}
		return out[i].Club < out[j].Club
	})
	return out
}

// containsFold reports whether needle is an accent-insensitive, case-
// insensitive substring of haystack. An empty needle always matches.
func containsFold(haystack, needle string) bool {
	if needle == "" {
		return true
	}
	return strings.Contains(
		strings.ToLower(FoldAccents(haystack)),
		strings.ToLower(FoldAccents(needle)),
	)
}
