// players.go — FIFA player search.
//
// The FIFA 19 database covers 15 Brazilian clubs (Flamengo, Palmeiras,
// Corinthians and São Paulo are not licensed in that edition), so club
// filters first try to resolve the club through the team registry and fall
// back to a substring match on the FIFA club name.
package main

import (
	"sort"
	"strings"
)

// positionGroups maps role words to FIFA position codes.
var positionGroups = map[string][]string{
	"forward":     {"ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"},
	"attacker":    {"ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"},
	"striker":     {"ST", "CF", "LS", "RS"},
	"winger":      {"LW", "RW", "LM", "RM"},
	"midfielder":  {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"},
	"defender":    {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper":  {"GK"},
	"keeper":      {"GK"},
	"fullback":    {"LB", "RB", "LWB", "RWB"},
	"centre back": {"CB", "LCB", "RCB"},
	"center back": {"CB", "LCB", "RCB"},
}

// PositionCodes turns "forwards", "GK", "st,cf" into a set of FIFA codes.
func PositionCodes(q string) map[string]bool {
	out := map[string]bool{}
	for _, part := range strings.Split(q, ",") {
		f := strings.TrimSpace(Fold(part))
		if f == "" {
			continue
		}
		f = strings.TrimSuffix(f, "s")
		if codes, ok := positionGroups[f]; ok {
			for _, c := range codes {
				out[c] = true
			}
			continue
		}
		out[strings.ToUpper(f)] = true
		if strings.HasSuffix(Fold(part), "s") && len(part) <= 4 {
			out[strings.ToUpper(Fold(part))] = true // e.g. "rs"/"ls"
		}
	}
	return out
}

// PlayerFilter selects FIFA players.
type PlayerFilter struct {
	Name               string
	Nationality        string
	Club               string
	ClubTeam           *Team
	Positions          map[string]bool
	MinOverall         int
	MaxAge             int
	BrazilianClubsOnly bool
}

// NameMatches does an accent-insensitive token match on a player name.
func NameMatches(name, query string) bool {
	hay := Fold(name)
	for _, tok := range strings.Fields(Fold(query)) {
		if !strings.Contains(hay, tok) {
			return false
		}
	}
	return true
}

// FilterPlayers returns players matching f (unsorted).
func (s *Store) FilterPlayers(f PlayerFilter) []*Player {
	nat := Fold(f.Nationality)
	club := Fold(f.Club)
	var out []*Player
	for _, p := range s.Players {
		if f.Name != "" && !NameMatches(p.Name, f.Name) {
			continue
		}
		if nat != "" && Fold(p.Nationality) != nat {
			continue
		}
		if f.ClubTeam != nil {
			if p.ClubTeam != f.ClubTeam {
				continue
			}
		} else if club != "" && !strings.Contains(Fold(p.Club), club) {
			continue
		}
		if f.BrazilianClubsOnly && p.ClubTeam == nil {
			continue
		}
		if len(f.Positions) > 0 && !f.Positions[p.Position] {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MaxAge > 0 && p.Age > f.MaxAge {
			continue
		}
		out = append(out, p)
	}
	return out
}

// SortPlayers orders players by the given key ("overall", "potential",
// "age", "name" or a skill column such as "Finishing").
func SortPlayers(ps []*Player, by string) {
	key := func(p *Player) int {
		switch Fold(by) {
		case "", "overall", "rating":
			return p.Overall
		case "potential":
			return p.Potential
		case "age":
			return -p.Age
		}
		for k, v := range p.Skills {
			if Fold(k) == Fold(by) {
				return v
			}
		}
		return p.Overall
	}
	sort.SliceStable(ps, func(i, j int) bool {
		if Fold(by) == "name" {
			return ps[i].Name < ps[j].Name
		}
		ki, kj := key(ps[i]), key(ps[j])
		if ki != kj {
			return ki > kj
		}
		if ps[i].Overall != ps[j].Overall {
			return ps[i].Overall > ps[j].Overall
		}
		return ps[i].Name < ps[j].Name
	})
}

// FuzzyPlayers finds players sharing any name token with the query, ranked
// by the number of shared tokens and then rating. Used for suggestions.
func (s *Store) FuzzyPlayers(query string, limit int) []*Player {
	qt := strings.Fields(Fold(query))
	type scored struct {
		p *Player
		n int
	}
	var hits []scored
	for _, p := range s.Players {
		ptoks := map[string]bool{}
		for _, t := range strings.Fields(Fold(p.Name)) {
			ptoks[t] = true
		}
		n := 0
		for _, t := range qt {
			if len(t) > 2 && ptoks[t] {
				n++
			}
		}
		if n > 0 {
			hits = append(hits, scored{p, n})
		}
	}
	sort.SliceStable(hits, func(i, j int) bool {
		if hits[i].n != hits[j].n {
			return hits[i].n > hits[j].n
		}
		return hits[i].p.Overall > hits[j].p.Overall
	})
	var out []*Player
	for i := 0; i < len(hits) && i < limit; i++ {
		out = append(out, hits[i].p)
	}
	return out
}

// TopSkills returns the n highest skill ratings of a player.
func TopSkills(p *Player, n int) []string {
	type kv struct {
		k string
		v int
	}
	var all []kv
	for k, v := range p.Skills {
		if strings.HasPrefix(k, "GK") && p.Position != "GK" {
			continue
		}
		all = append(all, kv{k, v})
	}
	sort.Slice(all, func(i, j int) bool {
		if all[i].v != all[j].v {
			return all[i].v > all[j].v
		}
		return all[i].k < all[j].k
	})
	var out []string
	for i := 0; i < len(all) && i < n; i++ {
		out = append(out, all[i].k+" "+itoa(all[i].v))
	}
	return out
}
