package main

import (
	"sort"
	"strings"
)

// --- SearchMatches ---

type SearchMatchesParams struct {
	Team        string // matches either home or away
	HomeTeam    string
	AwayTeam    string
	StartDate   string
	EndDate     string
	Competition string
	Season      int
	Limit       int
}

// SearchMatches filters matches by the given parameters.
func SearchMatches(db *Database, p SearchMatchesParams) []Match {
	compKey := competitionKey(p.Competition)
	var results []Match

	for _, m := range db.Matches {
		// Competition filter
		if compKey != "all" && competitionKey(m.Competition) != compKey {
			continue
		}
		// Season filter
		if p.Season != 0 && m.Season != p.Season {
			continue
		}
		// Team filter (home or away)
		if p.Team != "" {
			if !teamContains(m.HomeTeam, p.Team) && !teamContains(m.AwayTeam, p.Team) {
				continue
			}
		}
		// Specific home/away filters
		if p.HomeTeam != "" && !teamContains(m.HomeTeam, p.HomeTeam) {
			continue
		}
		if p.AwayTeam != "" && !teamContains(m.AwayTeam, p.AwayTeam) {
			continue
		}
		// Date range filter
		if p.StartDate != "" && m.Date < p.StartDate {
			continue
		}
		if p.EndDate != "" && m.Date > p.EndDate {
			continue
		}
		results = append(results, m)
	}

	// Sort by date descending (most recent first)
	sort.Slice(results, func(i, j int) bool {
		return results[i].Date > results[j].Date
	})

	if p.Limit > 0 && len(results) > p.Limit {
		results = results[:p.Limit]
	}
	return results
}

// --- GetHeadToHead ---

type GetHeadToHeadParams struct {
	Competition string
	Season      int
}

type HeadToHeadResult struct {
	Team1        string
	Team2        string
	TotalMatches int
	Team1Wins    int
	Team2Wins    int
	Draws        int
	Team1Goals   int
	Team2Goals   int
	Matches      []Match
}

// GetHeadToHead returns the head-to-head record between two teams.
func GetHeadToHead(db *Database, team1, team2 string, p GetHeadToHeadParams) HeadToHeadResult {
	result := HeadToHeadResult{Team1: team1, Team2: team2}
	compKey := competitionKey(p.Competition)

	for _, m := range db.Matches {
		if compKey != "all" && competitionKey(m.Competition) != compKey {
			continue
		}
		if p.Season != 0 && m.Season != p.Season {
			continue
		}

		t1Home := teamContains(m.HomeTeam, team1) && teamContains(m.AwayTeam, team2)
		t1Away := teamContains(m.HomeTeam, team2) && teamContains(m.AwayTeam, team1)

		if !t1Home && !t1Away {
			continue
		}

		result.TotalMatches++
		result.Matches = append(result.Matches, m)

		if t1Home {
			result.Team1Goals += m.HomeGoal
			result.Team2Goals += m.AwayGoal
			if m.HomeGoal > m.AwayGoal {
				result.Team1Wins++
			} else if m.AwayGoal > m.HomeGoal {
				result.Team2Wins++
			} else {
				result.Draws++
			}
		} else {
			result.Team1Goals += m.AwayGoal
			result.Team2Goals += m.HomeGoal
			if m.AwayGoal > m.HomeGoal {
				result.Team1Wins++
			} else if m.HomeGoal > m.AwayGoal {
				result.Team2Wins++
			} else {
				result.Draws++
			}
		}
	}

	// Sort matches by date descending
	sort.Slice(result.Matches, func(i, j int) bool {
		return result.Matches[i].Date > result.Matches[j].Date
	})

	return result
}

// --- GetTeamStats ---

type GetTeamStatsParams struct {
	Competition string
	Season      int
	HomeOnly    bool
	AwayOnly    bool
}

// GetTeamStats returns statistics for a team.
func GetTeamStats(db *Database, team string, p GetTeamStatsParams) TeamRecord {
	compKey := competitionKey(p.Competition)
	rec := TeamRecord{Team: team}

	for _, m := range db.Matches {
		if compKey != "all" && competitionKey(m.Competition) != compKey {
			continue
		}
		if p.Season != 0 && m.Season != p.Season {
			continue
		}

		isHome := teamContains(m.HomeTeam, team)
		isAway := teamContains(m.AwayTeam, team)

		if !isHome && !isAway {
			continue
		}
		if p.HomeOnly && !isHome {
			continue
		}
		if p.AwayOnly && !isAway {
			continue
		}

		rec.Played++
		if isHome {
			rec.GF += m.HomeGoal
			rec.GA += m.AwayGoal
			if m.HomeGoal > m.AwayGoal {
				rec.Wins++
			} else if m.HomeGoal == m.AwayGoal {
				rec.Draws++
			} else {
				rec.Losses++
			}
		} else {
			rec.GF += m.AwayGoal
			rec.GA += m.HomeGoal
			if m.AwayGoal > m.HomeGoal {
				rec.Wins++
			} else if m.AwayGoal == m.HomeGoal {
				rec.Draws++
			} else {
				rec.Losses++
			}
		}
	}

	rec.GD = rec.GF - rec.GA
	rec.Points = rec.Wins*3 + rec.Draws
	return rec
}

// --- GetStandings ---

// GetStandings computes a league table for a given competition and season.
func GetStandings(db *Database, competition string, season int) []TeamRecord {
	compKey := competitionKey(competition)
	teamMap := make(map[string]*TeamRecord)

	// Use teamGroupKey (full name, state-preserving) as map key so
	// "Atletico-MG" and "Atletico-PR" remain distinct entries in the standings.
	// Display the raw name (with state suffix when present) for disambiguation.
	getOrCreate := func(rawName string) *TeamRecord {
		key := teamGroupKey(rawName)
		if r, ok := teamMap[key]; ok {
			return r
		}
		r := &TeamRecord{Team: strings.TrimSpace(rawName)}
		teamMap[key] = r
		return r
	}

	for _, m := range db.Matches {
		if compKey != "all" && competitionKey(m.Competition) != compKey {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}

		home := getOrCreate(m.HomeTeam)
		away := getOrCreate(m.AwayTeam)

		home.Played++
		away.Played++
		home.GF += m.HomeGoal
		home.GA += m.AwayGoal
		away.GF += m.AwayGoal
		away.GA += m.HomeGoal

		if m.HomeGoal > m.AwayGoal {
			home.Wins++
			home.Points += 3
			away.Losses++
		} else if m.HomeGoal == m.AwayGoal {
			home.Draws++
			home.Points++
			away.Draws++
			away.Points++
		} else {
			away.Wins++
			away.Points += 3
			home.Losses++
		}
	}

	standings := make([]TeamRecord, 0, len(teamMap))
	for _, r := range teamMap {
		r.GD = r.GF - r.GA
		standings = append(standings, *r)
	}

	sort.Slice(standings, func(i, j int) bool {
		if standings[i].Points != standings[j].Points {
			return standings[i].Points > standings[j].Points
		}
		if standings[i].GD != standings[j].GD {
			return standings[i].GD > standings[j].GD
		}
		return standings[i].GF > standings[j].GF
	})

	return standings
}

// --- SearchPlayers ---

type SearchPlayersParams struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// SearchPlayers filters players by the given parameters, sorted by Overall desc.
func SearchPlayers(db *Database, p SearchPlayersParams) []Player {
	var results []Player

	for _, pl := range db.Players {
		if p.Name != "" && !strings.Contains(strings.ToLower(pl.Name), strings.ToLower(p.Name)) {
			continue
		}
		if p.Nationality != "" && !strings.EqualFold(pl.Nationality, p.Nationality) {
			continue
		}
		if p.Club != "" && !strings.Contains(strings.ToLower(pl.Club), strings.ToLower(p.Club)) {
			continue
		}
		if p.Position != "" && !strings.EqualFold(pl.Position, p.Position) {
			continue
		}
		if p.MinOverall > 0 && pl.Overall < p.MinOverall {
			continue
		}
		results = append(results, pl)
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Overall > results[j].Overall
	})

	if p.Limit > 0 && len(results) > p.Limit {
		results = results[:p.Limit]
	}
	return results
}

// --- GetStatistics ---

type GetStatisticsParams struct {
	Competition string
	Season      int
	Limit       int
}

type StatisticsResult struct {
	GoalsPerMatch float64
	HomeWinRate   float64
	AwayWinRate   float64
	DrawRate      float64
	TotalMatches  int
	BiggestWins   []Match
}

// GetStatistics computes aggregate statistics for matches.
func GetStatistics(db *Database, statType string, p GetStatisticsParams) StatisticsResult {
	compKey := competitionKey(p.Competition)
	limit := p.Limit
	if limit == 0 {
		limit = 10
	}

	var filtered []Match
	for _, m := range db.Matches {
		if compKey != "all" && competitionKey(m.Competition) != compKey {
			continue
		}
		if p.Season != 0 && m.Season != p.Season {
			continue
		}
		filtered = append(filtered, m)
	}

	result := StatisticsResult{TotalMatches: len(filtered)}
	if len(filtered) == 0 {
		return result
	}

	totalGoals := 0
	homeWins, awayWins, draws := 0, 0, 0
	for _, m := range filtered {
		totalGoals += m.HomeGoal + m.AwayGoal
		if m.HomeGoal > m.AwayGoal {
			homeWins++
		} else if m.AwayGoal > m.HomeGoal {
			awayWins++
		} else {
			draws++
		}
	}

	n := float64(len(filtered))
	result.GoalsPerMatch = float64(totalGoals) / n
	result.HomeWinRate = float64(homeWins) / n
	result.AwayWinRate = float64(awayWins) / n
	result.DrawRate = float64(draws) / n

	// Biggest wins: sort by goal margin descending
	sorted := make([]Match, len(filtered))
	copy(sorted, filtered)
	sort.Slice(sorted, func(i, j int) bool {
		mi := sorted[i].HomeGoal - sorted[i].AwayGoal
		if mi < 0 {
			mi = -mi
		}
		mj := sorted[j].HomeGoal - sorted[j].AwayGoal
		if mj < 0 {
			mj = -mj
		}
		return mi > mj
	})
	if limit > len(sorted) {
		limit = len(sorted)
	}
	result.BiggestWins = sorted[:limit]

	return result
}
