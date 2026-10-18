// FIFA player data: model, parsing and queries.

package main

import (
	"sort"
	"strings"
)

// Player is one row of fifa_data.csv.
type Player struct {
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string
	Jersey      int
	Value       string
	Wage        string
	Height      string
	Weight      string
	Foot        string
}

func parsePlayers(rows []row) []Player {
	out := make([]Player, 0, len(rows))
	for _, r := range rows {
		name := r.get("name")
		if name == "" {
			continue
		}
		out = append(out, Player{
			Name:        name,
			Age:         atoi(r.get("age")),
			Nationality: r.get("nationality"),
			Overall:     atoi(r.get("overall")),
			Potential:   atoi(r.get("potential")),
			Club:        r.get("club"),
			Position:    strings.ToUpper(r.get("position")),
			Jersey:      atoi(r.get("jersey number")),
			Value:       r.get("value"),
			Wage:        r.get("wage"),
			Height:      r.get("height"),
			Weight:      r.get("weight"),
			Foot:        r.get("preferred foot"),
		})
	}
	return out
}

// PlayerFilter selects players. Empty fields are ignored.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	// BrazilianClubsOnly restricts to clubs that appear in the Brasileirão files.
	BrazilianClubsOnly bool
}

// SearchPlayers returns matching players sorted by overall rating, then name.
func (ds *Dataset) SearchPlayers(f PlayerFilter) []Player {
	name := stripAccents(f.Name)
	nat := stripAccents(f.Nationality)
	club := stripAccents(f.Club)
	pos := strings.ToUpper(strings.TrimSpace(f.Position))

	var out []Player
	for _, p := range ds.Players {
		if name != "" && !strings.Contains(stripAccents(p.Name), name) {
			continue
		}
		if nat != "" && stripAccents(p.Nationality) != nat {
			continue
		}
		if club != "" && !strings.Contains(stripAccents(p.Club), club) {
			continue
		}
		if pos != "" && !positionMatches(p.Position, pos) {
			continue
		}
		if p.Overall < f.MinOverall {
			continue
		}
		if f.BrazilianClubsOnly && !ds.BrazilianClubs[ParseTeam(p.Club, "").Base] {
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
	return out
}

// positionGroups maps broad position words to FIFA position codes.
var positionGroups = map[string][]string{
	"FORWARD":    {"ST", "CF", "LW", "RW", "LF", "RF", "RS", "LS"},
	"MIDFIELDER": {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"},
	"DEFENDER":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"GOALKEEPER": {"GK"},
}

// positionMatches accepts an exact FIFA code ("ST") or a group ("FORWARD").
func positionMatches(playerPos, want string) bool {
	if playerPos == want {
		return true
	}
	for _, code := range positionGroups[want] {
		if playerPos == code {
			return true
		}
	}
	return false
}

// ClubAverageOverall returns the number of players and average overall for a club.
func ClubAverageOverall(players []Player) (int, float64) {
	if len(players) == 0 {
		return 0, 0
	}
	sum := 0
	for _, p := range players {
		sum += p.Overall
	}
	return len(players), float64(sum) / float64(len(players))
}
