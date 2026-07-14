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

func FindPlayersTool(players []data.Player) server.ServerTool {
	tool := mcp.NewTool("find_players",
		mcp.WithDescription("Find players with optional filters"),
		mcp.WithString("name", mcp.Description("Player name (substring match)")),
		mcp.WithString("nationality", mcp.Description("Player nationality")),
		mcp.WithString("club", mcp.Description("Player club (substring match)")),
		mcp.WithString("position", mcp.Description("Player position")),
		mcp.WithNumber("min_overall", mcp.Description("Minimum overall rating")),
		mcp.WithNumber("limit", mcp.Description("Maximum number of results (default 20)")),
	)

	handler := func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		args := req.GetArguments()
		nameParam, _ := args["name"].(string)
		nationalityParam, _ := args["nationality"].(string)
		clubParam, _ := args["club"].(string)
		positionParam, _ := args["position"].(string)
		minOverallF, _ := args["min_overall"].(float64)
		minOverall := int(minOverallF)
		limitF, _ := args["limit"].(float64)
		limit := int(limitF)
		if limit <= 0 {
			limit = 20
		}

		var result []data.Player
		for _, p := range players {
			if nameParam != "" && !strings.Contains(strings.ToLower(p.Name), strings.ToLower(nameParam)) {
				continue
			}
			if nationalityParam != "" && !strings.EqualFold(p.Nationality, nationalityParam) {
				continue
			}
			if clubParam != "" && !strings.Contains(strings.ToLower(p.Club), strings.ToLower(clubParam)) {
				continue
			}
			if positionParam != "" && !strings.EqualFold(p.Position, positionParam) {
				continue
			}
			if minOverall > 0 && p.Overall < minOverall {
				continue
			}
			result = append(result, p)
		}

		// Sort by overall descending
		sort.Slice(result, func(i, j int) bool {
			return result[i].Overall > result[j].Overall
		})

		total := len(result)
		if limit > 0 && len(result) > limit {
			result = result[:limit]
		}

		type playerJSON struct {
			ID          int    `json:"id"`
			Name        string `json:"name"`
			Age         int    `json:"age"`
			Nationality string `json:"nationality"`
			Overall     int    `json:"overall"`
			Potential   int    `json:"potential"`
			Club        string `json:"club"`
			Position    string `json:"position"`
		}

		var jsonPlayers []playerJSON
		for _, p := range result {
			jsonPlayers = append(jsonPlayers, playerJSON{
				ID:          p.ID,
				Name:        p.Name,
				Age:         p.Age,
				Nationality: p.Nationality,
				Overall:     p.Overall,
				Potential:   p.Potential,
				Club:        p.Club,
				Position:    p.Position,
			})
		}

		resp := map[string]interface{}{
			"players": jsonPlayers,
			"total":   total,
		}
		if jsonPlayers == nil {
			resp["players"] = []playerJSON{}
		}

		b, _ := json.Marshal(resp)
		return mcp.NewToolResultText(string(b)), nil
	}

	return server.ServerTool{Tool: tool, Handler: handler}
}
