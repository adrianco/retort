package tools

import (
	"context"
	"encoding/json"

	"brazilian-soccer-mcp/internal/data"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func GetHeadToHeadTool(matches []data.Match) server.ServerTool {
	tool := mcp.NewTool("get_head_to_head",
		mcp.WithDescription("Get head-to-head record between two teams"),
		mcp.WithString("team1", mcp.Required(), mcp.Description("First team name")),
		mcp.WithString("team2", mcp.Required(), mcp.Description("Second team name")),
		mcp.WithString("competition", mcp.Description("Competition filter: brasileirao, copa, libertadores")),
		mcp.WithNumber("season", mcp.Description("Season year")),
	)

	handler := func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		team1Param, _ := args["team1"].(string)
		team2Param, _ := args["team2"].(string)
		competitionParam, _ := args["competition"].(string)
		seasonFloat, _ := args["season"].(float64)
		season := int(seasonFloat)

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

		team1Wins := 0
		team2Wins := 0
		draws := 0
		var matchList []matchJSON

		for _, m := range matches {
			if competitionParam != "" && !matchesCompetition(competitionParam, m.Competition) {
				continue
			}
			if season != 0 && m.Season != season {
				continue
			}

			t1Home := teamMatches(team1Param, m.HomeTeam)
			t1Away := teamMatches(team1Param, m.AwayTeam)
			t2Home := teamMatches(team2Param, m.HomeTeam)
			t2Away := teamMatches(team2Param, m.AwayTeam)

			isH2H := (t1Home && t2Away) || (t2Home && t1Away)
			if !isH2H {
				continue
			}

			matchList = append(matchList, matchJSON{
				Date:        m.Date,
				HomeTeam:    m.HomeTeam,
				AwayTeam:    m.AwayTeam,
				HomeGoal:    m.HomeGoal,
				AwayGoal:    m.AwayGoal,
				Competition: m.Competition,
				Season:      m.Season,
				Round:       m.Round,
			})

			if m.HomeGoal == m.AwayGoal {
				draws++
			} else if t1Home && m.HomeGoal > m.AwayGoal {
				team1Wins++
			} else if t1Away && m.AwayGoal > m.HomeGoal {
				team1Wins++
			} else {
				team2Wins++
			}
		}

		if matchList == nil {
			matchList = []matchJSON{}
		}

		resp := map[string]interface{}{
			"team1":       team1Param,
			"team2":       team2Param,
			"team1_wins":  team1Wins,
			"team2_wins":  team2Wins,
			"draws":       draws,
			"total":       len(matchList),
			"matches":     matchList,
		}

		b, _ := json.Marshal(resp)
		return mcp.NewToolResultText(string(b)), nil
	}

	return server.ServerTool{Tool: tool, Handler: handler}
}
