package main

import "strings"

// SearchPlayers filters players by optional criteria.
// name, nationality, club, position are case-insensitive substring matches.
// minOverall filters by minimum overall rating (0 = no filter).
// limit=0 means no limit.
func SearchPlayers(players []Player, name, nationality, club, position string, minOverall, limit int) []Player {
	nameLower := strings.ToLower(name)
	natLower := strings.ToLower(nationality)
	clubLower := strings.ToLower(club)
	posLower := strings.ToLower(position)

	var results []Player
	for _, p := range players {
		if nameLower != "" && !strings.Contains(strings.ToLower(p.Name), nameLower) {
			continue
		}
		if natLower != "" && !strings.Contains(strings.ToLower(p.Nationality), natLower) {
			continue
		}
		if clubLower != "" && !strings.Contains(strings.ToLower(p.Club), clubLower) {
			continue
		}
		if posLower != "" && !strings.Contains(strings.ToLower(p.Position), posLower) {
			continue
		}
		if minOverall > 0 && p.Overall < minOverall {
			continue
		}
		results = append(results, p)
		if limit > 0 && len(results) >= limit {
			break
		}
	}
	return results
}
