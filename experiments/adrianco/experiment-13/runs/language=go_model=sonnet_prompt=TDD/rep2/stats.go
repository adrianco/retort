package main

import "sort"

// GetStatistics returns statistics for the given competition/season and stat type.
// statType values: "avg_goals", "biggest_wins", "best_home_record"
// Returns a map with keys depending on statType:
//   - "avg_goals": {"avg_goals_per_match": float64, "total_goals": int, "match_count": int}
//   - "biggest_wins": {"biggest_wins": []Match}
//   - "best_home_record": {"best_home_record": []TeamStats}
func GetStatistics(db *Database, competition string, season int, statType string) map[string]interface{} {
	pool := matchesForCompetition(db, competition)

	// Filter by season
	var matches []Match
	for _, m := range pool {
		if season != 0 && m.Season != season {
			continue
		}
		matches = append(matches, m)
	}

	result := make(map[string]interface{})

	switch statType {
	case "avg_goals":
		totalGoals := 0
		for _, m := range matches {
			totalGoals += m.HomeGoals + m.AwayGoals
		}
		count := len(matches)
		var avg float64
		if count > 0 {
			avg = float64(totalGoals) / float64(count)
		}
		result["avg_goals_per_match"] = avg
		result["total_goals"] = totalGoals
		result["match_count"] = count

	case "biggest_wins":
		// Sort matches by absolute goal difference descending
		sorted := make([]Match, len(matches))
		copy(sorted, matches)
		sort.Slice(sorted, func(i, j int) bool {
			diffI := sorted[i].HomeGoals - sorted[i].AwayGoals
			if diffI < 0 {
				diffI = -diffI
			}
			diffJ := sorted[j].HomeGoals - sorted[j].AwayGoals
			if diffJ < 0 {
				diffJ = -diffJ
			}
			return diffI > diffJ
		})
		// Return top 10
		top := sorted
		if len(top) > 10 {
			top = top[:10]
		}
		result["biggest_wins"] = top

	case "best_home_record":
		// Aggregate home stats per team
		type homeEntry struct {
			wins, draws, losses, played int
		}
		table := make(map[string]*homeEntry)
		for _, m := range matches {
			if _, ok := table[m.HomeTeam]; !ok {
				table[m.HomeTeam] = &homeEntry{}
			}
			e := table[m.HomeTeam]
			e.played++
			switch {
			case m.HomeGoals > m.AwayGoals:
				e.wins++
			case m.HomeGoals == m.AwayGoals:
				e.draws++
			default:
				e.losses++
			}
		}
		var records []TeamStats
		for team, e := range table {
			records = append(records, TeamStats{
				Team:   team,
				Played: e.played,
				Wins:   e.wins,
				Draws:  e.draws,
				Losses: e.losses,
				Points: e.wins*3 + e.draws,
			})
		}
		sort.Slice(records, func(i, j int) bool {
			if records[i].Points != records[j].Points {
				return records[i].Points > records[j].Points
			}
			return records[i].Team < records[j].Team
		})
		result["best_home_record"] = records

	default:
		// Return basic match count for unknown stat types
		result["match_count"] = len(matches)
	}

	return result
}
