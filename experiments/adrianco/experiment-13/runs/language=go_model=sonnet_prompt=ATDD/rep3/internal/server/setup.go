package server

import (
	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/tools"
	"github.com/mark3labs/mcp-go/server"
)

func RegisterTools(dataDir string) ([]server.ServerTool, error) {
	matches, players, err := data.LoadAll(dataDir)
	if err != nil {
		return nil, err
	}
	return []server.ServerTool{
		tools.FindMatchesTool(matches),
		tools.GetTeamStatsTool(matches),
		tools.FindPlayersTool(players),
		tools.GetHeadToHeadTool(matches),
		tools.GetStandingsTool(matches),
		tools.GetStatisticsTool(matches),
	}, nil
}
