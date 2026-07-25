package query

import (
	"fmt"
	"sort"
	"strings"

	"brazilian-soccer-mcp/data"
	"brazilian-soccer-mcp/model"
)

// QueryHandler handles soccer data queries
type QueryHandler struct {
	dataLoader *data.DataLoader
}

// NewQueryHandler creates a new QueryHandler
func NewQueryHandler(dataLoader *data.DataLoader) *QueryHandler {
	return &QueryHandler{
		dataLoader: dataLoader,
	}
}

// MatchQuery represents a match search query
type MatchQuery struct {
	HomeTeam    string
	AwayTeam    string
	Tournament  string
	Season      string
	DateTime    string
	Limit       int
	Offset      int
}

// TeamQuery represents a team statistics query
type TeamQuery struct {
	Team     string
	Season   string
	Tournament string
}

// PlayerQuery represents a player search query
type PlayerQuery struct {
	Name         string
	Nationality  string
	Club         string
	Position     string
	MinOverall   int
	Limit        int
	Offset       int
}

// SearchMatches searches for matches based on criteria
func (qh *QueryHandler) SearchMatches(query *MatchQuery) ([]model.Match, int, error) {
	matches := qh.dataLoader.GetMatches()

	var result []model.Match
	for _, match := range matches {
		if query.HomeTeam != "" && !strings.Contains(strings.ToLower(match.HomeTeam), strings.ToLower(query.HomeTeam)) {
			continue
		}
		if query.AwayTeam != "" && !strings.Contains(strings.ToLower(match.AwayTeam), strings.ToLower(query.AwayTeam)) {
			continue
		}
		if query.Tournament != "" && !strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(query.Tournament)) {
			continue
		}
		if query.Season != "" && match.Season != query.Season {
			continue
		}

		result = append(result, match)
	}

	// Apply pagination
	total := len(result)
	if query.Offset > 0 && query.Offset < total {
		result = result[query.Offset:]
	}
	if query.Limit > 0 && len(result) > query.Limit {
		result = result[:query.Limit]
	}

	return result, total, nil
}

// GetTeamStats calculates team statistics
func (qh *QueryHandler) GetTeamStats(query *TeamQuery) (*model.TeamStats, error) {
	matches := qh.dataLoader.GetMatches()
	team := query.Team
	season := query.Season
	tournament := query.Tournament

	stats := &model.TeamStats{
		Team: team,
	}

	for _, match := range matches {
		// Filter by tournament if specified
		if tournament != "" && !strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(tournament)) {
			continue
		}
		// Filter by season if specified
		if season != "" && match.Season != season {
			continue
		}

		// Check if team played (home or away)
		isHome := strings.EqualFold(match.HomeTeam, team)
		isAway := strings.EqualFold(match.AwayTeam, team)

		if !isHome && !isAway {
			continue
		}

		stats.Matches++
		stats.GoalsFor += match.HomeGoal
		stats.GoalsAgainst += match.AwayGoal

		if isHome {
			stats.HomeMatches++
			stats.HomeGoalsFor += match.HomeGoal
			stats.HomeGoalsAgainst += match.AwayGoal
		} else {
			stats.AwayMatches++
			stats.AwayGoalsFor += match.AwayGoal
			stats.AwayGoalsAgainst += match.HomeGoal
		}

		if match.HomeGoal > match.AwayGoal {
			if isHome {
				stats.Wins++
			} else {
				stats.Losses++
			}
		} else if match.HomeGoal < match.AwayGoal {
			if isHome {
				stats.Losses++
			} else {
				stats.Wins++
			}
		} else {
			stats.Draws++
		}
	}

	stats.GoalDifference = stats.GoalsFor - stats.GoalsAgainst
	stats.Points = stats.Wins*3 + stats.Draws

	return stats, nil
}

// GetTeamHeadToHead calculates head-to-head between two teams
func (qh *QueryHandler) GetTeamHeadToHead(team1, team2 string) (*model.TeamHeadToHead, error) {
	matches := qh.dataLoader.GetMatches()
	h2h := &model.TeamHeadToHead{
		Team1: team1,
		Team2: team2,
	}

	var matchesList []model.Match
	for _, match := range matches {
		team1Played := strings.EqualFold(match.HomeTeam, team1) || strings.EqualFold(match.AwayTeam, team1)
		team2Played := strings.EqualFold(match.HomeTeam, team2) || strings.EqualFold(match.AwayTeam, team2)

		if team1Played && team2Played {
			h2h.Matches++
			h2h.Team1GoalsFor += match.HomeGoal
			h2h.Team2GoalsFor += match.AwayGoal

			if strings.EqualFold(match.HomeTeam, team1) || strings.EqualFold(match.AwayTeam, team2) {
				if match.HomeGoal > match.AwayGoal {
					h2h.Team1Wins++
				} else if match.HomeGoal < match.AwayGoal {
					h2h.Team2Wins++
				} else {
					h2h.Draws++
				}
			} else {
				if match.HomeGoal > match.AwayGoal {
					h2h.Team2Wins++
				} else if match.HomeGoal < match.AwayGoal {
					h2h.Team1Wins++
				} else {
					h2h.Draws++
				}
			}

			matchesList = append(matchesList, match)
		}
	}

	// Sort matches by date (most recent first)
	sort.Slice(matchesList, func(i, j int) bool {
		return matchesList[i].DateTime > matchesList[j].DateTime
	})
	h2h.MatchesList = matchesList

	return h2h, nil
}

// SearchPlayers searches for players based on criteria
func (qh *QueryHandler) SearchPlayers(query *PlayerQuery) ([]model.Player, int, error) {
	players := qh.dataLoader.GetPlayers()

	var result []model.Player
	for _, player := range players {
		if query.Name != "" && !strings.Contains(strings.ToLower(player.Name), strings.ToLower(query.Name)) {
			continue
		}
		if query.Nationality != "" && !strings.Contains(strings.ToLower(player.Nationality), strings.ToLower(query.Nationality)) {
			continue
		}
		if query.Club != "" && !strings.Contains(strings.ToLower(player.Club), strings.ToLower(query.Club)) {
			continue
		}
		if query.Position != "" && !strings.Contains(strings.ToLower(player.Position), strings.ToLower(query.Position)) {
			continue
		}
		if query.MinOverall > 0 && player.Overall < query.MinOverall {
			continue
		}

		result = append(result, player)
	}

	// Sort by overall rating (descending)
	sort.Slice(result, func(i, j int) bool {
		return result[i].Overall > result[j].Overall
	})

	// Apply pagination
	total := len(result)
	if query.Offset > 0 && query.Offset < total {
		result = result[query.Offset:]
	}
	if query.Limit > 0 && len(result) > query.Limit {
		result = result[:query.Limit]
	}

	return result, total, nil
}

// GetTopScorers returns top scorers from matches
func (qh *QueryHandler) GetTopScorers(tournament string, limit int) ([]model.TeamStats, error) {
	matches := qh.dataLoader.GetMatches()
	teamStats := make(map[string]*model.TeamStats)

	for _, match := range matches {
		if tournament != "" && !strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(tournament)) {
			continue
		}

		if _, ok := teamStats[match.HomeTeam]; !ok {
			teamStats[match.HomeTeam] = &model.TeamStats{
				Team: match.HomeTeam,
			}
		}
		if _, ok := teamStats[match.AwayTeam]; !ok {
			teamStats[match.AwayTeam] = &model.TeamStats{
				Team: match.AwayTeam,
			}
		}

		teamStats[match.HomeTeam].GoalsFor += match.HomeGoal
		teamStats[match.HomeTeam].GoalsAgainst += match.AwayGoal
		teamStats[match.HomeTeam].Matches++

		teamStats[match.AwayTeam].GoalsFor += match.AwayGoal
		teamStats[match.AwayTeam].GoalsAgainst += match.HomeGoal
		teamStats[match.AwayTeam].Matches++
	}

	// Convert to slice and sort
	var stats []model.TeamStats
	for _, s := range teamStats {
		s.GoalDifference = s.GoalsFor - s.GoalsAgainst
		stats = append(stats, *s)
	}

	sort.Slice(stats, func(i, j int) bool {
		return stats[i].GoalsFor > stats[j].GoalsFor
	})

	if limit > len(stats) {
		limit = len(stats)
	}
	return stats[:limit], nil
}

// CalculateStandings calculates competition standings
func (qh *QueryHandler) CalculateStandings(tournament string, season string) (*model.CompetitionStandings, error) {
	matches := qh.dataLoader.GetMatches()
	teamStats := make(map[string]*model.TeamStats)

	for _, match := range matches {
		if tournament != "" && !strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(tournament)) {
			continue
		}
		if season != "" && match.Season != season {
			continue
		}

		if _, ok := teamStats[match.HomeTeam]; !ok {
			teamStats[match.HomeTeam] = &model.TeamStats{
				Team: match.HomeTeam,
			}
		}
		if _, ok := teamStats[match.AwayTeam]; !ok {
			teamStats[match.AwayTeam] = &model.TeamStats{
				Team: match.AwayTeam,
			}
		}

		// Update home team stats
		ht := teamStats[match.HomeTeam]
		ht.Matches++
		ht.GoalsFor += match.HomeGoal
		ht.GoalsAgainst += match.AwayGoal
		ht.HomeMatches++
		ht.HomeGoalsFor += match.HomeGoal
		ht.HomeGoalsAgainst += match.AwayGoal

		// Update away team stats
		at := teamStats[match.AwayTeam]
		at.Matches++
		at.GoalsFor += match.AwayGoal
		at.GoalsAgainst += match.HomeGoal
		at.AwayMatches++
		at.AwayGoalsFor += match.AwayGoal
		at.AwayGoalsAgainst += match.HomeGoal

		// Determine winner
		if match.HomeGoal > match.AwayGoal {
			ht.Wins++
			ht.Points += 3
			at.Losses++
		} else if match.HomeGoal < match.AwayGoal {
			at.Wins++
			at.Points += 3
			ht.Losses++
		} else {
			ht.Draws++
			ht.Points++
			at.Draws++
			at.Points++
		}
	}

	// Convert to slice and sort by points
	var standings []model.TeamStats
	for _, s := range teamStats {
		s.GoalDifference = s.GoalsFor - s.GoalsAgainst
		standings = append(standings, *s)
	}

	sort.Slice(standings, func(i, j int) bool {
		if standings[i].Points != standings[j].Points {
			return standings[i].Points > standings[j].Points
		}
		if standings[i].GoalDifference != standings[j].GoalDifference {
			return standings[i].GoalDifference > standings[j].GoalDifference
		}
		return standings[i].GoalsFor > standings[j].GoalsFor
	})

	return &model.CompetitionStandings{
		Competition: tournament,
		Season:      season,
		Standings:   standings,
	}, nil
}

// GetBiggestWins finds matches with the largest goal differences
func (qh *QueryHandler) GetBiggestWins(tournament string, limit int) ([]model.BigWin, error) {
	matches := qh.dataLoader.GetMatches()
	var bigWins []model.BigWin

	for _, match := range matches {
		if tournament != "" && !strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(tournament)) {
			continue
		}

		goalDiff := abs(match.HomeGoal - match.AwayGoal)
		if goalDiff > 2 { // Only include significant wins
			bigWins = append(bigWins, model.BigWin{
				Match:          match,
				GoalDifference: goalDiff,
			})
		}
	}

	// Sort by goal difference (descending)
	sort.Slice(bigWins, func(i, j int) bool {
		return bigWins[i].GoalDifference > bigWins[j].GoalDifference
	})

	if limit > len(bigWins) {
		limit = len(bigWins)
	}
	return bigWins[:limit], nil
}

// GetRecentMatches gets recent matches for a team
func (qh *QueryHandler) GetRecentMatches(team string, limit int) ([]model.Match, error) {
	matches := qh.dataLoader.GetMatches()
	var result []model.Match

	for _, match := range matches {
		if strings.EqualFold(match.HomeTeam, team) || strings.EqualFold(match.AwayTeam, team) {
			result = append(result, match)
		}
	}

	// Sort by date (most recent first)
	sort.Slice(result, func(i, j int) bool {
		return result[i].DateTime > result[j].DateTime
	})

	if limit > len(result) {
		limit = len(result)
	}
	return result[:limit], nil
}

// GetTeamMatches gets all matches for a team
func (qh *QueryHandler) GetTeamMatches(team string, tournament string) ([]model.Match, error) {
	matches := qh.dataLoader.GetMatches()
	var result []model.Match

	for _, match := range matches {
		teamPlayed := strings.EqualFold(match.HomeTeam, team) || strings.EqualFold(match.AwayTeam, team)
		if !teamPlayed {
			continue
		}
		if tournament != "" && !strings.Contains(strings.ToLower(match.Tournament), strings.ToLower(tournament)) {
			continue
		}
		result = append(result, match)
	}

	return result, nil
}

// GetMatchesBetweenTeams gets matches between two teams
func (qh *QueryHandler) GetMatchesBetweenTeams(team1, team2 string) ([]model.Match, error) {
	matches := qh.dataLoader.GetMatches()
	var result []model.Match

	for _, match := range matches {
		team1Played := strings.EqualFold(match.HomeTeam, team1) || strings.EqualFold(match.AwayTeam, team1)
		team2Played := strings.EqualFold(match.HomeTeam, team2) || strings.EqualFold(match.AwayTeam, team2)

		if team1Played && team2Played {
			result = append(result, match)
		}
	}

	// Sort by date (most recent first)
	sort.Slice(result, func(i, j int) bool {
		return result[i].DateTime > result[j].DateTime
	})

	return result, nil
}

// GetTeamRecord gets a team's record (W-D-L)
func (qh *QueryHandler) GetTeamRecord(team string) (wins, draws, losses int, err error) {
	matches := qh.dataLoader.GetMatches()

	for _, match := range matches {
		isHome := strings.EqualFold(match.HomeTeam, team)
		isAway := strings.EqualFold(match.AwayTeam, team)

		if !isHome && !isAway {
			continue
		}

		if match.HomeGoal > match.AwayGoal {
			if isHome {
				wins++
			} else {
				losses++
			}
		} else if match.HomeGoal < match.AwayGoal {
			if isHome {
				losses++
			} else {
				wins++
			}
		} else {
			draws++
		}
	}

	return wins, draws, losses, nil
}

// abs returns the absolute value of an integer
func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

// FormatMatchResponse formats a match for display
func FormatMatchResponse(match model.Match) string {
	return fmt.Sprintf("%s: %s %d-%d %s (%s)",
		match.DateTime,
		match.HomeTeam,
		match.HomeGoal,
		match.AwayGoal,
		match.AwayTeam,
		match.Tournament,
	)
}

// FormatTeamStats formats team stats for display
func FormatTeamStats(stats *model.TeamStats) string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%s:\n", stats.Team))
	sb.WriteString(fmt.Sprintf("- Matches: %d\n", stats.Matches))
	sb.WriteString(fmt.Sprintf("- Wins: %d, Draws: %d, Losses: %d\n", stats.Wins, stats.Draws, stats.Losses))
	sb.WriteString(fmt.Sprintf("- Goals For: %d, Goals Against: %d\n", stats.GoalsFor, stats.GoalsAgainst))
	sb.WriteString(fmt.Sprintf("- Goal Difference: %d, Points: %d\n", stats.GoalDifference, stats.Points))
	if stats.Matches > 0 {
		winRate := float64(stats.Wins) / float64(stats.Matches) * 100
		sb.WriteString(fmt.Sprintf("- Win rate: %.1f%%\n", winRate))
	}
	return sb.String()
}

// FormatHeadToHead formats head-to-head for display
func FormatHeadToHead(h2h *model.TeamHeadToHead) string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%s vs %s Head-to-Head:\n", h2h.Team1, h2h.Team2))
	sb.WriteString(fmt.Sprintf("- Matches: %d\n", h2h.Matches))
	sb.WriteString(fmt.Sprintf("- %s Wins: %d\n", h2h.Team1, h2h.Team1Wins))
	sb.WriteString(fmt.Sprintf("- %s Wins: %d\n", h2h.Team2, h2h.Team2Wins))
	sb.WriteString(fmt.Sprintf("- Draws: %d\n", h2h.Draws))
	sb.WriteString(fmt.Sprintf("- %s Goals: %d, %s Goals: %d\n", h2h.Team1, h2h.Team1GoalsFor, h2h.Team2, h2h.Team2GoalsFor))
	return sb.String()
}

// FormatStandings formats standings for display
func FormatStandings(standings *model.CompetitionStandings) string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%s %s Standings:\n", standings.Competition, standings.Season))
	sb.WriteString(strings.Repeat("-", 60) + "\n")
	sb.WriteString(fmt.Sprintf("%-3s %-25s %4s %4s %4s %4s %4s %4s\n", "Pos", "Team", "MP", "W", "D", "L", "GF", "GA"))
	sb.WriteString(strings.Repeat("-", 60) + "\n")

	for i, team := range standings.Standings {
		sb.WriteString(fmt.Sprintf("%-3d %-25s %4d %4d %4d %4d %4d %4d\n",
			i+1, team.Team, team.Matches, team.Wins, team.Draws, team.Losses, team.GoalsFor, team.GoalsAgainst))
	}
	return sb.String()
}
