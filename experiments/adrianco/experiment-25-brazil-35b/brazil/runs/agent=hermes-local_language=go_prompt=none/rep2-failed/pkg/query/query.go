package query

import (
	"sort"
	"strings"
	"time"

	"brazilian-soccer-mcp/pkg/data"
	"brazilian-soccer-mcp/pkg/datautil"
	"brazilian-soccer-mcp/pkg/loader"
)

// QueryHandler provides query operations on loaded data.
type QueryHandler struct {
	manager *loader.Manager
}

// NewQueryHandler creates a new QueryHandler.
func NewQueryHandler(manager *loader.Manager) *QueryHandler {
	return &QueryHandler{manager: manager}
}

// SearchMatches finds matches by team name (matches either home or away).
func (q *QueryHandler) SearchMatches(teamName, competition, season string, dateStart, dateEnd string) []data.Match {
	normalized := datautil.NormalizeTeam(teamName)
	seasonInt := 0
	if season != "" {
		seasonInt = parseInt(season)
	}

	var results []data.Match
	matches := q.manager.AllMatches()

	for _, m := range matches {
		// Check team match
		nHome := datautil.NormalizeTeam(m.HomeTeam)
		nAway := datautil.NormalizeTeam(m.AwayTeam)
		teamMatches := datautil.MustContain(nHome, normalized) || datautil.MustContain(nAway, normalized)
		if !teamMatches {
			continue
		}

		// Check competition filter
		if competition != "" {
			srcMatch := false
			switch competition {
			case "brasileirao":
				srcMatch = m.Source == "brasileirao" || m.Source == "novo_campeonato" || m.Source == "br_football"
			case "copa do brasil", "brazilian cup":
				srcMatch = m.Source == "brazilian_cup" || m.Source == "br_football"
			case "libertadores":
				srcMatch = m.Source == "libertadores" || m.Source == "br_football"
			default:
				srcMatch = true // free text - match any source
			}
			if !srcMatch {
				continue
			}
		}

		// Check season filter
		if seasonInt > 0 && m.Season != seasonInt {
			continue
		}

		// Check date range
		if dateStart != "" {
			start := parseTimeStr(dateStart)
			if !start.IsZero() && m.DateTime.Before(start) {
				continue
			}
		}
		if dateEnd != "" {
			end := parseTimeStr(dateEnd)
			if !end.IsZero() && m.DateTime.After(end) {
				continue
			}
		}

		results = append(results, m)
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].DateTime.Before(results[j].DateTime)
	})
	return results
}

// SearchMatchesExact finds matches where both teams match exactly.
func (q *QueryHandler) SearchMatchesExact(team1, team2 string) []data.Match {
	n1 := datautil.NormalizeTeam(team1)
	n2 := datautil.NormalizeTeam(team2)
	var results []data.Match

	for _, m := range q.manager.AllMatches() {
		home := datautil.NormalizeTeam(m.HomeTeam)
		away := datautil.NormalizeTeam(m.AwayTeam)

		if (home == n1 && away == n2) || (home == n2 && away == n1) {
			results = append(results, m)
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].DateTime.Before(results[j].DateTime)
	})
	return results
}

// GetTeamStats returns aggregated stats for a team.
func (q *QueryHandler) GetTeamStats(teamName, competition, season string) data.TeamStats {
	nTeam := datautil.NormalizeTeam(teamName)
	matches := q.manager.AllMatches()

	stats := data.TeamStats{TeamName: teamName}
	for _, m := range matches {
		if !matchesTeam(m, nTeam) {
			continue
		}
		if competition != "" {
			if !matchCompetition(m, competition) {
				continue
			}
		}
		seasonInt := 0
		if season != "" {
			seasonInt = parseInt(season)
		}
		if seasonInt > 0 && m.Season != seasonInt {
			continue
		}

		stats.Matches++

		var homeScored, awayScored int
		if matchesTeamAsHome(m, nTeam) {
			homeScored = m.HomeGoals
			awayScored = m.AwayGoals
			stats.GoalsFor += m.HomeGoals
			stats.GoalsAgainst += m.AwayGoals
		} else {
			homeScored = m.AwayGoals
			awayScored = m.HomeGoals
			stats.GoalsFor += m.AwayGoals
			stats.GoalsAgainst += m.HomeGoals
		}

		if homeScored > awayScored {
			stats.Wins++
		} else if homeScored == awayScored {
			stats.Draws++
		} else {
			stats.Losses++
		}
	}

	if stats.Matches > 0 {
		stats.WinRate = float64(stats.Wins) / float64(stats.Matches) * 100
	}
	stats.GoalDiffer = stats.GoalsFor - stats.GoalsAgainst
	return stats
}

// GetHeadToHead returns head-to-head stats between two teams.
func (q *QueryHandler) GetHeadToHead(team1, team2 string) data.H2HRecord {
	n1 := datautil.NormalizeTeam(team1)
	n2 := datautil.NormalizeTeam(team2)
	result := data.H2HRecord{
		Team1Name: team1,
		Team2Name: team2,
	}

	for _, m := range q.manager.AllMatches() {
		home := datautil.NormalizeTeam(m.HomeTeam)
		away := datautil.NormalizeTeam(m.AwayTeam)

		if (home == n1 && away == n2) || (home == n2 && away == n1) {
			result.Matches = append(result.Matches, m)

			if matchesTeamAsHome(m, n1) {
				if m.HomeGoals > m.AwayGoals {
					result.Team1Wins++
				} else if m.HomeGoals == m.AwayGoals {
					result.Draws++
				} else {
					result.Team2Wins++
				}
			} else {
				if m.AwayGoals > m.HomeGoals {
					result.Team1Wins++
				} else if m.AwayGoals == m.HomeGoals {
					result.Draws++
				} else {
					result.Team2Wins++
				}
			}
		}
	}

	sort.Slice(result.Matches, func(i, j int) bool {
		return result.Matches[i].DateTime.Before(result.Matches[j].DateTime)
	})
	return result
}

// GetCompetitionStandings calculates standings for a competition/season.
func (q *QueryHandler) GetCompetitionStandings(competition, season string) []data.CompetitionStanding {
	nSeason := 0
	if season != "" {
		nSeason = parseInt(season)
	}

	teams := make(map[string]*data.CompetitionStanding)

	for _, m := range q.manager.AllMatches() {
		if !matchCompetition(m, competition) {
			continue
		}
		if nSeason > 0 && m.Season != nSeason {
			continue
		}

		nHome := datautil.NormalizeTeam(m.HomeTeam)
		nAway := datautil.NormalizeTeam(m.AwayTeam)

		if teams[nHome] == nil {
			teams[nHome] = &data.CompetitionStanding{TeamName: m.HomeTeam}
		}
		if teams[nAway] == nil {
			teams[nAway] = &data.CompetitionStanding{TeamName: m.AwayTeam}
		}

		teams[nHome].GoalsFor += m.HomeGoals
		teams[nHome].GoalsAgainst += m.AwayGoals
		teams[nAway].GoalsFor += m.AwayGoals
		teams[nAway].GoalsAgainst += m.HomeGoals

		if m.HomeGoals > m.AwayGoals {
			teams[nHome].Wins++
			teams[nHome].Points += 3
			teams[nAway].Losses++
		} else if m.HomeGoals == m.AwayGoals {
			teams[nHome].Draws++
			teams[nHome].Points++
			teams[nAway].Draws++
			teams[nAway].Points++
		} else {
			teams[nAway].Wins++
			teams[nAway].Points += 3
			teams[nHome].Losses++
		}
	}

	standings := make([]data.CompetitionStanding, 0, len(teams))
	for _, s := range teams {
		s.GoalDiff = s.GoalsFor - s.GoalsAgainst
		standings = append(standings, *s)
	}

	sort.Slice(standings, func(i, j int) bool {
		if standings[i].Points != standings[j].Points {
			return standings[i].Points > standings[j].Points
		}
		if standings[i].GoalDiff != standings[j].GoalDiff {
			return standings[i].GoalDiff > standings[j].GoalDiff
		}
		return standings[i].GoalsFor > standings[j].GoalsFor
	})

	for i := range standings {
		standings[i].Position = i + 1
	}

	return standings
}

// SearchPlayers searches players by name, nationality, or club.
func (q *QueryHandler) SearchPlayers(name, nationality, club, position string, minOverall int) []data.Player {
	nName := strings.ToLower(name)
	nNat := strings.ToLower(nationality)
	nClub := datautil.NormalizeTeam(club)
	nPos := strings.ToLower(position)

	var results []data.Player
	for _, p := range q.manager.Players {
		// Filter by name
		if name != "" && !strings.Contains(strings.ToLower(p.Name), nName) {
			continue
		}
		// Filter by nationality
		if nNat != "" && !strings.Contains(strings.ToLower(p.Nationality), nNat) {
			continue
		}
		// Filter by club
		if nClub != "" && !datautil.MustContain(datautil.NormalizeTeam(p.Club), nClub) {
			continue
		}
		// Filter by position
		if nPos != "" && !strings.Contains(strings.ToLower(p.Position), nPos) {
			continue
		}
		// Filter by minimum overall
		if minOverall > 0 && p.Overall < minOverall {
			continue
		}
		results = append(results, p)
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Overall > results[j].Overall
	})
	return results
}

// GetBiggestWins returns the biggest goal differences in the dataset.
func (q *QueryHandler) GetBiggestWins(competition string, limit int) []data.Match {
	matches := q.manager.AllMatches()
	if competition != "" {
		filtered := make([]data.Match, 0)
		for _, m := range matches {
			if matchCompetition(m, competition) {
				filtered = append(filtered, m)
			}
		}
		matches = filtered
	}

	sort.Slice(matches, func(i, j int) bool {
		diffI := matches[i].HomeGoals - matches[i].AwayGoals
		if diffI < 0 {
			diffI = -diffI
		}
		diffJ := matches[j].HomeGoals - matches[j].AwayGoals
		if diffJ < 0 {
			diffJ = -diffJ
		}
		return diffI > diffJ
	})

	if limit > 0 && len(matches) > limit {
		return matches[:limit]
	}
	return matches
}

// GetStatistics returns aggregated statistics for all matches or filtered.
func (q *QueryHandler) GetStatistics(competition string) data.StatResult {
	matches := q.manager.AllMatches()
	if competition != "" {
		filtered := make([]data.Match, 0)
		for _, m := range matches {
			if matchCompetition(m, competition) {
				filtered = append(filtered, m)
			}
		}
		matches = filtered
	}

	var result data.StatResult
	result.TotalMatches = len(matches)
	if result.TotalMatches == 0 {
		return result
	}

	for _, m := range matches {
		result.TotalGoals += float64(m.HomeGoals + m.AwayGoals)
		if m.HomeGoals > m.AwayGoals {
			result.HomeWinCount++
		} else if m.HomeGoals < m.AwayGoals {
			result.AwayWinCount++
		} else {
			result.DrawCount++
		}
	}

	result.AvgGoalsPerMatch = result.TotalGoals / float64(result.TotalMatches)
	result.HomeWinRate = float64(result.HomeWinCount) / float64(result.TotalMatches) * 100
	result.AwayWinRate = float64(result.AwayWinCount) / float64(result.TotalMatches) * 100
	result.DrawRate = float64(result.DrawCount) / float64(result.TotalMatches) * 100

	return result
}

// GetAllTeams returns unique normalized team names from all match data.
func (q *QueryHandler) GetAllTeams() map[string]string {
	teams := make(map[string]string)
	for _, m := range q.manager.AllMatches() {
		h := datautil.NormalizeTeam(m.HomeTeam)
		a := datautil.NormalizeTeam(m.AwayTeam)
		if _, ok := teams[h]; !ok {
			teams[h] = m.HomeTeam
		}
		if _, ok := teams[a]; !ok {
			teams[a] = m.AwayTeam
		}
	}
	return teams
}

// GetPlayersByClub returns players at a specific club.
func (q *QueryHandler) GetPlayersByClub(clubName string) []data.Player {
	nClub := datautil.NormalizeTeam(clubName)
	var results []data.Player
	for _, p := range q.manager.Players {
		if datautil.MustContain(datautil.NormalizeTeam(p.Club), nClub) {
			results = append(results, p)
		}
	}
	sort.Slice(results, func(i, j int) bool {
		return results[i].Overall > results[j].Overall
	})
	return results
}

// GetBrazilianPlayers returns Brazilian players.
func (q *QueryHandler) GetBrazilianPlayers(topN int) []data.Player {
	var brazilians []data.Player
	for _, p := range q.manager.Players {
		if strings.Contains(strings.ToLower(p.Nationality), "brazil") {
			brazilians = append(brazilians, p)
		}
	}
	sort.Slice(brazilians, func(i, j int) bool {
		return brazilians[i].Overall > brazilians[j].Overall
	})
	if topN > 0 && len(brazilians) > topN {
		return brazilians[:topN]
	}
	return brazilians
}

func matchesTeam(m data.Match, normalized string) bool {
	return datautil.NormalizeTeam(m.HomeTeam) == normalized || datautil.NormalizeTeam(m.AwayTeam) == normalized
}

func matchesTeamAsHome(m data.Match, normalized string) bool {
	return datautil.NormalizeTeam(m.HomeTeam) == normalized
}

func matchCompetition(m data.Match, competition string) bool {
	comp := strings.ToLower(competition)
	switch {
	case comp == "brasileirao":
		return m.Source == "brasileirao" || m.Source == "novo_campeonato" || m.Source == "br_football"
	case comp == "copa do brasil", comp == "brazilian cup":
		return m.Source == "brazilian_cup" || m.Source == "br_football"
	case comp == "libertadores":
		return m.Source == "libertadores" || m.Source == "br_football"
	default:
		return true
	}
}

func parseInt(s string) int {
	if s == "" {
		return 0
	}
	n := 0
	for _, c := range s {
		if c >= '0' && c <= '9' {
			n = n*10 + int(c-'0')
		}
	}
	return n
}

func parseTimeStr(s string) time.Time {
	formats := []string{
		"2006-01-02",
		"2006-01-02T15:04:05",
		"2006-01-02 15:04:05",
	}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t
		}
	}
	return time.Time{}
}
