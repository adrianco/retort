package tools

import (
	"context"
	"encoding/json"
	"strings"

	"brazilian-soccer-mcp/internal/data"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func matchesCompetition(competition string, matchComp string) bool {
	comp := strings.ToLower(competition)
	mc := strings.ToLower(matchComp)
	if strings.Contains(comp, "brasileirao") || comp == "brasileirao" {
		return mc == "brasileirao"
	}
	if strings.Contains(comp, "copa") || strings.Contains(comp, "cup") {
		return strings.Contains(mc, "copa") || strings.Contains(mc, "cup")
	}
	if strings.Contains(comp, "libertadores") {
		return strings.Contains(mc, "libertadores")
	}
	return strings.Contains(mc, comp)
}

func teamMatches(teamParam string, matchTeam string) bool {
	if teamParam == "" {
		return true
	}
	normalized := strings.ToLower(data.NormalizeName(matchTeam))
	search := strings.ToLower(data.NormalizeName(teamParam))
	return strings.Contains(normalized, search)
}

func FindMatchesTool(matches []data.Match) server.ServerTool {
	tool := mcp.NewTool("find_matches",
		mcp.WithDescription("Find soccer matches with optional filters"),
		mcp.WithString("team", mcp.Description("Team name (substring match, either home or away)")),
		mcp.WithString("home_team", mcp.Description("Home team name (substring match)")),
		mcp.WithString("away_team", mcp.Description("Away team name (substring match)")),
		mcp.WithString("date_from", mcp.Description("Filter matches from this date (YYYY-MM-DD)")),
		mcp.WithString("date_to", mcp.Description("Filter matches to this date (YYYY-MM-DD)")),
		mcp.WithString("competition", mcp.Description("Competition filter: brasileirao, copa, libertadores")),
		mcp.WithNumber("season", mcp.Description("Season year")),
	)

	handler := func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		teamParam, _ := args["team"].(string)
		homeTeamParam, _ := args["home_team"].(string)
		awayTeamParam, _ := args["away_team"].(string)
		dateFrom, _ := args["date_from"].(string)
		dateTo, _ := args["date_to"].(string)
		competitionParam, _ := args["competition"].(string)
		seasonFloat, hasSeasonF := args["season"].(float64)
		seasonStr, hasSeasonS := args["season"].(string)
		season := 0
		if hasSeasonF {
			season = int(seasonFloat)
		} else if hasSeasonS {
			_ = seasonStr // ignore
		}

		var result []data.Match
		for _, m := range matches {
			// Team filter (either side)
			if teamParam != "" {
				if !teamMatches(teamParam, m.HomeTeam) && !teamMatches(teamParam, m.AwayTeam) {
					continue
				}
			}
			// Home team filter
			if homeTeamParam != "" && !teamMatches(homeTeamParam, m.HomeTeam) {
				continue
			}
			// Away team filter
			if awayTeamParam != "" && !teamMatches(awayTeamParam, m.AwayTeam) {
				continue
			}
			// Date filters
			if dateFrom != "" && m.Date < dateFrom {
				continue
			}
			if dateTo != "" && m.Date > dateTo {
				continue
			}
			// Competition filter
			if competitionParam != "" && !matchesCompetition(competitionParam, m.Competition) {
				continue
			}
			// Season filter
			if season != 0 && m.Season != season {
				continue
			}
			result = append(result, m)
		}

		type matchJSON struct {
			Date        string `json:"date"`
			HomeTeam    string `json:"home_team"`
			AwayTeam    string `json:"away_team"`
			HomeGoal    int    `json:"home_goal"`
			AwayGoal    int    `json:"away_goal"`
			Competition string `json:"competition"`
			Season      int    `json:"season"`
			Round       string `json:"round,omitempty"`
		}

		var jsonMatches []matchJSON
		for _, m := range result {
			jsonMatches = append(jsonMatches, matchJSON{
				Date:        m.Date,
				HomeTeam:    m.HomeTeam,
				AwayTeam:    m.AwayTeam,
				HomeGoal:    m.HomeGoal,
				AwayGoal:    m.AwayGoal,
				Competition: m.Competition,
				Season:      m.Season,
				Round:       m.Round,
			})
		}

		resp := map[string]interface{}{
			"matches": jsonMatches,
			"total":   len(jsonMatches),
		}
		if jsonMatches == nil {
			resp["matches"] = []matchJSON{}
		}

		b, _ := json.Marshal(resp)
		return mcp.NewToolResultText(string(b)), nil
	}

	return server.ServerTool{Tool: tool, Handler: handler}
}
