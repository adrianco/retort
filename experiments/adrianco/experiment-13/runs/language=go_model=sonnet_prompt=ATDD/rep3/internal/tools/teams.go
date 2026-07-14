package tools

import (
	"context"
	"encoding/json"
	"strings"

	"brazilian-soccer-mcp/internal/data"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func GetTeamStatsTool(matches []data.Match) server.ServerTool {
	tool := mcp.NewTool("get_team_stats",
		mcp.WithDescription("Get statistics for a team"),
		mcp.WithString("team", mcp.Required(), mcp.Description("Team name")),
		mcp.WithString("competition", mcp.Description("Competition filter: brasileirao, copa, libertadores")),
		mcp.WithNumber("season", mcp.Description("Season year")),
		mcp.WithString("venue", mcp.Description("Venue filter: home, away, or both (default: both)")),
	)

	handler := func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		teamParam, _ := args["team"].(string)
		competitionParam, _ := args["competition"].(string)
		seasonFloat, _ := args["season"].(float64)
		season := int(seasonFloat)
		venueParam, _ := args["venue"].(string)
		if venueParam == "" {
			venueParam = "both"
		}
		venueParam = strings.ToLower(venueParam)

		type stats struct {
			Matches      int
			Wins         int
			Draws        int
			Losses       int
			GoalsFor     int
			GoalsAgainst int
		}

		var st stats
		competitions := map[string]bool{}

		for _, m := range matches {
			if competitionParam != "" && !matchesCompetition(competitionParam, m.Competition) {
				continue
			}
			if season != 0 && m.Season != season {
				continue
			}

			isHome := teamMatches(teamParam, m.HomeTeam)
			isAway := teamMatches(teamParam, m.AwayTeam)

			if !isHome && !isAway {
				continue
			}

			if venueParam == "home" && !isHome {
				continue
			}
			if venueParam == "away" && !isAway {
				continue
			}

			competitions[m.Competition] = true
			st.Matches++

			if isHome {
				st.GoalsFor += m.HomeGoal
				st.GoalsAgainst += m.AwayGoal
				if m.HomeGoal > m.AwayGoal {
					st.Wins++
				} else if m.HomeGoal == m.AwayGoal {
					st.Draws++
				} else {
					st.Losses++
				}
			} else {
				st.GoalsFor += m.AwayGoal
				st.GoalsAgainst += m.HomeGoal
				if m.AwayGoal > m.HomeGoal {
					st.Wins++
				} else if m.AwayGoal == m.HomeGoal {
					st.Draws++
				} else {
					st.Losses++
				}
			}
		}

		compList := []string{}
		for c := range competitions {
			compList = append(compList, c)
		}

		winRate := 0.0
		if st.Matches > 0 {
			winRate = float64(st.Wins) / float64(st.Matches)
		}

		resp := map[string]interface{}{
			"team":           teamParam,
			"matches":        st.Matches,
			"wins":           st.Wins,
			"draws":          st.Draws,
			"losses":         st.Losses,
			"goals_for":      st.GoalsFor,
			"goals_against":  st.GoalsAgainst,
			"goal_diff":      st.GoalsFor - st.GoalsAgainst,
			"win_rate":       winRate,
			"competitions":   compList,
		}

		b, _ := json.Marshal(resp)
		return mcp.NewToolResultText(string(b)), nil
	}

	return server.ServerTool{Tool: tool, Handler: handler}
}
