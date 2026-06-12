package main

import (
	"sort"
	"strings"
	"time"
)

// allMatches returns all matches across all competitions in the database.
func allMatches(db *Database) []Match {
	var all []Match
	all = append(all, db.Brasileirao...)
	all = append(all, db.Copa...)
	all = append(all, db.Libertadores...)
	all = append(all, db.BRFootball...)
	all = append(all, db.Historico...)
	return all
}

// matchesForCompetition returns the slice for the named competition (or all if empty).
func matchesForCompetition(db *Database, competition string) []Match {
	switch strings.ToLower(competition) {
	case CompBrasileirao:
		return db.Brasileirao
	case CompCopa:
		return db.Copa
	case CompLibertadores:
		return db.Libertadores
	case CompBRFootball:
		return db.BRFootball
	case CompHistorico:
		return db.Historico
	case "":
		return allMatches(db)
	default:
		return nil
	}
}

// SearchMatches filters matches by optional criteria.
// team matches either home or away team (substring after normalize).
// homeTeam / awayTeam are positional filters.
// competition, season, dateFrom, dateTo all filter as expected.
// limit=0 means no limit.
func SearchMatches(db *Database, team, homeTeam, awayTeam, competition string, season int, dateFrom, dateTo time.Time, limit int) []Match {
	pool := matchesForCompetition(db, competition)

	var results []Match
	for _, m := range pool {
		if team != "" {
			if !TeamMatches(team, m.HomeTeam) && !TeamMatches(team, m.AwayTeam) {
				continue
			}
		}
		if homeTeam != "" && !TeamMatches(homeTeam, m.HomeTeam) {
			continue
		}
		if awayTeam != "" && !TeamMatches(awayTeam, m.AwayTeam) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if !dateFrom.IsZero() && m.DateTime.Before(dateFrom) {
			continue
		}
		if !dateTo.IsZero() && m.DateTime.After(dateTo) {
			continue
		}
		results = append(results, m)
		if limit > 0 && len(results) >= limit {
			break
		}
	}
	return results
}

// HeadToHead returns win/draw/loss stats for team1 against team2 across all
// (or filtered) matches. Stats are from team1's perspective.
func HeadToHead(db *Database, team1, team2, competition string, season int) map[string]interface{} {
	pool := matchesForCompetition(db, competition)

	wins, draws, losses := 0, 0, 0
	goalsFor, goalsAgainst := 0, 0
	played := 0

	for _, m := range pool {
		if season != 0 && m.Season != season {
			continue
		}
		t1Home := TeamMatches(team1, m.HomeTeam) && TeamMatches(team2, m.AwayTeam)
		t1Away := TeamMatches(team1, m.AwayTeam) && TeamMatches(team2, m.HomeTeam)
		if !t1Home && !t1Away {
			continue
		}
		played++
		if t1Home {
			goalsFor += m.HomeGoals
			goalsAgainst += m.AwayGoals
			if m.HomeGoals > m.AwayGoals {
				wins++
			} else if m.HomeGoals == m.AwayGoals {
				draws++
			} else {
				losses++
			}
		} else {
			goalsFor += m.AwayGoals
			goalsAgainst += m.HomeGoals
			if m.AwayGoals > m.HomeGoals {
				wins++
			} else if m.AwayGoals == m.HomeGoals {
				draws++
			} else {
				losses++
			}
		}
	}
	return map[string]interface{}{
		"team1":         team1,
		"team2":         team2,
		"played":        played,
		"wins":          wins,
		"draws":         draws,
		"losses":        losses,
		"goals_for":     goalsFor,
		"goals_against": goalsAgainst,
	}
}

// GetTeamStats returns aggregated stats for a team in the given competition/season.
func GetTeamStats(db *Database, team, competition string, season int) *TeamStats {
	pool := matchesForCompetition(db, competition)

	stats := &TeamStats{Team: team}
	for _, m := range pool {
		if season != 0 && m.Season != season {
			continue
		}
		isHome := TeamMatches(team, m.HomeTeam)
		isAway := TeamMatches(team, m.AwayTeam)
		if !isHome && !isAway {
			continue
		}
		stats.Played++
		if isHome {
			stats.GoalsFor += m.HomeGoals
			stats.GoalsAgainst += m.AwayGoals
			if m.HomeGoals > m.AwayGoals {
				stats.Wins++
			} else if m.HomeGoals == m.AwayGoals {
				stats.Draws++
			} else {
				stats.Losses++
			}
		} else {
			stats.GoalsFor += m.AwayGoals
			stats.GoalsAgainst += m.HomeGoals
			if m.AwayGoals > m.HomeGoals {
				stats.Wins++
			} else if m.AwayGoals == m.HomeGoals {
				stats.Draws++
			} else {
				stats.Losses++
			}
		}
	}
	stats.Points = stats.Wins*3 + stats.Draws
	return stats
}

// GetStandings calculates and returns a sorted standings table.
func GetStandings(db *Database, season int, competition string) []Standing {
	pool := matchesForCompetition(db, competition)

	type entry struct {
		played, wins, draws, losses, goalsFor, goalsAgainst int
	}
	table := make(map[string]*entry)

	ensure := func(team string) {
		if _, ok := table[team]; !ok {
			table[team] = &entry{}
		}
	}

	for _, m := range pool {
		if season != 0 && m.Season != season {
			continue
		}
		ensure(m.HomeTeam)
		ensure(m.AwayTeam)
		home := table[m.HomeTeam]
		away := table[m.AwayTeam]

		home.played++
		away.played++
		home.goalsFor += m.HomeGoals
		home.goalsAgainst += m.AwayGoals
		away.goalsFor += m.AwayGoals
		away.goalsAgainst += m.HomeGoals

		switch {
		case m.HomeGoals > m.AwayGoals:
			home.wins++
			away.losses++
		case m.HomeGoals == m.AwayGoals:
			home.draws++
			away.draws++
		default:
			home.losses++
			away.wins++
		}
	}

	standings := make([]Standing, 0, len(table))
	for team, e := range table {
		s := Standing{
			Team:         team,
			Played:       e.played,
			Wins:         e.wins,
			Draws:        e.draws,
			Losses:       e.losses,
			GoalsFor:     e.goalsFor,
			GoalsAgainst: e.goalsAgainst,
			GoalDiff:     e.goalsFor - e.goalsAgainst,
			Points:       e.wins*3 + e.draws,
		}
		standings = append(standings, s)
	}

	// Sort: points desc, goal diff desc, goals for desc, name asc
	sort.Slice(standings, func(i, j int) bool {
		if standings[i].Points != standings[j].Points {
			return standings[i].Points > standings[j].Points
		}
		if standings[i].GoalDiff != standings[j].GoalDiff {
			return standings[i].GoalDiff > standings[j].GoalDiff
		}
		if standings[i].GoalsFor != standings[j].GoalsFor {
			return standings[i].GoalsFor > standings[j].GoalsFor
		}
		return standings[i].Team < standings[j].Team
	})

	for i := range standings {
		standings[i].Position = i + 1
	}
	return standings
}
