package server

import (
	"fmt"

	"brazilian-soccer-mcp/internal/models"
)

// formatMatchesText formats matches as human-readable text
func formatMatchesText(matches []models.Match) string {
	if len(matches) == 0 {
		return "No matches found"
	}
	var result string
	for i, match := range matches {
		if i >= 20 {
			result += fmt.Sprintf("\n... and %d more matches", len(matches)-20)
			break
		}
		result += fmt.Sprintf("%s: %s %d-%d %s (Season %d, Round %d, %s)\n",
			match.Datetime.Format("2006-01-02"), match.HomeTeam, match.HomeGoal, match.AwayGoal,
			match.AwayTeam, match.Season, match.Round, match.Tournament)
	}
	return result
}

// formatPlayersText formats players as human-readable text
func formatPlayersText(players []models.Player) string {
	if len(players) == 0 {
		return "No players found"
	}
	var result string
	for i, player := range players {
		if i >= 20 {
			result += fmt.Sprintf("\n... and %d more players", len(players)-20)
			break
		}
		result += fmt.Sprintf("%d. %s (%s, %s) - Overall: %d, Club: %s\n",
			i+1, player.Name, player.Nationality, player.Position, player.Overall, player.Club)
	}
	return result
}

// formatPlayerText formats a single player as human-readable text
func formatPlayerText(player *models.Player) string {
	return fmt.Sprintf("%s (%d years old, %s) - Overall: %d, Potential: %d, Club: %s, Position: %s",
		player.Name, player.Age, player.Nationality, player.Overall, player.Potential, player.Club, player.Position)
}

// formatBigWinsText formats big wins as human-readable text
func formatBigWinsText(wins []models.BigWin) string {
	if len(wins) == 0 {
		return "No big wins found"
	}
	var result string
	for i, win := range wins {
		if i >= 20 {
			result += fmt.Sprintf("\n... and %d more big wins", len(wins)-20)
			break
		}
		result += fmt.Sprintf("%d. %s: %s %d-%d %s (Goal Diff: %d, %s)\n",
			i+1, win.Date.Format("2006-01-02"), win.HomeTeam, win.HomeGoal, win.AwayGoal,
			win.AwayTeam, win.GoalDiff, win.Tournament)
	}
	return result
}

// formatStandingsText formats standings as human-readable text
func formatStandingsText(standings []models.CompetitionResult) string {
	if len(standings) == 0 {
		return "No standings found"
	}
	var result string
	for i, team := range standings {
		result += fmt.Sprintf("%d. %s - %d pts (%dW-%dD-%dL) GF:%d GA:%d\n",
			i+1, team.TeamName, team.Points, team.Wins, team.Draws, team.Losses,
			team.GoalsFor, team.GoalsAgainst)
	}
	return result
}

// formatCompareTeamsText formats team comparison as human-readable text
func formatCompareTeamsText(result map[string]interface{}) string {
	team1 := result["team_1"].(map[string]interface{})
	team2 := result["team_2"].(map[string]interface{})
	h2h := result["head_to_head"].(map[string]interface{})

	return fmt.Sprintf("Team 1 (%s): %d matches, %d wins, %d draws, %d losses, GF:%d GA:%d %d pts\n"+
		"Team 2 (%s): %d matches, %d wins, %d draws, %d losses, GF:%d GA:%d %d pts\n"+
		"Head-to-Head: %d-%d-%d",
		team1["name"], team1["matches"], team1["wins"], team1["draws"], team1["losses"],
		team1["goals_for"], team1["goals_against"], team1["points"],
		team2["name"], team2["matches"], team2["wins"], team2["draws"], team2["losses"],
		team2["goals_for"], team2["goals_against"], team2["points"],
		h2h["team_1_wins"], h2h["team_2_wins"], h2h["draws"])
}
