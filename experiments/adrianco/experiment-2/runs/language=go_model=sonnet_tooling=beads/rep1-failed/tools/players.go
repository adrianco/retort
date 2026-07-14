package tools

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"brazilian-soccer-mcp/data"
)

// RegisterPlayerTools registers player-related MCP tools.
func RegisterPlayerTools(s *server.MCPServer, store *data.Store) {
	s.AddTool(mcp.NewTool("search_players",
		mcp.WithDescription("Search FIFA player data by name, nationality, club, or position."),
		mcp.WithString("name", mcp.Description("Player name (partial match)")),
		mcp.WithString("nationality", mcp.Description("Player nationality (e.g. 'Brazil', 'Argentina')")),
		mcp.WithString("club", mcp.Description("Club name (e.g. 'Flamengo', 'Palmeiras')")),
		mcp.WithString("position", mcp.Description("Position (e.g. 'GK', 'ST', 'CM')")),
		mcp.WithNumber("min_overall", mcp.Description("Minimum FIFA overall rating")),
		mcp.WithString("sort_by",
			mcp.Description("Sort by: 'overall', 'potential', 'age' (default 'overall')"),
			mcp.DefaultString("overall"),
		),
		mcp.WithNumber("limit", mcp.Description("Max results (default 20)")),
	), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return searchPlayers(store, req)
	})

	s.AddTool(mcp.NewTool("club_players",
		mcp.WithDescription("List all players at a specific club from the FIFA dataset, grouped by position."),
		mcp.WithString("club", mcp.Description("Club name"), mcp.Required()),
		mcp.WithNumber("limit", mcp.Description("Max players to list (default 30)")),
	), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return clubPlayers(store, req)
	})
}

func playerMatches(p data.Player, name, nationality, club, position string, minOverall int) bool {
	if name != "" && !strings.Contains(strings.ToLower(data.RemoveAccents(p.Name)), strings.ToLower(data.RemoveAccents(name))) {
		return false
	}
	if nationality != "" && !strings.EqualFold(p.Nationality, nationality) &&
		!strings.Contains(strings.ToLower(p.Nationality), strings.ToLower(nationality)) {
		return false
	}
	if club != "" && !strings.Contains(strings.ToLower(data.RemoveAccents(p.Club)), strings.ToLower(data.RemoveAccents(club))) {
		return false
	}
	if position != "" && !strings.EqualFold(p.Position, position) &&
		!strings.Contains(strings.ToLower(p.Position), strings.ToLower(position)) {
		return false
	}
	if minOverall > 0 && p.Overall < minOverall {
		return false
	}
	return true
}

func searchPlayers(store *data.Store, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	name, _ := args["name"].(string)
	nationality, _ := args["nationality"].(string)
	club, _ := args["club"].(string)
	position, _ := args["position"].(string)
	minOverallF, _ := args["min_overall"].(float64)
	minOverall := int(minOverallF)
	sortBy, _ := args["sort_by"].(string)
	if sortBy == "" {
		sortBy = "overall"
	}
	limitF, _ := args["limit"].(float64)
	limit := int(limitF)
	if limit <= 0 {
		limit = 20
	}

	var players []data.Player
	for _, p := range store.Players {
		if playerMatches(p, name, nationality, club, position, minOverall) {
			players = append(players, p)
		}
	}

	sort.Slice(players, func(i, j int) bool {
		switch sortBy {
		case "potential":
			return players[i].Potential > players[j].Potential
		case "age":
			return players[i].Age < players[j].Age
		default:
			return players[i].Overall > players[j].Overall
		}
	})

	total := len(players)
	if len(players) > limit {
		players = players[:limit]
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Found %d player(s)", total))
	if total > limit {
		sb.WriteString(fmt.Sprintf(" (showing top %d by %s)", limit, sortBy))
	}
	sb.WriteString(":\n\n")
	sb.WriteString(fmt.Sprintf("%-3s  %-25s  %-5s  %-4s  %-4s  %-12s  %-28s\n",
		"#", "Name", "Nat", "OVR", "POT", "Position", "Club"))
	sb.WriteString(strings.Repeat("-", 95) + "\n")

	for i, p := range players {
		nat := p.Nationality
		if len(nat) > 5 {
			nat = nat[:5]
		}
		sb.WriteString(fmt.Sprintf("%-3d  %-25s  %-5s  %4d  %4d  %-12s  %-28s\n",
			i+1,
			truncate(p.Name, 25),
			nat,
			p.Overall,
			p.Potential,
			truncate(p.Position, 12),
			truncate(p.Club, 28),
		))
	}

	return mcp.NewToolResultText(sb.String()), nil
}

func clubPlayers(store *data.Store, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	club, _ := args["club"].(string)
	limitF, _ := args["limit"].(float64)
	limit := int(limitF)
	if limit <= 0 {
		limit = 30
	}

	if club == "" {
		return mcp.NewToolResultText("club parameter is required."), nil
	}

	var players []data.Player
	for _, p := range store.Players {
		if strings.Contains(strings.ToLower(data.RemoveAccents(p.Club)), strings.ToLower(data.RemoveAccents(club))) {
			players = append(players, p)
		}
	}

	sort.Slice(players, func(i, j int) bool {
		return players[i].Overall > players[j].Overall
	})

	total := len(players)
	if len(players) > limit {
		players = players[:limit]
	}

	if len(players) == 0 {
		return mcp.NewToolResultText(fmt.Sprintf("No players found for club '%s'.", club)), nil
	}

	// Group by position
	byPos := make(map[string][]data.Player)
	posOrder := []string{"GK", "CB", "LB", "RB", "LWB", "RWB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "CF", "ST", "RF", "LF"}
	for _, p := range players {
		byPos[p.Position] = append(byPos[p.Position], p)
	}

	// Collect any positions not in posOrder
	seen := make(map[string]bool)
	for _, pos := range posOrder {
		seen[pos] = true
	}
	for pos := range byPos {
		if !seen[pos] {
			posOrder = append(posOrder, pos)
		}
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%s — FIFA squad (%d players", players[0].Club, total))
	if total > limit {
		sb.WriteString(fmt.Sprintf(", showing top %d by overall", limit))
	}
	sb.WriteString("):\n\n")

	avgOverall := 0
	for _, p := range players {
		avgOverall += p.Overall
	}
	if len(players) > 0 {
		sb.WriteString(fmt.Sprintf("Average overall rating: %.1f\n\n", float64(avgOverall)/float64(len(players))))
	}

	for _, pos := range posOrder {
		pp := byPos[pos]
		if len(pp) == 0 {
			continue
		}
		sb.WriteString(fmt.Sprintf("[%s]\n", pos))
		for _, p := range pp {
			sb.WriteString(fmt.Sprintf("  %-25s  OVR:%d  POT:%d  %-5s  #%s\n",
				truncate(p.Name, 25), p.Overall, p.Potential, p.Nationality[:min(5, len(p.Nationality))], p.JerseyNumber))
		}
	}

	return mcp.NewToolResultText(sb.String()), nil
}
