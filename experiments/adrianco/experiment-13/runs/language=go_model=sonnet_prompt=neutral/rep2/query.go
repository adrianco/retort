package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// MatchFilter holds criteria for filtering matches.
type MatchFilter struct {
	Team        string    // matches either home or away team
	Team2       string    // when set, require both team and team2 to play
	Competition string    // competition name substring
	Season      int       // 0 means any
	DateFrom    time.Time // zero means no lower bound
	DateTo      time.Time // zero means no upper bound
	HomeOnly    bool      // only home matches for Team
	AwayOnly    bool      // only away matches for Team
}

// filterMatches returns matches that satisfy all non-zero criteria in f.
func filterMatches(matches []Match, f MatchFilter) []Match {
	var result []Match
	for _, m := range matches {
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !f.DateFrom.IsZero() && m.Date.Before(f.DateFrom) {
			continue
		}
		if !f.DateTo.IsZero() && m.Date.After(f.DateTo) {
			continue
		}
		if f.Competition != "" && !competitionMatchesQuery(m.Competition, f.Competition) {
			continue
		}
		if f.Team != "" {
			homeMatch := teamMatchesQuery(m.HomeTeam, f.Team)
			awayMatch := teamMatchesQuery(m.AwayTeam, f.Team)
			if f.HomeOnly && !homeMatch {
				continue
			}
			if f.AwayOnly && !awayMatch {
				continue
			}
			if !f.HomeOnly && !f.AwayOnly && !homeMatch && !awayMatch {
				continue
			}
			if f.Team2 != "" {
				opp1 := teamMatchesQuery(m.HomeTeam, f.Team2)
				opp2 := teamMatchesQuery(m.AwayTeam, f.Team2)
				if !opp1 && !opp2 {
					continue
				}
				// Avoid matching same team on both sides
				if homeMatch && opp1 && normalizeTeam(m.HomeTeam) == normalizeTeam(m.AwayTeam) {
					continue
				}
			}
		}
		result = append(result, m)
	}
	return result
}

// sortMatchesByDate sorts matches newest-first.
func sortMatchesByDate(matches []Match) {
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date.After(matches[j].Date)
	})
}

// TeamStats holds win/draw/loss statistics for a team.
type TeamStats struct {
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int
}

func (s TeamStats) GoalDiff() int { return s.GoalsFor - s.GoalsAgainst }
func (s TeamStats) WinRate() float64 {
	if s.Played == 0 {
		return 0
	}
	return float64(s.Wins) / float64(s.Played) * 100
}

// calcTeamStats computes statistics for a team across the provided matches.
// It assumes matches have already been filtered to include the team.
func calcTeamStats(team string, matches []Match) TeamStats {
	stats := TeamStats{Team: team}
	for _, m := range matches {
		isHome := teamMatchesQuery(m.HomeTeam, team)
		isAway := teamMatchesQuery(m.AwayTeam, team)
		if !isHome && !isAway {
			continue
		}
		stats.Played++
		if isHome {
			stats.GoalsFor += m.HomeGoals
			stats.GoalsAgainst += m.AwayGoals
			switch {
			case m.HomeGoals > m.AwayGoals:
				stats.Wins++
				stats.Points += 3
			case m.HomeGoals == m.AwayGoals:
				stats.Draws++
				stats.Points++
			default:
				stats.Losses++
			}
		} else {
			stats.GoalsFor += m.AwayGoals
			stats.GoalsAgainst += m.HomeGoals
			switch {
			case m.AwayGoals > m.HomeGoals:
				stats.Wins++
				stats.Points += 3
			case m.AwayGoals == m.HomeGoals:
				stats.Draws++
				stats.Points++
			default:
				stats.Losses++
			}
		}
	}
	return stats
}

// HeadToHeadResult holds the H2H record between two teams.
type HeadToHeadResult struct {
	Team1      string
	Team2      string
	Team1Wins  int
	Team2Wins  int
	Draws      int
	Total      int
	Matches    []Match
}

func headToHead(matches []Match, team1, team2 string) HeadToHeadResult {
	result := HeadToHeadResult{Team1: team1, Team2: team2}
	// Deduplicate before counting to avoid double-counting when the same match
	// appears in multiple CSV files with different team name formats.
	matches = dedupMatchesFuzzy(matches)
	for _, m := range matches {
		t1home := teamMatchesQuery(m.HomeTeam, team1)
		t1away := teamMatchesQuery(m.AwayTeam, team1)
		t2home := teamMatchesQuery(m.HomeTeam, team2)
		t2away := teamMatchesQuery(m.AwayTeam, team2)

		// Match must have one of team1 and one of team2 on different sides
		if (t1home && t2away) || (t1away && t2home) {
			result.Total++
			result.Matches = append(result.Matches, m)
			var homeWin bool
			if m.HomeGoals > m.AwayGoals {
				homeWin = true
			}
			switch {
			case m.HomeGoals == m.AwayGoals:
				result.Draws++
			case homeWin && t1home:
				result.Team1Wins++
			case homeWin && t2home:
				result.Team2Wins++
			case !homeWin && t1away:
				result.Team1Wins++
			case !homeWin && t2away:
				result.Team2Wins++
			}
		}
	}
	sortMatchesByDate(result.Matches)
	return result
}

// StandingsEntry represents a team's entry in the competition standings.
type StandingsEntry struct {
	TeamStats
	Rank int
}

// dedupMatches removes duplicate matches (same teams + same date) keeping first occurrence.
// Uses normalizeTeamKey (preserves state suffix) to distinguish e.g. Atletico-MG vs Atletico-GO.
// Suitable for standings calculations where team identity must be precise.
func dedupMatches(matches []Match) []Match {
	type key struct {
		home, away, date string
	}
	seen := make(map[key]bool, len(matches))
	result := make([]Match, 0, len(matches))
	for _, m := range matches {
		k := key{
			home: normalizeTeamKey(m.HomeTeam),
			away: normalizeTeamKey(m.AwayTeam),
			date: m.Date.Format("2006-01-02"),
		}
		if !seen[k] {
			seen[k] = true
			result = append(result, m)
		}
	}
	return result
}

// dedupMatchesFuzzy removes duplicate matches using full normalization (strips state suffix),
// so "Corinthians-SP" and "Corinthians" are treated as the same team.
// Suitable for user-facing search results and head-to-head displays.
func dedupMatchesFuzzy(matches []Match) []Match {
	type key struct {
		home, away, date string
	}
	seen := make(map[key]bool, len(matches))
	result := make([]Match, 0, len(matches))
	for _, m := range matches {
		k := key{
			home: normalizeTeam(m.HomeTeam),
			away: normalizeTeam(m.AwayTeam),
			date: m.Date.Format("2006-01-02"),
		}
		if !seen[k] {
			seen[k] = true
			result = append(result, m)
		}
	}
	return result
}

// competitionStandings calculates standings for a given competition and season.
func competitionStandings(matches []Match, competition string, season int) []StandingsEntry {
	filtered := filterMatches(matches, MatchFilter{
		Competition: competition,
		Season:      season,
	})
	// Deduplicate to handle the same match appearing in multiple CSV files
	filtered = dedupMatches(filtered)

	teamMap := make(map[string]*TeamStats)
	addTeam := func(name string) *TeamStats {
		// Use normalizeTeamKey (keeps state suffix) to distinguish e.g. Atletico-MG vs Atletico-GO
		key := normalizeTeamKey(name)
		if _, ok := teamMap[key]; !ok {
			teamMap[key] = &TeamStats{Team: name}
		}
		return teamMap[key]
	}

	for _, m := range filtered {
		home := addTeam(m.HomeTeam)
		away := addTeam(m.AwayTeam)

		home.Played++
		away.Played++
		home.GoalsFor += m.HomeGoals
		home.GoalsAgainst += m.AwayGoals
		away.GoalsFor += m.AwayGoals
		away.GoalsAgainst += m.HomeGoals

		switch {
		case m.HomeGoals > m.AwayGoals:
			home.Wins++
			home.Points += 3
			away.Losses++
		case m.HomeGoals == m.AwayGoals:
			home.Draws++
			home.Points++
			away.Draws++
			away.Points++
		default:
			home.Losses++
			away.Wins++
			away.Points += 3
		}
	}

	entries := make([]StandingsEntry, 0, len(teamMap))
	for _, s := range teamMap {
		entries = append(entries, StandingsEntry{TeamStats: *s})
	}

	sort.Slice(entries, func(i, j int) bool {
		a, b := entries[i], entries[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.GoalDiff() != b.GoalDiff() {
			return a.GoalDiff() > b.GoalDiff()
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})

	for i := range entries {
		entries[i].Rank = i + 1
	}
	return entries
}

// PlayerFilter holds criteria for searching players.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
}

// searchPlayers returns players matching the filter.
func searchPlayers(players []Player, f PlayerFilter) []Player {
	var result []Player
	for _, p := range players {
		if f.Name != "" && !strings.Contains(strings.ToLower(stripAccents(p.Name)), strings.ToLower(stripAccents(f.Name))) {
			continue
		}
		if f.Nationality != "" && !strings.Contains(strings.ToLower(p.Nationality), strings.ToLower(f.Nationality)) {
			continue
		}
		if f.Club != "" && !teamMatchesQuery(p.Club, f.Club) {
			continue
		}
		if f.Position != "" && !strings.Contains(strings.ToLower(p.Position), strings.ToLower(f.Position)) {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		result = append(result, p)
	}
	return result
}

// sortPlayersByOverall sorts players by overall rating descending.
func sortPlayersByOverall(players []Player) {
	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})
}

// BiggestWin represents a match result with the goal margin.
type BiggestWin struct {
	Match  Match
	Margin int
	Winner string
	Loser  string
}

// biggestWins returns the matches with the largest goal differences.
func biggestWins(matches []Match, limit int) []BiggestWin {
	var wins []BiggestWin
	for _, m := range matches {
		diff := m.HomeGoals - m.AwayGoals
		if diff < 0 {
			diff = -diff
		}
		if diff == 0 {
			continue
		}
		winner, loser := m.HomeTeam, m.AwayTeam
		if m.AwayGoals > m.HomeGoals {
			winner, loser = m.AwayTeam, m.HomeTeam
		}
		wins = append(wins, BiggestWin{Match: m, Margin: diff, Winner: winner, Loser: loser})
	}
	sort.Slice(wins, func(i, j int) bool {
		if wins[i].Margin != wins[j].Margin {
			return wins[i].Margin > wins[j].Margin
		}
		return wins[i].Match.Date.After(wins[j].Match.Date)
	})
	if limit > 0 && len(wins) > limit {
		wins = wins[:limit]
	}
	return wins
}

// OverallStats holds aggregate match statistics.
type OverallStats struct {
	TotalMatches  int
	TotalGoals    int
	HomeWins      int
	AwayWins      int
	Draws         int
	AvgGoals      float64
	HomeWinRate   float64
	AwayWinRate   float64
	DrawRate      float64
}

func calcOverallStats(matches []Match) OverallStats {
	var s OverallStats
	s.TotalMatches = len(matches)
	for _, m := range matches {
		s.TotalGoals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			s.HomeWins++
		case m.AwayGoals > m.HomeGoals:
			s.AwayWins++
		default:
			s.Draws++
		}
	}
	if s.TotalMatches > 0 {
		s.AvgGoals = float64(s.TotalGoals) / float64(s.TotalMatches)
		s.HomeWinRate = float64(s.HomeWins) / float64(s.TotalMatches) * 100
		s.AwayWinRate = float64(s.AwayWins) / float64(s.TotalMatches) * 100
		s.DrawRate = float64(s.Draws) / float64(s.TotalMatches) * 100
	}
	return s
}

// formatMatch returns a human-readable single-line match summary.
func formatMatch(m Match) string {
	dateStr := "unknown date"
	if !m.Date.IsZero() {
		dateStr = m.Date.Format("2006-01-02")
	}
	line := fmt.Sprintf("%s: %s %d-%d %s (%s", dateStr, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Competition)
	if m.Season > 0 {
		line += fmt.Sprintf(" %d", m.Season)
	}
	if m.Round != "" {
		line += fmt.Sprintf(", Round %s", m.Round)
	}
	if m.Stage != "" {
		line += fmt.Sprintf(", %s", m.Stage)
	}
	line += ")"
	return line
}

// formatPlayer returns a human-readable player summary.
func formatPlayer(p Player) string {
	return fmt.Sprintf("%s | Overall: %d | Position: %s | Club: %s | Nationality: %s | Age: %d",
		p.Name, p.Overall, p.Position, p.Club, p.Nationality, p.Age)
}

// topScoringTeams returns teams with the most goals in the filtered matches.
func topScoringTeams(matches []Match, limit int) []TeamStats {
	teamMap := make(map[string]*TeamStats)
	for _, m := range matches {
		homeKey := normalizeTeamKey(m.HomeTeam)
		awayKey := normalizeTeamKey(m.AwayTeam)
		if _, ok := teamMap[homeKey]; !ok {
			teamMap[homeKey] = &TeamStats{Team: m.HomeTeam}
		}
		if _, ok := teamMap[awayKey]; !ok {
			teamMap[awayKey] = &TeamStats{Team: m.AwayTeam}
		}
		teamMap[homeKey].GoalsFor += m.HomeGoals
		teamMap[homeKey].Played++
		teamMap[awayKey].GoalsFor += m.AwayGoals
		teamMap[awayKey].Played++
	}

	result := make([]TeamStats, 0, len(teamMap))
	for _, s := range teamMap {
		result = append(result, *s)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].GoalsFor > result[j].GoalsFor
	})
	if limit > 0 && len(result) > limit {
		result = result[:limit]
	}
	return result
}

// bestHomeRecord returns teams with the best home win rate (min matches threshold).
func bestHomeRecord(matches []Match, minMatches, limit int) []TeamStats {
	teamMap := make(map[string]*TeamStats)
	for _, m := range matches {
		key := normalizeTeamKey(m.HomeTeam)
		if _, ok := teamMap[key]; !ok {
			teamMap[key] = &TeamStats{Team: m.HomeTeam}
		}
		s := teamMap[key]
		s.Played++
		s.GoalsFor += m.HomeGoals
		s.GoalsAgainst += m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			s.Wins++
			s.Points += 3
		case m.HomeGoals == m.AwayGoals:
			s.Draws++
			s.Points++
		default:
			s.Losses++
		}
	}

	result := make([]TeamStats, 0, len(teamMap))
	for _, s := range teamMap {
		if s.Played >= minMatches {
			result = append(result, *s)
		}
	}
	sort.Slice(result, func(i, j int) bool {
		ri, rj := result[i].WinRate(), result[j].WinRate()
		if ri != rj {
			return ri > rj
		}
		return result[i].Played > result[j].Played
	})
	if limit > 0 && len(result) > limit {
		result = result[:limit]
	}
	return result
}
