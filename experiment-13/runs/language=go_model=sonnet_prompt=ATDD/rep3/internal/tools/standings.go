package tools

import (
	"context"
	"encoding/json"
	"sort"
	"strings"

	"brazilian-soccer-mcp/internal/data"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func GetStandingsTool(matches []data.Match) server.ServerTool {
	tool := mcp.NewTool("get_standings",
		mcp.WithDescription("Get league standings for a season"),
		mcp.WithNumber("season", mcp.Required(), mcp.Description("Season year")),
		mcp.WithString("competition", mcp.Description("Competition (default: brasileirao)")),
	)

	handler := func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		seasonFloat, _ := args["season"].(float64)
		season := int(seasonFloat)
		competitionParam, _ := args["competition"].(string)
		if competitionParam == "" {
			competitionParam = "brasileirao"
		}

		type teamStats struct {
			Team         string
			Matches      int
			Wins         int
			Draws        int
			Losses       int
			GoalsFor     int
			GoalsAgainst int
			Points       int
		}

		standings := map[string]*teamStats{}

		getOrCreate := func(name string) *teamStats {
			key := strings.ToLower(name)
			if _, ok := standings[key]; !ok {
				standings[key] = &teamStats{Team: name}
			}
			return standings[key]
		}

		for _, m := range matches {
			if !matchesCompetition(competitionParam, m.Competition) {
				continue
			}
			if season != 0 && m.Season != season {
				continue
			}

			home := getOrCreate(m.HomeTeam)
			away := getOrCreate(m.AwayTeam)

			home.Matches++
			away.Matches++
			home.GoalsFor += m.HomeGoal
			home.GoalsAgainst += m.AwayGoal
			away.GoalsFor += m.AwayGoal
			away.GoalsAgainst += m.HomeGoal

			if m.HomeGoal > m.AwayGoal {
				home.Wins++
				home.Points += 3
				away.Losses++
			} else if m.HomeGoal == m.AwayGoal {
				home.Draws++
				away.Draws++
				home.Points++
				away.Points++
			} else {
				away.Wins++
				away.Points += 3
				home.Losses++
			}
		}

		type standingEntry struct {
			Rank         int    `json:"rank"`
			Team         string `json:"team"`
			Matches      int    `json:"matches"`
			Wins         int    `json:"wins"`
			Draws        int    `json:"draws"`
			Losses       int    `json:"losses"`
			GoalsFor     int    `json:"goals_for"`
			GoalsAgainst int    `json:"goals_against"`
			GoalDiff     int    `json:"goal_diff"`
			Points       int    `json:"points"`
		}

		var table []standingEntry
		for _, st := range standings {
			table = append(table, standingEntry{
				Team:         st.Team,
				Matches:      st.Matches,
				Wins:         st.Wins,
				Draws:        st.Draws,
				Losses:       st.Losses,
				GoalsFor:     st.GoalsFor,
				GoalsAgainst: st.GoalsAgainst,
				GoalDiff:     st.GoalsFor - st.GoalsAgainst,
				Points:       st.Points,
			})
		}

		sort.Slice(table, func(i, j int) bool {
			if table[i].Points != table[j].Points {
				return table[i].Points > table[j].Points
			}
			if table[i].GoalDiff != table[j].GoalDiff {
				return table[i].GoalDiff > table[j].GoalDiff
			}
			return table[i].GoalsFor > table[j].GoalsFor
		})

		for i := range table {
			table[i].Rank = i + 1
		}

		if table == nil {
			table = []standingEntry{}
		}

		resp := map[string]interface{}{
			"season":      season,
			"competition": competitionParam,
			"standings":   table,
		}

		b, _ := json.Marshal(resp)
		return mcp.NewToolResultText(string(b)), nil
	}

	return server.ServerTool{Tool: tool, Handler: handler}
}
