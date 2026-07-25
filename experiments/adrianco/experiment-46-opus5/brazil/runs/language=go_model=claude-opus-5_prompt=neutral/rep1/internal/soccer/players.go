// players.go - player search over the FIFA dataset.
//
// Context
//
//	fifa_data.csv is a FIFA 19 export: 18,207 players, 827 of them Brazilian,
//	with overall/potential ratings and 34 skill attributes each. It is a
//	different kind of node from a match, and it links into the match graph
//	through exactly 15 Brazilian clubs - the only ones EA licensed - via
//	fifaClubToClubID in clubs.go.
//
//	That gap is a feature of the data, not a bug in the loader, so club-scoped
//	player queries report it explicitly rather than silently returning nothing:
//	asking for Flamengo's squad returns an empty list plus the list of Brazilian
//	clubs that are covered.
package soccer

import (
	"sort"
	"strings"
)

// PlayerFilter describes a player search.
type PlayerFilter struct {
	Name          string
	Nationality   string
	Club          string
	ClubID        string
	Position      string
	PositionGroup string
	MinOverall    int
	MaxOverall    int
	MinAge        int
	MaxAge        int
	MinPotential  int
	SortBy        string
	Limit         int
}

// PlayerSortModes are the orderings exposed by the MCP tool.
var PlayerSortModes = []string{"overall", "potential", "age", "name", "growth"}

// SearchPlayers applies a filter and ordering to the player nodes.
func (g *Graph) SearchPlayers(f PlayerFilter) []*Player {
	name := normalizeText(f.Name)
	nationality := normalizeText(f.Nationality)
	club := normalizeText(f.Club)
	position := strings.ToUpper(strings.TrimSpace(f.Position))
	group := normalizeText(f.PositionGroup)

	var pool []*Player
	if f.ClubID != "" {
		pool = g.playersByClubID[f.ClubID]
	} else {
		pool = g.players
	}

	out := make([]*Player, 0, 64)
	for _, p := range pool {
		if name != "" && !strings.Contains(normalizeText(p.Name), name) {
			continue
		}
		if nationality != "" && normalizeText(p.Nationality) != nationality &&
			!strings.Contains(normalizeText(p.Nationality), nationality) {
			continue
		}
		if club != "" && !strings.Contains(normalizeText(p.Club), club) {
			continue
		}
		if position != "" && p.Position != position {
			continue
		}
		if group != "" && normalizeText(p.PositionGroup) != group {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MaxOverall > 0 && p.Overall > f.MaxOverall {
			continue
		}
		if f.MinPotential > 0 && p.Potential < f.MinPotential {
			continue
		}
		if f.MinAge > 0 && p.Age < f.MinAge {
			continue
		}
		if f.MaxAge > 0 && p.Age > f.MaxAge {
			continue
		}
		out = append(out, p)
	}

	sortPlayers(out, f.SortBy, name)
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func sortPlayers(list []*Player, mode, nameQuery string) {
	switch strings.ToLower(strings.TrimSpace(mode)) {
	case "age":
		sort.SliceStable(list, func(i, j int) bool {
			if list[i].Age != list[j].Age {
				return list[i].Age < list[j].Age
			}
			return list[i].Overall > list[j].Overall
		})
	case "potential":
		sort.SliceStable(list, func(i, j int) bool {
			if list[i].Potential != list[j].Potential {
				return list[i].Potential > list[j].Potential
			}
			return list[i].Overall > list[j].Overall
		})
	case "growth":
		sort.SliceStable(list, func(i, j int) bool {
			gi, gj := list[i].Potential-list[i].Overall, list[j].Potential-list[j].Overall
			if gi != gj {
				return gi > gj
			}
			return list[i].Potential > list[j].Potential
		})
	case "name":
		sort.SliceStable(list, func(i, j int) bool {
			return normalizeText(list[i].Name) < normalizeText(list[j].Name)
		})
	default: // "overall"
		sort.SliceStable(list, func(i, j int) bool {
			// When the user searched by name, an exact hit outranks a higher
			// rated player whose name merely contains the query.
			if nameQuery != "" {
				ei := normalizeText(list[i].Name) == nameQuery
				ej := normalizeText(list[j].Name) == nameQuery
				if ei != ej {
					return ei
				}
			}
			if list[i].Overall != list[j].Overall {
				return list[i].Overall > list[j].Overall
			}
			return list[i].Potential > list[j].Potential
		})
	}
}

// PlayerByID looks up a player node by FIFA ID.
func (g *Graph) PlayerByID(id int) *Player { return g.playersByID[id] }

// FindPlayer returns the best match for a player name plus other candidates.
func (g *Graph) FindPlayer(name string) (*Player, []*Player) {
	hits := g.SearchPlayers(PlayerFilter{Name: name, Limit: 10})
	if len(hits) == 0 {
		return nil, nil
	}
	return hits[0], hits[1:]
}

// ClubPlayerSummary aggregates a club's FIFA squad.
type ClubPlayerSummary struct {
	ClubID     string  `json:"club_id,omitempty"`
	Club       string  `json:"club"`
	Players    int     `json:"players"`
	AvgOverall float64 `json:"avg_overall"`
	MaxOverall int     `json:"max_overall"`
	TopPlayer  string  `json:"top_player,omitempty"`
	AvgAge     float64 `json:"avg_age"`
}

// SummarizeByClub groups players by their FIFA club, ranked by squad rating.
func SummarizeByClub(players []*Player) []ClubPlayerSummary {
	type acc struct {
		count        int
		overall, age int
		best         *Player
		clubID       string
	}
	groups := map[string]*acc{}
	for _, p := range players {
		if p.Club == "" {
			continue
		}
		a, ok := groups[p.Club]
		if !ok {
			a = &acc{clubID: p.ClubID}
			groups[p.Club] = a
		}
		a.count++
		a.overall += p.Overall
		a.age += p.Age
		if a.best == nil || p.Overall > a.best.Overall {
			a.best = p
		}
	}
	out := make([]ClubPlayerSummary, 0, len(groups))
	for club, a := range groups {
		s := ClubPlayerSummary{ClubID: a.clubID, Club: club, Players: a.count}
		if a.count > 0 {
			s.AvgOverall = round1(float64(a.overall) / float64(a.count))
			s.AvgAge = round1(float64(a.age) / float64(a.count))
		}
		if a.best != nil {
			s.MaxOverall = a.best.Overall
			s.TopPlayer = a.best.Name
		}
		out = append(out, s)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Players != out[j].Players {
			return out[i].Players > out[j].Players
		}
		if out[i].AvgOverall != out[j].AvgOverall {
			return out[i].AvgOverall > out[j].AvgOverall
		}
		return out[i].Club < out[j].Club
	})
	return out
}

// NationalityCount is one row of a nationality breakdown.
type NationalityCount struct {
	Nationality string  `json:"nationality"`
	Players     int     `json:"players"`
	AvgOverall  float64 `json:"avg_overall"`
}

// SummarizeByNationality groups players by country.
func SummarizeByNationality(players []*Player, limit int) []NationalityCount {
	type acc struct{ count, overall int }
	groups := map[string]*acc{}
	for _, p := range players {
		if p.Nationality == "" {
			continue
		}
		a, ok := groups[p.Nationality]
		if !ok {
			a = &acc{}
			groups[p.Nationality] = a
		}
		a.count++
		a.overall += p.Overall
	}
	out := make([]NationalityCount, 0, len(groups))
	for n, a := range groups {
		out = append(out, NationalityCount{
			Nationality: n, Players: a.count,
			AvgOverall: round1(float64(a.overall) / float64(a.count)),
		})
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Players != out[j].Players {
			return out[i].Players > out[j].Players
		}
		return out[i].Nationality < out[j].Nationality
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// TopSkills returns a player's highest rated attributes.
func TopSkills(p *Player, n int) []string {
	type kv struct {
		k string
		v int
	}
	list := make([]kv, 0, len(p.Skills))
	for k, v := range p.Skills {
		if strings.HasPrefix(k, "GK") && p.PositionGroup != "Goalkeeper" {
			continue
		}
		list = append(list, kv{k, v})
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].v != list[j].v {
			return list[i].v > list[j].v
		}
		return list[i].k < list[j].k
	})
	if n > 0 && len(list) > n {
		list = list[:n]
	}
	out := make([]string, 0, len(list))
	for _, kv := range list {
		out = append(out, kv.k)
	}
	return out
}
